from django.db.models import Q
import csv
import io
import yaml
from django.db import transaction
from django.contrib import messages
from django.shortcuts import redirect
from iommi import Form, Field, Page, Header, html

from app.models import Source, Instrument, Project, Proposal, Observation, DataSet


def parse_yaml_csv_data(text_content, user, default_source=None, default_project=None, default_instrument=None):
    """
    Parses YAML-embedded CSV input or direct CSV input.
    Returns a list of created Observation objects or raises ValueError on validation errors.
    """
    metadata = {}
    csv_text = text_content.strip()

    # 1. Parse YAML front matter if it exists
    if csv_text.startswith("---"):
        parts = csv_text.split("---", 2)
        if len(parts) >= 3:
            try:
                yaml_data = yaml.safe_load(parts[1])
                if isinstance(yaml_data, dict):
                    metadata = {k.strip().lower(): v for k, v in yaml_data.items()}
                csv_text = parts[2].strip()
            except Exception as e:
                raise ValueError(f"Failed to parse YAML front matter: {e}")

    # 2. Extract metadata keys or fallback to overrides
    source_name = metadata.get("source") or (default_source.name if default_source else None)
    project_name = metadata.get("project") or (default_project.name if default_project else None)
    instrument_name = metadata.get("instrument") or (default_instrument.name if default_instrument else None)
    proposal_id = metadata.get("proposal")

    def parse_float(val):
        if val is None or str(val).strip() == "":
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    ra_val = parse_float(metadata.get("ra"))
    dec_val = parse_float(metadata.get("dec"))

    # Resolve project if specified
    project = None
    if project_name:
        try:
            project = Project.objects.get(name__iexact=project_name)
        except Project.DoesNotExist:
            if not user.is_staff:
                if not hasattr(user, "researcher"):
                    raise ValueError("Only registered researchers can create a new project during upload.")
                project = Project.objects.create(
                    name=project_name,
                    description=f"Auto-created during upload by {user.username}",
                    principal_investigator=user.researcher,
                    is_valid=False
                )
            else:
                researcher = getattr(user, "researcher", None)
                if not researcher:
                    from app.models import Researcher
                    researcher = Researcher.objects.first()
                if not researcher:
                    raise ValueError("At least one Researcher must exist in the database to assign as PI.")
                project = Project.objects.create(
                    name=project_name,
                    description=f"Auto-created during upload by staff {user.username}",
                    principal_investigator=researcher,
                    is_valid=True
                )

        # Verify project permission
        if not user.is_staff:
            if not hasattr(user, "researcher"):
                raise ValueError("Only registered researchers can upload observations to a project.")
            researcher = user.researcher
            is_member = (project.principal_investigator == researcher) or project.members.filter(pk=researcher.pk).exists()
            if not is_member:
                raise ValueError(f"You do not have permission to add observations to project '{project.name}'.")

    # Resolve proposal if specified
    proposal = None
    if proposal_id:
        try:
            proposal = Proposal.objects.get(pk=proposal_id)
        except Proposal.DoesNotExist:
            raise ValueError(f"Proposal ID {proposal_id} does not exist.")

    # 3. Read CSV data
    f = io.StringIO(csv_text)
    reader = csv.reader(f)
    try:
        header = next(reader)
    except StopIteration:
        raise ValueError("The uploaded data contains no headers or rows.")

    # Normalize headers
    header_map = {}
    for idx, col in enumerate(header):
        normalized = col.strip().lower().replace("_", "").replace(" ", "")
        header_map[normalized] = idx

    def find_header_index(keys, header_map):
        for key in keys:
            if key in header_map:
                return header_map[key]
        return None

    # Check headers
    jd_idx = find_header_index(["jd", "hjd", "mjd", "time", "date"], header_map)
    rv_idx = find_header_index(["rv", "radialvelocity", "vrad"], header_map)
    err_idx = find_header_index(["rverr", "radialvelocityerror", "rverror", "err", "error", "vraderr"], header_map)
    source_col_idx = header_map.get("source")
    inst_col_idx = header_map.get("instrument")

    if jd_idx is None:
        raise ValueError("Missing time column. CSV headers must include one of: JD, HJD, MJD, Time")
    if rv_idx is None:
        raise ValueError("Missing radial velocity column. CSV headers must include one of: RV, Radial Velocity")
    if err_idx is None:
        raise ValueError("Missing RV error column. CSV headers must include one of: RV Error, Error, RV Err")

    # Check default instrument resolver
    base_instrument = None
    if instrument_name:
        base_instrument, _ = Instrument.objects.get_or_create(
            name=instrument_name,
            defaults={"type": "e", "is_valid": True, "observatory": "Unknown"}
        )

    observations_created = []

    # Process rows inside an atomic transaction
    with transaction.atomic():
        for row_num, row in enumerate(reader, start=2):
            if not row or all(not val.strip() for val in row):
                continue

            if len(row) <= max(jd_idx, rv_idx, err_idx):
                raise ValueError(f"Row {row_num} has fewer columns than expected.")

            try:
                jd_val = float(row[jd_idx].strip())
                rv_val = float(row[rv_idx].strip())
                err_val = float(row[err_idx].strip())
            except ValueError:
                raise ValueError(f"Row {row_num}: Non-numeric value found (JD={row[jd_idx]}, RV={row[rv_idx]}, Err={row[err_idx]})")

            # Determine source for this row
            row_source_name = source_name
            if source_col_idx is not None and len(row) > source_col_idx:
                val = row[source_col_idx].strip()
                if val:
                    row_source_name = val

            if not row_source_name:
                raise ValueError(f"Row {row_num}: Source name not specified in YAML header, form, or CSV row.")

            # Get or create source
            is_staff_user = user.is_staff if user else False
            source, created = Source.objects.get_or_create(
                name=row_source_name,
                defaults={
                    "is_valid": is_staff_user,
                    "ra": ra_val or 0.0,
                    "dec": dec_val or 0.0,
                    "created_by": user.researcher if user and hasattr(user, "researcher") else None
                }
            )

            if created or (ra_val is not None and dec_val is not None and (source.ra == 0.0 and source.dec == 0.0)):
                if ra_val is not None and dec_val is not None:
                    source.ra = ra_val
                    source.dec = dec_val
                    source.save()
                from app.gaia_lookup import query_and_save_gaia_info
                query_and_save_gaia_info(source, user, ra=ra_val, dec=dec_val)
            elif not hasattr(source, "gaiainfo"):
                from app.gaia_lookup import query_and_save_gaia_info
                query_and_save_gaia_info(source, user, ra=ra_val, dec=dec_val)

            # Determine instrument for this row
            row_inst = base_instrument
            if inst_col_idx is not None and len(row) > inst_col_idx:
                val = row[inst_col_idx].strip()
                if val:
                    row_inst, _ = Instrument.objects.get_or_create(
                        name=val,
                        defaults={"type": "e", "is_valid": True, "observatory": "Unknown"}
                    )

            if not row_inst:
                raise ValueError(f"Row {row_num}: Instrument not specified in YAML header, form, or CSV row.")

            # Create Observation
            obs = Observation.objects.create(
                source=source,
                proposal=proposal,
                instrument=row_inst,
                project=project,
                observer=user.researcher if user and hasattr(user, "researcher") else None,
                jd=jd_val,
                is_valid=True,
                comment=f"Uploaded by {user.username if user else 'anonymous'} via YAML/CSV flow"
            )

            # Create DataSet
            DataSet.objects.create(
                observation=obs,
                flux_col="flux",
                flux_units_id=1,
                wavelength_col="wavelength",
                wavelength_units_id=1,
                radial_velocity=rv_val,
                radial_velocity_error=err_val,
                is_valid=is_staff_user,
                arxiv_url=metadata.get("arxiv") or metadata.get("arxiv_url"),
                ads_url=metadata.get("ads") or metadata.get("ads_url"),
                doi=metadata.get("doi"),
                bibtex=metadata.get("bibtex")
            )

            observations_created.append(obs)

    return observations_created


