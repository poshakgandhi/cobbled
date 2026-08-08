from django.utils.safestring import mark_safe
from iommi import Fragment, Header, Page, html
from iommi._web_compat import Template

from app.forms.observation import DatasetForm, ObservationForm
from app.plots.spectrum import get_spectrum_plot


class ObservationViewPage(Page):
    """
    The basic view for an observation.
    """

    header = Header(
        lambda observation,
        **_: f"{observation.get_instrument} observation of {observation.source}"
    )
    detail = ObservationForm(
        auto__exclude=["is_valid"],
        instance=lambda observation, **_: observation,
        editable=False,
    )
    data_plot = Fragment(
        Template("{{ page.extra_evaluated.data_plot | safe }}"),
        include=lambda user, observation, **_: hasattr(observation, "dataset")
        and (observation.dataset.is_valid or user.is_staff)
        and (user.has_perm("app.view_dataset", observation.dataset)),
    )
    dataset = DatasetForm(
        auto__exclude=[
            "observation",
            "upload",
            "arxiv_url",
            "ads_url",
            "bibtex",
            "flux_col",
            "flux_err_col",
            "flux_units",
            "wavelength_col",
            "wavelength_units",
            "is_valid",
        ],
        include=lambda user, observation, **_: hasattr(observation, "dataset")
        and (observation.dataset.is_valid or user.is_staff)
        and (user.has_perm("app.view_dataset", observation.dataset)),
        instance=lambda observation, **_: observation.dataset,
        editable=False,
    )

    class Meta:
        @staticmethod
        def extra_evaluated__data_plot(observation, **_) -> str:
            """
            Generates and renders the plot for a given spectrum dataset if relevant data is present
            """
            try:
                # Get the vpec_vs_gamma plot
                figure = get_spectrum_plot(observation)
                return figure
            except ValueError:
                # If plot could not be generated (if source has no DataSet or there's no file to draw from), skip and return an empty fragment
                return ""


