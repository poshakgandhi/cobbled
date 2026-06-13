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


def render_fit_parameters_table(parameters) -> str:
    rows = ""
    for p in parameters:
        unit_str = f" ({p['unit']})" if p['unit'] else ""
        rows += f"""
        <tr>
            <td><strong>{p['name']}</strong>{unit_str}</td>
            <td><code>{p['val']}</code></td>
            <td><code>± {p['err']}</code></td>
            <td><code>{p['ci']}</code></td>
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


def render_fit_results_html(source, fit_run=False, p_guess=None, k_guess=None, v0_guess=None, e_guess=None, user=None) -> str:
    from app.models.keplerian_fit import KeplerianFit
    from app.fitting import get_fit_results, get_rv_data_hash, load_rv_data

    # Check minimum observation requirement
    try:
        df = load_rv_data(source, user=user)
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

    # Determine if we should display a fit (either newly run, or loaded from DB)
    display_samples = None
    display_parameters = None
    status_alert = ""

    if fit_run:
        # User requested a new fit
        samples, parameters = get_fit_results(
            source,
            force_run=True,
            p_guess=p_guess,
            k_guess=k_guess,
            v0_guess=v0_guess,
            e_guess=e_guess,
            user=user
        )
        if samples is not None:
            display_samples = samples
            display_parameters = parameters
            status_alert = f"""
            <div class="alert alert-success d-flex align-items-center mb-4" role="alert">
                <div class="me-3">
                    <span class="fs-4">🚀</span>
                </div>
                <div>
                    <h5 class="alert-heading mb-1 fw-bold">Keplerian Fit Successful!</h5>
                    <p class="mb-0">The Joker completed rejection sampling successfully and returned {len(samples)} posterior orbits. The results have been saved to the database.</p>
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
    elif saved_fit:
        # Load from database automatically
        from app.fitting import deserialize_samples
        display_samples = deserialize_samples(saved_fit.sample_bundle)
        display_parameters = saved_fit.fit_parameters

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
            t_last = Time.now().jd
            jd_min = df["jd"].min()
            planning_dates = get_planning_dates(display_samples, t_last, jd_min)
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

    return f"""
    {form_html}
    {status_alert}
    <h5 class="fw-bold mb-3"><i class="fa-solid fa-list-check me-2"></i>Fitted Orbital Parameters</h5>
    {table_html}
    {planning_html}
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

                from app.fitting import get_fit_results
                fit_samples, _ = get_fit_results(
                    source,
                    force_run=fit_run,
                    p_guess=p_guess,
                    k_guess=k_guess,
                    v0_guess=v0_guess,
                    e_guess=e_guess,
                    user=request.user
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
                user=request.user
            )


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

