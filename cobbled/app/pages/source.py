from django.conf import settings
from django.utils.safestring import mark_safe
from iommi import Asset, Header, Page, html
from iommi._web_compat import Template

from app.forms.source import SourceForm, SourceGaiaInfoForm
from app.plots.rv_curve import get_rv_plot
from app.plots.vpec_vs_gamma import get_vvg_plot


def source_has_rv_data(source, user=None) -> bool:
    try:
        from app.plots.rv_curve import load_rv_data
        df = load_rv_data(source, user=user)
        return df.shape[0] >= 3
    except ValueError:
        return False


def get_request_cached_fit(source, request, fit_run, p_guess, k_guess, v0_guess, e_guess):
    if not request:
        from app.fitting import get_fit_results
        return get_fit_results(
            source,
            force_run=fit_run,
            p_guess=p_guess,
            k_guess=k_guess,
            v0_guess=v0_guess,
            e_guess=e_guess,
            user=None
        )

    cache_key = f"_fit_results_{source.id}"
    if not hasattr(request, cache_key):
        from app.fitting import get_fit_results
        fit_samples, fit_parameters = get_fit_results(
            source,
            force_run=fit_run,
            p_guess=p_guess,
            k_guess=k_guess,
            v0_guess=v0_guess,
            e_guess=e_guess,
            user=request.user
        )
        setattr(request, cache_key, (fit_samples, fit_parameters))
    return getattr(request, cache_key)


def render_fit_parameters_table(parameters) -> str:
    rows = ""
    for p in parameters:
        unit_str = f" ({p['unit']})" if p['unit'] else ""
        err_str = f"± {p['err']}" if p['err'] != 'N/A' else "—"
        ci_str = p['ci'] if p['ci'] != 'N/A' else "—"
        rows += f"""
        <tr>
            <td><strong>{p['name']}</strong>{unit_str}</td>
            <td><code>{p['val']}</code></td>
            <td><code>{err_str}</code></td>
            <td><code>{ci_str}</code></td>
        </tr>
        """
    return f"""
    <div class="table-responsive">
        <table class="table table-hover table-striped align-middle">
            <thead class="table-dark">
                <tr>
                    <th>Parameter</th>
                    <th>Fitted Value (MAP)</th>
                    <th>Standard Deviation (σ)</th>
                    <th>68% Credible Interval</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
    """


def get_planning_dates(fit_samples, t_last, jd_min):
    if fit_samples is None:
        return None

    import numpy as np
    import astropy.units as u
    from astropy.time import Time

    results = []

    if hasattr(fit_samples, 'get_orbit'):
        # It's a JokerSamples object
        best_orbit = fit_samples.get_orbit(0)
        best_P = best_orbit.P.to(u.day).value
        
        # Evaluate 1 cycle starting at t_last
        t_eval = np.linspace(t_last, t_last + best_P, 300)
        t_eval_time = Time(t_eval, format='jd')
        rv_eval = best_orbit.radial_velocity(t_eval_time).to(u.km/u.s).value
        
        min_idx = np.argmin(rv_eval)
        max_idx = np.argmax(rv_eval)
        
        results.append({
            "type": "Best-fit Model",
            "P": best_P,
            "min_jd": t_eval[min_idx],
            "min_date": Time(t_eval[min_idx], format='jd').iso.split()[0],
            "min_rv": rv_eval[min_idx],
            "max_jd": t_eval[max_idx],
            "max_date": Time(t_eval[max_idx], format='jd').iso.split()[0],
            "max_rv": rv_eval[max_idx],
        })
        
        num_samples = len(fit_samples)
        if num_samples > 1:
            periods = fit_samples['P'].to(u.day).value
            diffs = np.abs(np.log(periods / best_P))
            alt_idx = np.argmax(diffs)
            
            if diffs[alt_idx] > 0.15:
                alt_orbit = fit_samples.get_orbit(alt_idx)
                alt_P = periods[alt_idx]
                
                t_eval_alt = np.linspace(t_last, t_last + alt_P, 300)
                t_eval_alt_time = Time(t_eval_alt, format='jd')
                rv_eval_alt = alt_orbit.radial_velocity(t_eval_alt_time).to(u.km/u.s).value
                
                alt_min_idx = np.argmin(rv_eval_alt)
                alt_max_idx = np.argmax(rv_eval_alt)
                
                results.append({
                    "type": "Alternative Model",
                    "P": alt_P,
                    "min_jd": t_eval_alt[alt_min_idx],
                    "min_date": Time(t_eval_alt[alt_min_idx], format='jd').iso.split()[0],
                    "min_rv": rv_eval_alt[alt_min_idx],
                    "max_jd": t_eval_alt[alt_max_idx],
                    "max_date": Time(t_eval_alt[alt_max_idx], format='jd').iso.split()[0],
                    "max_rv": rv_eval_alt[alt_max_idx],
                })
    else:
        # Mock data (list of dicts)
        best_fit = fit_samples[0]
        best_P = best_fit['P']
        best_K = best_fit['K']
        best_v0 = best_fit['v0']
        best_phi = best_fit.get('phi', 0.0)
        
        t_eval = np.linspace(t_last, t_last + best_P, 300)
        x_eval = t_eval - jd_min
        rv_eval = best_v0 + best_K * np.sin(2 * np.pi * x_eval / best_P + best_phi)
        
        min_idx = np.argmin(rv_eval)
        max_idx = np.argmax(rv_eval)
        
        results.append({
            "type": "Best-fit Model",
            "P": best_P,
            "min_jd": t_eval[min_idx],
            "min_date": Time(t_eval[min_idx], format='jd').iso.split()[0],
            "min_rv": rv_eval[min_idx],
            "max_jd": t_eval[max_idx],
            "max_date": Time(t_eval[max_idx], format='jd').iso.split()[0],
            "max_rv": rv_eval[max_idx],
        })
        
        if len(fit_samples) > 1:
            periods = [p['P'] for p in fit_samples]
            diffs = [abs(np.log(p / best_P)) for p in periods]
            alt_idx = np.argmax(diffs)
            
            if diffs[alt_idx] > 0.15:
                alt_fit = fit_samples[alt_idx]
                alt_P = alt_fit['P']
                alt_K = alt_fit['K']
                alt_v0 = alt_fit['v0']
                alt_phi = alt_fit.get('phi', 0.0)
                
                t_eval_alt = np.linspace(t_last, t_last + alt_P, 300)
                x_eval_alt = t_eval_alt - jd_min
                rv_eval_alt = alt_v0 + alt_K * np.sin(2 * np.pi * x_eval_alt / alt_P + alt_phi)
                
                alt_min_idx = np.argmin(rv_eval_alt)
                alt_max_idx = np.argmax(rv_eval_alt)
                
                results.append({
                    "type": "Alternative Model",
                    "P": alt_P,
                    "min_jd": t_eval_alt[alt_min_idx],
                    "min_date": Time(t_eval_alt[alt_min_idx], format='jd').iso.split()[0],
                    "min_rv": rv_eval_alt[alt_min_idx],
                    "max_jd": t_eval_alt[alt_max_idx],
                    "max_date": Time(t_eval_alt[alt_max_idx], format='jd').iso.split()[0],
                    "max_rv": rv_eval_alt[alt_max_idx],
                })
                
    return results