def edit_observation_view(request, obs_id):
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from django.middleware.csrf import get_token
    from app.models import Observation, DataSet
    from app.models.observation import is_linked_project_member
    from app.fitting import run_joker_fit
    from app.plots.rv_curve import get_rv_plot
    from app.models.keplerian_fit import KeplerianFit

    obs = get_object_or_404(Observation, pk=obs_id)
    source = obs.source

    # Verify permission
    can_edit = request.user.is_staff or is_linked_project_member(request.user, obs)
    if not can_edit:
        messages.error(request, "You do not have permission to edit this observation data point.")
        return redirect(source.get_absolute_url())

    dataset = getattr(obs, "dataset", None)

    if request.method == "POST":
        jd_str = request.POST.get("jd")
        rv_str = request.POST.get("radial_velocity")
        err_str = request.POST.get("radial_velocity_error")
        comment_str = request.POST.get("comment")

        try:
            if jd_str and jd_str.strip():
                obs.jd = float(jd_str.strip())
            else:
                obs.jd = None
            obs.comment = comment_str
            obs.save()

            if dataset:
                if rv_str and rv_str.strip():
                    dataset.radial_velocity = float(rv_str.strip())
                else:
                    dataset.radial_velocity = None

                if err_str and err_str.strip():
                    dataset.radial_velocity_error = float(err_str.strip())
                else:
                    dataset.radial_velocity_error = None
                dataset.save()
            else:
                if (rv_str and rv_str.strip()) or (err_str and err_str.strip()):
                    from app.models import FluxUnit, WavelengthUnit
                    dataset = DataSet.objects.create(
                        observation=obs,
                        radial_velocity=float(rv_str.strip()) if rv_str and rv_str.strip() else None,
                        radial_velocity_error=float(err_str.strip()) if err_str and err_str.strip() else None,
                        flux_units=FluxUnit.objects.first(),
                        wavelength_units=WavelengthUnit.objects.first(),
                        is_valid=True
                    )

            # Re-run Joker fit for source to update plot and parameters
            try:
                samples, _ = run_joker_fit(source, force_run=True, user=request.user)
                if samples:
                    plot_html = get_rv_plot(source, fit_samples=samples, user=request.user)
                    fit = KeplerianFit.objects.filter(source=source).order_by("-created_at").first()
                    if fit:
                        fit.plot_html = plot_html
                        fit.save()
            except Exception:
                pass

            messages.success(request, f"Observation #{obs.pk} for '{source.name}' successfully updated. Keplerian fit recalculated.")
            return redirect(source.get_absolute_url())

        except ValueError as val_err:
            messages.error(request, f"Invalid numerical value: {val_err}")

    observer_name = obs.observer.user.get_full_name() or obs.observer.user.email if (obs.observer and obs.observer.user) else "Unassigned"
    jd_val = obs.jd if obs.jd is not None else ""
    rv_val = dataset.radial_velocity if (dataset and dataset.radial_velocity is not None) else ""
    err_val = dataset.radial_velocity_error if (dataset and dataset.radial_velocity_error is not None) else ""
    comment_val = obs.comment or ""
    csrf_token = get_token(request)

    form_html = f"""
    <div class="container py-4">
        <div class="card shadow-lg border-0 rounded-3" style="max-width: 650px; margin: 0 auto;">
            <div class="card-header bg-primary text-white p-3 d-flex justify-content-between align-items-center">
                <h4 class="mb-0 fw-bold"><i class="fa-solid fa-pen-to-square me-2"></i>Edit Observation #{obs.pk}</h4>
                <span class="badge bg-light text-primary">Source: {source.name}</span>
            </div>
            <div class="card-body p-4">
                <div class="alert alert-info py-2 px-3 mb-4 small d-flex align-items-center">
                    <i class="fa-solid fa-user-check me-2 fs-5"></i>
                    <div>
                        <strong>User Provenance:</strong> Data point entered by <code>{observer_name}</code> under project <code>{obs.project.name if obs.project else "Independent"}</code>.
                    </div>
                </div>

                <form method="POST">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
                    
                    <div class="mb-3">
                        <label class="form-label fw-bold">Observation Date (Julian Date JD)</label>
                        <input type="number" step="any" name="jd" value="{jd_val}" class="form-control" placeholder="e.g. 2460591.0" required>
                        <div class="form-text">Correct any typos in Julian Date. E.g. fix an extra digit.</div>
                    </div>

                    <div class="row g-3 mb-3">
                        <div class="col-md-6">
                            <label class="form-label fw-bold">Radial Velocity (km/s)</label>
                            <input type="number" step="any" name="radial_velocity" value="{rv_val}" class="form-control" placeholder="e.g. 150.0">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-bold">RV Error (km/s)</label>
                            <input type="number" step="any" name="radial_velocity_error" value="{err_val}" class="form-control" placeholder="e.g. 2.5">
                        </div>
                    </div>

                    <div class="mb-4">
                        <label class="form-label fw-bold">Comment / Note</label>
                        <textarea name="comment" class="form-control" rows="2" placeholder="Optional notes...">{comment_val}</textarea>
                    </div>

                    <div class="d-flex justify-content-between align-items-center">
                        <a href="{source.get_absolute_url()}" class="btn btn-outline-secondary">
                            <i class="fa-solid fa-xmark me-1"></i>Cancel
                        </a>
                        <button type="submit" class="btn btn-primary px-4">
                            <i class="fa-solid fa-floppy-disk me-2"></i>Save Changes & Recalculate Fit
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    """

    class EditPage(Page):
        header = Header(f"Edit Observation #{obs.pk}")
        body = html.div(mark_safe(form_html))

    return EditPage().bind(request=request)


def delete_observation_view(request, obs_id):
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from app.models import Observation
    from app.models.observation import is_linked_project_member
    from app.fitting import run_joker_fit, get_rv_plot
    from app.models.keplerian_fit import KeplerianFit

    obs = get_object_or_404(Observation, pk=obs_id)
    source = obs.source

    can_edit = request.user.is_staff or is_linked_project_member(request.user, obs)
    if not can_edit:
        messages.error(request, "You do not have permission to delete this observation data point.")
        return redirect(source.get_absolute_url())

    if request.method == "POST":
        obs_pk = obs.pk
        obs.delete()
        
        # Re-run Joker fit for source to update plot and parameters
        try:
            samples, _ = run_joker_fit(source, force_run=True, user=request.user)
            if samples:
                plot_html = get_rv_plot(source, fit_samples=samples, user=request.user)
                fit = KeplerianFit.objects.filter(source=source).order_by("-created_at").first()
                if fit:
                    fit.plot_html = plot_html
                    fit.save()
        except Exception:
            pass

        messages.success(request, f"Observation #{obs_pk} deleted. Keplerian fit recalculated.")
        return redirect(source.get_absolute_url())

    messages.error(request, "Invalid request method for deletion.")
    return redirect(source.get_absolute_url())