def handle_upload_submit(form, request):
    if not form.is_valid():
        return

    user = request.user
    fields = form.fields

    project = fields.project.value
    source = fields.source.value
    instrument = fields.instrument.value
    uploaded_file = fields.file.value
    text_data = fields.text_data.value

    content = ""
    if uploaded_file:
        try:
            content = uploaded_file.read().decode("utf-8")
        except Exception as e:
            messages.error(request, f"Failed to read uploaded file: {e}")
            return
    elif text_data:
        content = text_data
    else:
        messages.error(request, "Please either upload a CSV file or paste YAML/CSV data in the text area.")
        return

    try:
        observations = parse_yaml_csv_data(
            text_content=content,
            user=user,
            default_source=source,
            default_project=project,
            default_instrument=instrument
        )
    except Exception as e:
        messages.error(request, f"Ingestion failed: {e}")
        return

    # Trigger fit recalculations for all unique sources modified
    unique_sources = {obs.source for obs in observations}
    fit_errors = []

    from app.fitting import run_joker_fit
    from app.plots.rv_curve import get_rv_plot
    from app.models.keplerian_fit import KeplerianFit

    for src in unique_sources:
        try:
            samples, _ = run_joker_fit(src, prior_samples=100000, user=user)
            if samples:
                plot_html = get_rv_plot(src, fit_samples=samples, user=user)
                # Save/Update the cached KeplerianFit entry
                fit = KeplerianFit.objects.filter(source=src).latest("created_at")
                fit.plot_html = plot_html
                fit.save()
        except Exception as fit_err:
            fit_errors.append(f"Fit update failed for {src.name}: {fit_err}")

    success_msg = f"Successfully ingested {len(observations)} observations across {len(unique_sources)} source(s)."
    if fit_errors:
        success_msg += " Note: " + "; ".join(fit_errors)

    messages.success(request, success_msg)

    if len(unique_sources) == 1:
        return redirect(list(unique_sources)[0].get_absolute_url())
    return redirect("/")