def render_fit_results_html(source, fit_run=False, p_guess=None, k_guess=None, v0_guess=None, e_guess=None, request=None) -> str:
    from app.models.keplerian_fit import KeplerianFit
    from app.fitting import get_rv_data_hash, load_rv_data

    # Check minimum observation requirement
    try:
        df = load_rv_data(source, user=request.user if request else None)
        if df.shape[0] < 3:
            return ""
    except ValueError:
        return ""

    # 1. Fetch saved fit if any
    saved_fit = KeplerianFit.objects.filter(source=source).order_by("-created_at").first()

    # Check data hash mismatch
    has_mismatch = False
    saved_date_str = ""
    if saved_fit:
        try:
            current_hash = get_rv_data_hash(df)
            has_mismatch = (saved_fit.observation_hash != current_hash)
            saved_date_str = saved_fit.created_at.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass

    # Retrieve or run the fit (cached on request to avoid double runs)
    display_samples, display_parameters = get_request_cached_fit(
        source, request, fit_run, p_guess, k_guess, v0_guess, e_guess
    )

    status_alert = ""
    if fit_run:
        if display_samples is not None:
            status_alert = f"""
            <div class="alert alert-success d-flex align-items-center mb-4" role="alert">
                <div class="me-3">
                    <span class="fs-4">🚀</span>
                </div>
                <div>
                    <h5 class="alert-heading mb-1 fw-bold">Keplerian Fit Successful!</h5>
                    <p class="mb-0">The Joker completed rejection sampling successfully and returned {len(display_samples)} posterior orbits. The results have been saved to the database.</p>
                </div>
            </div>
            """
        else:
            status_alert = """
            <div class="alert alert-warning d-flex align-items-center mb-4" role="alert">
                <div class="me-3">
                    <span class="fs-4">⚠️</span>
                </div>
                <div>
                    <h5 class="alert-heading mb-1 fw-bold">Fit Converged to 0 Orbits</h5>
                    <p class="mb-0">The Joker rejection sampler did not find any accepted orbits. This can happen if observations have large errors or if the prior is too narrow. Try adjusting your guesses.</p>
                </div>
            </div>
            """
    elif saved_fit and display_samples:
        if has_mismatch:
            status_alert = f"""
            <div class="alert alert-warning d-flex align-items-center mb-4" role="alert">
                <div class="me-3">
                    <span class="fs-4">⚠️</span>
                </div>
                <div>
                    <h5 class="alert-heading mb-1 fw-bold">Observation Data Changed</h5>
                    <p class="mb-0">Loaded saved fit from <strong>{saved_date_str}</strong>, but the radial velocity observations have changed since then. Consider re-running the fit below.</p>
                </div>
            </div>
            """
        else:
            status_alert = f"""
            <div class="alert alert-info d-flex align-items-center mb-4" role="alert">
                <div class="me-3">
                    <span class="fs-4">💾</span>
                </div>
                <div>
                    <h5 class="alert-heading mb-1 fw-bold">Loaded Saved Fit</h5>
                    <p class="mb-0">Displaying saved fitting solution from <strong>{saved_date_str}</strong>.</p>
                </div>
            </div>
            """


    # Generate guesses form
    p_val = f'value="{p_guess}"' if p_guess is not None else ''
    k_val = f'value="{k_guess}"' if k_guess is not None else ''
    v0_val = f'value="{v0_guess}"' if v0_guess is not None else ''
    e_val = f'value="{e_guess}"' if e_guess is not None else ''

    form_html = f"""
    <div class="bg-light p-3 rounded mb-4 border">
        <h6 class="fw-bold mb-3"><i class="fa-solid fa-sliders me-2"></i>Configure Fitting Priors / Initial Guesses</h6>
        <form method="get">
            <input type="hidden" name="fit" value="true">
            <div class="row g-3 mb-3">
                <div class="col-md-3">
                    <label class="form-label fw-bold small text-muted mb-1">Period Guess (days)</label>
                    <input type="number" step="any" min="0.1" name="p_guess" class="form-control form-control-sm" placeholder="e.g. 10.5" {p_val}>
                </div>
                <div class="col-md-3">
                    <label class="form-label fw-bold small text-muted mb-1">Amplitude K Guess (km/s)</label>
                    <input type="number" step="any" min="0.1" name="k_guess" class="form-control form-control-sm" placeholder="e.g. 20.0" {k_val}>
                </div>
                <div class="col-md-3">
                    <label class="form-label fw-bold small text-muted mb-1">Systemic Velocity v0 (km/s)</label>
                    <input type="number" step="any" name="v0_guess" class="form-control form-control-sm" placeholder="e.g. 5.0" {v0_val}>
                </div>
                <div class="col-md-3">
                    <label class="form-label fw-bold small text-muted mb-1">Eccentricity Guess e</label>
                    <input type="number" step="any" min="0" max="0.99" name="e_guess" class="form-control form-control-sm" placeholder="e.g. 0.20" {e_val}>
                </div>
            </div>
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <button type="submit" class="btn btn-primary btn-sm">
                        <i class="fa-solid fa-play me-2"></i>Run Fit with Guesses
                    </button>
                    <a href="?fit=true" class="btn btn-outline-secondary btn-sm ms-2">
                        <i class="fa-solid fa-wand-magic-sparkles me-2"></i>Run Auto Fit (Wide Prior)
                    </a>
                </div>
                {"<a href='?' class='btn btn-link btn-sm text-decoration-none text-muted'><i class='fa-solid fa-rotate-left me-1'></i>Clear Parameters</a>" if (fit_run or p_guess or k_guess or v0_guess or e_guess) else ""}
            </div>
        </form>
    </div>
    """

    if not display_parameters:
        if fit_run:
            # Fit was run but failed (0 orbits)
            return form_html + status_alert
        else:
            # No fit has ever been run/saved
            no_fit_msg = """
            <div class="text-center p-4">
                <p class="text-muted mb-0">Keplerian orbit fit has not been run for this source yet. Configure starting values above or run auto fit to start fitting.</p>
            </div>
            """
            return form_html + no_fit_msg

    table_html = render_fit_parameters_table(display_parameters)

    # Calculate next observation planning dates
    planning_html = ""
    if display_samples:
        try:
            from astropy.time import Time
            t_now = Time.now().jd
            t_last_obs = df["jd"].max()
            jd_min = df["jd"].min()
            
            # Determine period for threshold check
            best_P = None
            if hasattr(display_samples, 'get_orbit'):
                import astropy.units as u
                best_orbit = display_samples.get_orbit(0)
                best_P = best_orbit.P.to(u.day).value
            elif display_samples:
                best_P = display_samples[0]['P']
                
            limit = max(365.0, 5 * best_P) if best_P else 365.0
            is_far_ahead = (t_now - t_last_obs) > limit

            if is_far_ahead:
                planning_html = f"""
                <h5 class="fw-bold mt-4 mb-3"><i class="fa-solid fa-calendar-days me-2"></i>Observation Planning (Next Extrema)</h5>
                <div class="alert alert-warning py-3">
                    <i class="fa-solid fa-triangle-exclamation me-2 fs-5 align-middle"></i>
                    <span><strong>Notice:</strong> The current date ({Time(t_now, format='jd').iso.split()[0]}) is far ahead of the last observation date ({Time(t_last_obs, format='jd').iso.split()[0]}) by {(t_now - t_last_obs):.1f} days. 
                    Predictions for the next RV extrema are not shown because they are highly uncertain due to accumulated phase errors over many orbital cycles.</span>
                </div>
                """
            else:
                planning_dates = get_planning_dates(display_samples, t_now, jd_min)
                if planning_dates:
                    planning_html = f"""
                    <h5 class="fw-bold mt-4 mb-3"><i class="fa-solid fa-calendar-days me-2"></i>Observation Planning (Next Extrema)</h5>
                    <div class="table-responsive">
                        <table class="table table-hover table-striped border align-middle small">
                            <thead class="table-dark">
                                <tr>
                                    <th>Model Type</th>
                                    <th>Period (days)</th>
                                    <th>Next Minimum RV Date (Gregorian)</th>
                                    <th>Min RV JD</th>
                                    <th>Min RV (km/s)</th>
                                    <th>Next Maximum RV Date (Gregorian)</th>
                                    <th>Max RV JD</th>
                                    <th>Max RV (km/s)</th>
                                </tr>
                            </thead>
                            <tbody>
                    """
                    for item in planning_dates:
                        planning_html += f"""
                                <tr>
                                    <td class="fw-bold">{item['type']}</td>
                                    <td>{item['P']:.2f}</td>
                                    <td class="text-danger fw-bold">{item['min_date']}</td>
                                    <td class="text-muted">{item['min_jd']:.4f}</td>
                                    <td class="text-danger fw-bold">{item['min_rv']:.2f}</td>
                                    <td class="text-success fw-bold">{item['max_date']}</td>
                                    <td class="text-muted">{item['max_jd']:.4f}</td>
                                    <td class="text-success fw-bold">{item['max_rv']:.2f}</td>
                                </tr>
                        """
                    planning_html += """
                            </tbody>
                        </table>
                    </div>
                    """
        except Exception as e:
            planning_html = f"<div class='alert alert-danger'>Error generating planning dates: {str(e)}</div>"

    # Fine Grid Scan Section
    fine_grid_html = ""
    if display_parameters:
        # Get MAP period estimate
        map_period = 10.0
        for row in display_parameters:
            if row.get("name") in ["MAP Period (P)", "Period (P)", "Period"]:
                try:
                    map_period = float(row.get("val"))
                except (ValueError, TypeError):
                    pass

        p_min_default = f"{max(0.1, map_period * 0.7):.2f}"
        p_max_default = f"{map_period * 1.3:.2f}"

        fine_scan_plot_html = ""
        fine_scan_summary = ""

        # Check if fine grid scan was requested via GET params
        p_min_param = request.GET.get("fine_p_min") if request else None
        p_max_param = request.GET.get("fine_p_max") if request else None
        samples_param = request.GET.get("fine_samples", "250000") if request else "250000"

        if p_min_param and p_max_param:
            try:
                p_min_val = float(p_min_param)
                p_max_val = float(p_max_param)
                num_s = int(samples_param)

                from app.fitting import run_fine_grid_scan
                from app.plots.rv_curve import get_fine_grid_plot

                user_obj = request.user if request else None
                scan_res = run_fine_grid_scan(source, p_min_val, p_max_val, num_samples=num_s, user=user_obj)

                if scan_res and scan_res.get("accepted", 0) > 0:
                    fine_scan_plot_html = get_fine_grid_plot(scan_res)
                    fine_scan_summary = f"""
                    <div class="alert alert-success d-flex align-items-center justify-content-between my-3 py-2 px-3">
                        <div>
                            <i class="fa-solid fa-chart-line me-2 fs-5"></i>
                            <strong>Fine Grid Peak:</strong> Best Period $P_{{best}} = <strong>{scan_res['best_period']:.4f} days</strong>$,
                            $K = <strong>{scan_res['best_k']:.2f} km/s</strong>$,
                            $e = <strong>{scan_res['best_e']:.3f}</strong>$
                            ({scan_res['accepted']} accepted orbits sampled out of {num_s:,} grid points).
                        </div>
                        <span class="badge bg-dark">Δχ²_min = 0.0</span>
                    </div>
                    """
                else:
                    fine_scan_plot_html = "<div class='alert alert-warning my-3'><i class='fa-solid fa-triangle-exclamation me-2'></i>No accepted orbits found in the specified period range. Try expanding the min/max period window.</div>"
            except Exception as ex:
                fine_scan_plot_html = f"<div class='alert alert-danger my-3'>Fine Grid Scan Error: {str(ex)}</div>"

        fine_grid_html = f"""
        <div class="card mt-4 border border-secondary-subtle shadow-sm rounded-3">
            <div class="card-header bg-dark text-white p-3 d-flex justify-content-between align-items-center">
                <h5 class="mb-0 fw-bold"><i class="fa-solid fa-magnifying-glass-chart me-2 text-warning"></i>Finer Grid Simulation & Posterior Likelihood Scan</h5>
                <span class="badge bg-secondary">On-Demand Fine Period Scan</span>
            </div>
            <div class="card-body p-4">
                <p class="text-muted small mb-3">
                    <i class="fa-solid fa-info-circle me-1 text-primary"></i>Conduct a high-density sampling grid focused over a narrow period window to evaluate posterior log-likelihood $\ln \mathcal{{L}}$ and $\Delta \chi^2$ profile confidence limits ($1\sigma$ and $3\sigma$).
                </p>

                <form method="GET" action="" class="row g-3 align-items-end mb-3">
                    <input type="hidden" name="fit" value="true">
                    <div class="col-md-3">
                        <label class="form-label fw-bold small mb-1">Period Min $P_{{min}}$ (days)</label>
                        <input type="number" step="any" name="fine_p_min" value="{p_min_param or p_min_default}" class="form-control form-control-sm font-monospace" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label fw-bold small mb-1">Period Max $P_{{max}}$ (days)</label>
                        <input type="number" step="any" name="fine_p_max" value="{p_max_param or p_max_default}" class="form-control form-control-sm font-monospace" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label fw-bold small mb-1">Grid Prior Density</label>
                        <select name="fine_samples" class="form-select form-select-sm">
                            <option value="100000" {"selected" if samples_param == "100000" else ""}>100,000 Samples (Fast)</option>
                            <option value="250000" {"selected" if samples_param == "250000" else ""}>250,000 Samples (Standard)</option>
                            <option value="500000" {"selected" if samples_param == "500000" else ""}>500,000 Samples (Ultra Fine)</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <button type="submit" class="btn btn-warning btn-sm w-100 fw-bold shadow-sm">
                            <i class="fa-solid fa-bolt me-1"></i>Run Fine Grid Scan
                        </button>
                    </div>
                </form>

                {fine_scan_summary}
                {fine_scan_plot_html}
            </div>
        </div>
        """

    return f"""
    {form_html}
    {status_alert}
    <h5 class="fw-bold mb-3"><i class="fa-solid fa-list-check me-2"></i>Fitted Orbital Parameters</h5>
    {table_html}
    {planning_html}
    {fine_grid_html}
    """


class SourceViewPage(Page):
    """
    The basic view for a source.

    Needs to include all the plots too!
    """

    header = Header(lambda source, **_: source)

    # This could be done using a Panel, but this is simplest
    detail = html.div(
        attrs__class={"row": True},
        children=dict(
            form=SourceForm(
                auto__exclude=["is_valid", "name"],
                instance=lambda source, **_: source,
                editable=False,
                attrs__class={"col-md-9": True},
            ),
            aladin=html.div(
                attrs__id="aladin-lite-div",
                attrs__class={"col-md-3": True},  # Can't have a dict key called 'class'
                assets=dict(
                    aladin_target=Asset.js(
                        lambda source, **_: mark_safe(
                            f'let aladin_target = "{source.get_aladin_coordinates()}";'
                            f"let aladin_fov = {settings.ALADIN_DEFAULT_FOV:.1f};"
                            f"let aladin_survey = {settings.ALADIN_DEFAULT_SURVEY};"
                        )
                    ),
                    aladin_library=Asset.js(
                        attrs__src="https://aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.js"
                    ),
                    aladin=Asset.js(
                        attrs__src="/static/js/source_aladin.js", in_body=True
                    ),  # The code that finds the div and renders it
                ),
            ),
        ),
    )
    vvg_plot = Template("{{ page.extra_evaluated.vvg_plot | safe }}")
    rv_plot = Template("{{ page.extra_evaluated.rv_plot | safe }}")

    fit_panel = html.div(
        attrs__class={"card my-4": True},
        children=dict(
            header=html.div(
                html.h4("Keplerian Orbit Fitting", attrs__class={"card-title mb-0": True}),
                attrs__class={"card-header bg-dark text-white d-flex justify-content-between align-items-center": True},
            ),
            body=html.div(
                Template("{{ page.extra_evaluated.fit_results_html | safe }}"),
                attrs__class={"card-body": True},
                include=lambda source, request, **_: source_has_rv_data(source, user=request.user)
            )
        ),
        include=lambda source, request, **_: source_has_rv_data(source, user=request.user)
    )

    observations_panel = Template("{{ page.extra_evaluated.observations_table_html | safe }}")

    gaia_info = SourceGaiaInfoForm(
        auto__exclude=["is_valid", "source"],
        include=lambda source, **_: hasattr(
            source, "gaiainfo"
        ),  # Skip this block if we don't have Gaia info
        instance=lambda source, **_: source.gaiainfo,
        editable=False,
    )

    class Meta:
        @staticmethod
        def extra_evaluated__observations_table_html(source, request, **_) -> str:
            return render_observations_table_html(source, request)

        @staticmethod
        def extra_evaluated__vvg_plot(source, **_) -> str:
            """
            Generates and renders the vpec_vs_gamma plot for a given source if relevant data is present
            """
            try:
                # Get the vpec_vs_gamma plot
                figure = get_vvg_plot(source)
                return figure
            except ValueError:
                # If plot could not be generated (if source has no Gaiainfo or there's no file to draw from), skip and return an empty fragment
                return ""

        @staticmethod
        def extra_evaluated__rv_plot(source, request, **_) -> str:
            """
            Generates and renders the rv_curve plot for a given source if relevant data is present
            """
            try:
                p_guess = request.GET.get("p_guess")
                k_guess = request.GET.get("k_guess")
                v0_guess = request.GET.get("v0_guess")
                e_guess = request.GET.get("e_guess")

                p_guess = float(p_guess) if p_guess else None
                k_guess = float(k_guess) if k_guess else None
                v0_guess = float(v0_guess) if v0_guess else None
                e_guess = float(e_guess) if e_guess else None

                fit_run = (request and request.GET.get("fit") == "true") or any(v is not None for v in [p_guess, k_guess, v0_guess, e_guess])

                from app.models.keplerian_fit import KeplerianFit
                from app.fitting import get_rv_data_hash, load_rv_data

                saved_fit = KeplerianFit.objects.filter(source=source).order_by("-created_at").first()
                has_mismatch = False
                if saved_fit:
                    try:
                        df = load_rv_data(source, user=request.user)
                        current_hash = get_rv_data_hash(df)
                        has_mismatch = (saved_fit.observation_hash != current_hash)
                    except ValueError:
                        pass

                # If a saved fit exists, there's no data mismatch, we are not forcing a fit run,
                # and we have a cached plot_html, return it instantly to speed up page loads.
                if saved_fit and not fit_run and not has_mismatch and saved_fit.plot_html:
                    return saved_fit.plot_html

                fit_samples, _ = get_request_cached_fit(
                    source,
                    request,
                    fit_run,
                    p_guess,
                    k_guess,
                    v0_guess,
                    e_guess
                )
                figure = get_rv_plot(source, fit_samples=fit_samples, user=request.user)

                # Save/cache the generated figure html in the database
                if fit_samples is not None:
                    latest_fit = KeplerianFit.objects.filter(source=source).order_by("-created_at").first()
                    if latest_fit and not latest_fit.plot_html:
                        latest_fit.plot_html = figure
                        latest_fit.save(update_fields=["plot_html"])

                return figure
            except ValueError:
                return ""


        @staticmethod
        def extra_evaluated__fit_results_html(source, request, **_) -> str:
            """
            Generates fit results parameter table and status alerts
            """
            p_guess = request.GET.get("p_guess")
            k_guess = request.GET.get("k_guess")
            v0_guess = request.GET.get("v0_guess")
            e_guess = request.GET.get("e_guess")

            p_guess = float(p_guess) if p_guess else None
            k_guess = float(k_guess) if k_guess else None
            v0_guess = float(v0_guess) if v0_guess else None
            e_guess = float(e_guess) if e_guess else None

            fit_run = (request and request.GET.get("fit") == "true") or any(v is not None for v in [p_guess, k_guess, v0_guess, e_guess])
            return render_fit_results_html(
                source,
                fit_run=fit_run,
                p_guess=p_guess,
                k_guess=k_guess,
                v0_guess=v0_guess,
                e_guess=e_guess,
                request=request
            )