class UploadPage(Page):
    """
    Page view for uploading Radial Velocity data blocks/files.
    """

    header = Header("Upload Radial Velocity Data")

    instructions = html.div(
        attrs__class={"card mb-4": True},
        children=dict(
            header=html.div(
                html.h4("Upload Formats & Instructions", attrs__class={"card-title mb-0": True}),
                attrs__class={"card-header bg-dark text-white": True},
            ),
            body=html.div(
                children=dict(
                    p1=html.p(
                        "You can upload Radial Velocity (RV) datasets either by uploading a CSV file "
                        "or pasting the content directly into the text box below. "
                        "Attribution can be specified directly inside the file using YAML headers, "
                        "or overridden using the dropdown choices."
                    ),
                    h5_yaml=html.h5("Option A: YAML Metadata Header + CSV Data"),
                    pre_yaml=html.pre(
                        "---\n"
                        "Source: Gaia-BH1\n"
                        "Instrument: ESPRESSO\n"
                        "Project: Gaia-BH1-Precision-RVs\n"
                        "---\n"
                        "HJD, RV, RV_Error\n"
                        "2459791.9186, 131.9, 0.1\n"
                        "2459823.8525, 53.76, 0.1\n",
                        attrs__style={
                            "background-color": "#f1f5f9",
                            "padding": "1rem",
                            "border-radius": "8px",
                            "border": "1px solid #e2e8f0",
                            "font-family": "monospace",
                        }
                    ),
                    h5_csv=html.h5("Option B: Multi-Source CSV File"),
                    pre_csv=html.pre(
                        "Source, HJD, RV, RV_Error, Instrument\n"
                        "Gaia-BH1, 2459791.9186, 131.9, 0.1, ESPRESSO\n"
                        "Gaia-BH2, 2459823.8525, 53.76, 0.1, HIRES\n",
                        attrs__style={
                            "background-color": "#f1f5f9",
                            "padding": "1rem",
                            "border-radius": "8px",
                            "border": "1px solid #e2e8f0",
                            "font-family": "monospace",
                        }
                    ),
                ),
                attrs__class={"card-body": True},
            )
        )
    )

    form = Form(
        attrs__onsubmit="""
            // Prevent double submission if button text is already modified
            let btn = this.querySelector('button[type=\"submit\"]');
            if (btn && btn.disabled) return false;
            
            // Show patience message
            let container = this.querySelector('.card-body') || this;
            let existing = document.getElementById('patience-alert');
            if (!existing) {
                let alertDiv = document.createElement('div');
                alertDiv.id = 'patience-alert';
                alertDiv.className = 'alert alert-info d-flex align-items-center mt-3';
                alertDiv.innerHTML = `
                    <div class="spinner-border spinner-border-sm me-3 text-info" role="status"></div>
                    <div>
                        <strong>Validation successful!</strong> Please be patient while data ingestion and Keplerian orbit refitting are ongoing...
                    </div>
                `;
                container.appendChild(alertDiv);
            }
            if (btn) {
                btn.innerHTML = '✨ Processing... Please wait...';
                // Wait slightly to disable, so form submission registers
                setTimeout(() => { btn.disabled = true; }, 50);
            }
            return true;
        """,
        fields=dict(
            project=Field.choice_queryset(
                choices=Project.objects.filter(is_valid=True),
                required=False,
                help_text="Optional. Default project to attribute these observations to if not specified in YAML."
            ),
            source=Field.choice_queryset(
                model=Source,
                choices=lambda request, **_: (
                    Source.objects.all() if request.user.is_staff else (
                        Source.objects.filter(
                            Q(is_valid=True) | Q(created_by=request.user.researcher)
                        ).distinct() if request.user.is_authenticated and hasattr(request.user, "researcher") else Source.objects.filter(is_valid=True)
                    )
                ),
                required=False,
                help_text="Optional. Default source if not specified in YAML or CSV rows."
            ),
            instrument=Field.choice_queryset(
                choices=Instrument.objects.filter(is_valid=True),
                required=False,
                help_text="Optional. Default instrument if not specified in YAML or CSV rows."
            ),
            file=Field.file(
                required=False,
                help_text="Upload a CSV file containing observations."
            ),
            text_data=Field.textarea(
                required=False,
                help_text="Or copy-paste the CSV/YAML data block here."
            )
        ),
        actions__submit__post_handler=lambda form, request, **_: handle_upload_submit(form, request)
    )