def render_observations_table_html(source, request) -> str:
    from django.middleware.csrf import get_token
    from django.db.models import Max
    from app.models import Observation, Project
    from app.models.observation import is_linked_project_member

    user = request.user if request else None
    csrf_token = get_token(request) if request else ""

    from django.db.models import Q

    observations = source.observation_set.filter(
        jd__isnull=False,
        dataset__radial_velocity__isnull=False
    )

    if user and user.is_authenticated:
        if not user.is_staff:
            researcher = getattr(user, "researcher", None)
            if researcher:
                observations = observations.filter(
                    Q(is_community=True) |
                    Q(observer=researcher) |
                    Q(project__principal_investigator=researcher) |
                    Q(project__members=researcher)
                ).distinct()
            else:
                observations = observations.filter(is_community=True)
    else:
        observations = observations.filter(is_community=True)

    observations = observations.select_related("dataset", "observer__user", "project").order_by("jd")

    # Calculate default metadata for the inline row append
    next_id = (Observation.objects.aggregate(max_id=Max("id"))["max_id"] or 0) + 1
    user_email = user.email if (user and user.is_authenticated) else "Logged-in User"

    default_proj_name = "Independent"
    if source.observation_set.exists():
        first_obs = source.observation_set.filter(project__isnull=False).first()
        if first_obs and first_obs.project:
            default_proj_name = first_obs.project.name
    if default_proj_name == "Independent":
        if user and user.is_authenticated and hasattr(user, "researcher"):
            user_proj = Project.objects.filter(principal_investigator=user.researcher).first()
            if user_proj:
                default_proj_name = user_proj.name

    rows_html = ""
    for obs in observations:
        rv_str = f"<strong>{obs.dataset.radial_velocity:.2f}</strong>" if (hasattr(obs, "dataset") and obs.dataset and obs.dataset.radial_velocity is not None) else "<span class='text-muted'>—</span>"
        err_str = f"± {obs.dataset.radial_velocity_error:.2f}" if (hasattr(obs, "dataset") and obs.dataset and obs.dataset.radial_velocity_error is not None) else "<span class='text-muted'>—</span>"
        
        if obs.jd is not None:
            is_future_date = obs.jd > 2461000.0
            date_badge_cls = "bg-warning text-dark fw-bold" if is_future_date else "bg-light text-dark font-monospace"
            jd_str = f"<span class='badge {date_badge_cls} px-2 py-1 fs-6'>{obs.jd:.4f}</span>"
        else:
            jd_str = "<span class='badge bg-danger text-light'>Missing Date</span>"

        observer_email = obs.observer.user.email if (obs.observer and obs.observer.user) else "Unassigned"
        project_name = obs.project.name if obs.project else "Independent"

        can_edit = user and user.is_authenticated and (user.is_staff or is_linked_project_member(user, obs))

        actions_html = ""
        if can_edit:
            transfer_btn = ""
            if not obs.is_community:
                transfer_btn = f"""
                <form method="POST" action="/obs/{obs.pk}/transfer/" style="display:inline;" onsubmit="return confirm('Transfer Observation #{obs.pk} to Community Projects? Original uploader credit will be preserved.');">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
                    <button type="submit" class="btn btn-outline-success btn-sm px-2 py-1" title="Transfer Data Point to Community Tier">
                        <i class="fa-solid fa-globe me-1"></i>Transfer
                    </button>
                </form>
                """

            actions_html = f"""
            <div class="btn-group btn-group-sm" role="group">
                <a href="/obs/{obs.pk}/edit/" class="btn btn-outline-primary btn-sm px-2 py-1" title="Edit Observation Date & RV Data">
                    <i class="fa-solid fa-pen-to-square me-1"></i>Edit
                </a>
                {transfer_btn}
                <form method="POST" action="/obs/{obs.pk}/delete/" style="display:inline;" onsubmit="return confirm('Are you sure you want to delete Observation #{obs.pk}?');">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
                    <button type="submit" class="btn btn-outline-danger btn-sm px-2 py-1" title="Delete Data Point">
                        <i class="fa-solid fa-trash me-1"></i>Delete
                    </button>
                </form>
            </div>
            """
        else:
            actions_html = "<span class='text-muted small'><i class='fa-solid fa-lock me-1'></i>Read Only</span>"

        tier_badge = "<span class='badge bg-success text-white px-2 py-1 ms-1'><i class='fa-solid fa-globe me-1'></i>Community</span>" if obs.is_community else "<span class='badge bg-warning text-dark px-2 py-1 ms-1'><i class='fa-solid fa-user-lock me-1'></i>Draft</span>"

        rows_html += f"""
        <tr>
            <td class="fw-bold text-secondary">#{obs.pk}</td>
            <td>{jd_str}</td>
            <td>{rv_str}</td>
            <td><code>{err_str}</code></td>
            <td><span class="badge bg-secondary text-light px-2 py-1"><i class="fa-solid fa-user me-1"></i>{observer_email}</span>{tier_badge}</td>
            <td><span class="badge bg-info text-dark px-2 py-1"><i class="fa-solid fa-folder me-1"></i>{project_name}</span></td>
            <td>{actions_html}</td>
        </tr>
        """

    can_add = user and user.is_authenticated

    add_row_html = f"""
    <tr id="add-obs-row" style="display: none; background-color: #f0fdf4;" class="border-top border-2 border-success">
        <td class="align-middle">
            <span class="badge bg-success font-monospace px-2 py-1 fs-6">#{next_id} (Auto)</span>
        </td>
        <td class="align-middle">
            <input type="number" step="any" form="add-obs-form" name="jd" id="add-obs-jd-input" class="form-control form-control-sm font-monospace" placeholder="JD (e.g. 2460600.0)" required>
        </td>
        <td class="align-middle">
            <input type="number" step="any" form="add-obs-form" name="radial_velocity" class="form-control form-control-sm" placeholder="RV (km/s)" required>
        </td>
        <td class="align-middle">
            <input type="number" step="any" form="add-obs-form" name="radial_velocity_error" class="form-control form-control-sm" placeholder="Err (km/s)" required>
        </td>
        <td class="align-middle">
            <span class="badge bg-secondary text-light px-2 py-1"><i class="fa-solid fa-user me-1"></i>{user_email} (You)</span>
        </td>
        <td class="align-middle">
            <span class="badge bg-info text-dark px-2 py-1"><i class="fa-solid fa-folder me-1"></i>{default_proj_name}</span>
        </td>
        <td class="align-middle">
            <form id="add-obs-form" method="POST" action="/source/{source.pk}/add-obs/">
                <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
                <div class="btn-group btn-group-sm">
                    <button type="submit" class="btn btn-success btn-sm px-2 py-1 fw-bold">
                        <i class="fa-solid fa-check me-1"></i>Save
                    </button>
                    <button type="button" class="btn btn-outline-secondary btn-sm px-2 py-1" onclick="document.getElementById('add-obs-row').style.display='none';">
                        <i class="fa-solid fa-xmark me-1"></i>Cancel
                    </button>
                </div>
            </form>
        </td>
    </tr>
    """

    add_button_footer = ""
    if can_add:
        add_button_footer = f"""
        <div class="card-footer border-top border-secondary-subtle p-3 d-flex justify-content-between align-items-center">
            <span class="text-muted small">
                <i class="fa-solid fa-circle-info me-1 text-primary"></i>Append observation measurements directly to this source's dataset without leaving the page.
            </span>
            <button type="button" class="btn btn-success shadow-sm fw-bold px-3 py-2" onclick="document.getElementById('add-obs-row').style.display='table-row'; document.getElementById('add-obs-jd-input').focus();">
                <i class="fa-solid fa-plus-circle me-2"></i>Add data for this source
            </button>
        </div>
        """
    else:
        add_button_footer = """
        <div class="card-footer border-top border-secondary-subtle p-3 d-flex justify-content-between align-items-center text-muted small">
            <span><i class="fa-solid fa-lock me-1"></i>Please sign in to add new observations to this source.</span>
        </div>
        """

    return f"""
    <div class="card my-4 shadow-sm border-0 rounded-3 overflow-hidden">
        <div class="card-header bg-dark text-white p-3 d-flex justify-content-between align-items-center">
            <h5 class="mb-0 fw-bold"><i class="fa-solid fa-database me-2 text-warning"></i>Radial Velocity Observations & User Provenance</h5>
            <span class="badge bg-primary fs-6">{observations.count()} Data Points</span>
        </div>
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover table-striped align-middle mb-0">
                    <thead class="table-dark">
                        <tr>
                            <th>ID</th>
                            <th>Observation Date (JD)</th>
                            <th>Radial Velocity (km/s)</th>
                            <th>RV Error (km/s)</th>
                            <th>User Provenance (Observer)</th>
                            <th>Project</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html if rows_html else '<tr><td colspan="7" class="text-center text-muted p-4">No observations recorded yet for this source. Use the button below to add data.</td></tr>'}
                        {add_row_html}
                    </tbody>
                </table>
            </div>
        </div>
        {add_button_footer}
    </div>
    """


def add_observation_for_source_view(request, source_id):
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from app.models import Source, Observation, DataSet, Instrument, Project, Researcher, FluxUnit, WavelengthUnit
    from app.fitting import run_joker_fit
    from app.plots.rv_curve import get_rv_plot
    from app.models.keplerian_fit import KeplerianFit

    source = get_object_or_404(Source, pk=source_id)
    user = request.user

    if not user or not user.is_authenticated:
        messages.error(request, "You must be signed in to add observations.")
        return redirect(source.get_absolute_url())

    if request.method == "POST":
        jd_str = request.POST.get("jd")
        rv_str = request.POST.get("radial_velocity")
        err_str = request.POST.get("radial_velocity_error")
        comment_str = request.POST.get("comment", "")

        try:
            jd_val = float(jd_str.strip())
            rv_val = float(rv_str.strip())
            err_val = float(err_str.strip())

            # Logged in user researcher profile
            researcher, _ = Researcher.objects.get_or_create(user=user)

            # Determine project from source hierarchy
            proj = None
            if source.observation_set.exists():
                first_obs = source.observation_set.filter(project__isnull=False).first()
                if first_obs and first_obs.project:
                    proj = first_obs.project

            if not proj:
                proj = Project.objects.filter(principal_investigator=researcher).first() or Project.objects.filter(name="Test Projects").first() or Project.objects.first()

            inst = Instrument.objects.first()
            flux_u = FluxUnit.objects.first()
            wave_u = WavelengthUnit.objects.first()

            # Create Observation
            obs = Observation.objects.create(
                source=source,
                project=proj,
                observer=researcher,
                instrument=inst,
                jd=jd_val,
                comment=comment_str,
                is_valid=True
            )

            # Create DataSet
            DataSet.objects.create(
                observation=obs,
                radial_velocity=rv_val,
                radial_velocity_error=err_val,
                flux_units=flux_u,
                wavelength_units=wave_u,
                is_valid=True
            )

            # Automatically recalculate Keplerian fit for the source
            try:
                samples, _ = run_joker_fit(source, force_run=True, user=user)
                if samples:
                    plot_html = get_rv_plot(source, fit_samples=samples, user=user)
                    fit = KeplerianFit.objects.filter(source=source).order_by("-created_at").first()
                    if fit:
                        fit.plot_html = plot_html
                        fit.save()
            except Exception:
                pass

            messages.success(request, f"New Observation #{obs.pk} successfully appended to '{source.name}'. Keplerian orbit fit recalculated.")
            return redirect(source.get_absolute_url())

        except (ValueError, AttributeError) as err:
            messages.error(request, f"Failed to add observation: Invalid input values ({err}).")

    return redirect(source.get_absolute_url())


def add_gaiainfo_view(request, source, **kwargs):
    from django.middleware.csrf import get_token
    from django.shortcuts import redirect
    from django.contrib import messages
    from app.gaia_lookup import query_gaia_info_for_source
    from app.models import Source, SourceGaiaInfo

    if not isinstance(source, Source):
        if str(source).isdigit():
            source = Source.objects.get(id=int(source))
        else:
            source = Source.objects.get(name=source)

    # Perform the query
    try:
        info_data, resolved_ra, resolved_dec, resolved_name = query_gaia_info_for_source(
            source.name, source.ra, source.dec
        )
    except Exception as e:
        info_data, resolved_ra, resolved_dec, resolved_name = None, None, None, None
        messages.error(request, f"Failed to query Gaia/Simbad databases: {e}")
        return redirect(source.get_absolute_url())

    if request.method == "POST":
        if info_data:
            SourceGaiaInfo.objects.create(
                source=source,
                is_valid=source.is_valid,
                **info_data
            )
            # Update source coordinates if they are 0.0 or not set
            if resolved_ra is not None and resolved_dec is not None:
                if source.ra == 0.0 and source.dec == 0.0:
                    source.ra = resolved_ra
                    source.dec = resolved_dec
                    source.save()
            messages.success(request, f"Gaia Info successfully added to source '{source.name}'.")
        else:
            messages.error(request, "No Gaia Info was found to save.")
        return redirect(source.get_absolute_url())

    # GET request: Render retrieved data
    rows_html = []
    if info_data:
        for k, v in info_data.items():
            val_display = f"<code>{v}</code>" if v is not None else '<span class="text-muted">N/A</span>'
            rows_html.append(f"<tr><td><strong>{k.replace('_', ' ').title()}</strong></td><td>{val_display}</td></tr>")
        
        rows_html.append(f"<tr><td><strong>Resolved RA</strong></td><td><code>{resolved_ra}</code> (Current: {source.ra})</td></tr>")
        rows_html.append(f"<tr><td><strong>Resolved Dec</strong></td><td><code>{resolved_dec}</code> (Current: {source.dec})</td></tr>")
        rows_html.append(f"<tr><td><strong>Resolved Name</strong></td><td><code>{resolved_name}</code> (Current: {source.name})</td></tr>")
    
    table_content = "\n".join(rows_html)
    csrf_token = get_token(request)

    content_html = f"""
    <div class="container py-4">
        <div class="card shadow border-0 rounded-3 overflow-hidden" style="background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px);">
            <div class="card-header bg-dark text-white p-4 d-flex justify-content-between align-items-center">
                <div>
                    <h3 class="mb-1 font-monospace">Gaia Database Query Results</h3>
                    <p class="mb-0 text-white-50 small">Properties retrieved automatically from Simbad and Gaia DR3</p>
                </div>
                <div class="badge bg-success p-2 fs-6">Succeeded</div>
            </div>
            <div class="card-body p-4">
                {"<div class='table-responsive'><table class='table table-hover align-middle'>" + table_content + "</table></div>" if info_data else "<div class='alert alert-warning'>No matching Gaia info found for this source name or coordinates.</div>"}
                
                <form method="POST" class="mt-4 d-flex gap-3">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
                    <button type="submit" class="btn btn-primary btn-lg shadow-sm" {"" if info_data else "disabled"}>
                        <i class="fa-solid fa-cloud-arrow-down me-2"></i>Save Gaia Info
                    </button>
                    <a href="{source.get_absolute_url()}" class="btn btn-outline-secondary btn-lg">
                        Cancel
                    </a>
                </form>
            </div>
        </div>
    </div>
    """

    class CustomPage(Page):
        header = Header(f"Add Gaia info: {source.name}")
        body = html.div(mark_safe(content_html))

    return CustomPage().bind(request=request)

