import os
import sys
import django
import csv

# Set up Django environment
sys.path.append("/soft/cobbled/cobbled")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from app.models import Source, Instrument, Observation, DataSet, Project, FluxUnit, WavelengthUnit
from app.fitting import run_joker_fit
from app.plots.rv_curve import get_rv_plot
from app.models.keplerian_fit import KeplerianFit


def import_bh1():
    print("Starting Gaia-BH1 import...")
    
    # 1. Create or get Gaia-BH1 Source
    source, created = Source.objects.get_or_create(
        name="Gaia-BH1",
        defaults={
            "is_valid": True,
            "ra": 262.1712359,
            "dec": -0.5809787,
        }
    )
    if created:
        print("Created Source: Gaia-BH1")
    else:
        print("Gaia-BH1 Source already exists")

    # 2. Get or create Gaia BHs Project
    project, _ = Project.objects.get_or_create(
        name="Gaia BHs",
        defaults={
            "description": "Public community datasets for Gaia Black Hole binaries.",
            "is_community": True,
            "is_valid": True,
        }
    )
    project.is_community = True
    project.save()

    # 3. Read CSV file
    csv_path = "/soft/cobbled/cobbled/app/fixtures/gaia_bh1_rvs.csv"
    if not os.path.exists(csv_path):
        print(f"Error: CSV path {csv_path} does not exist.")
        return

    with open(csv_path, "r") as f:
        lines = f.readlines()

    data_lines = []
    header_found = False
    for line in lines:
        if "HJD,RV,RV Error,Instrument" in line:
            header_found = True
            continue
        if header_found and line.strip():
            data_lines.append(line.strip())

    print(f"Found {len(data_lines)} data points to import.")

    # Delete any existing observations for Gaia-BH1 to avoid duplicates
    Observation.objects.filter(source=source).delete()

    flux_u = FluxUnit.objects.first()
    wave_u = WavelengthUnit.objects.first()

    reader = csv.reader(data_lines)
    count = 0
    for row in reader:
        if len(row) < 4:
            continue
        hjd = float(row[0])
        rv = float(row[1])
        rv_err = float(row[2])
        inst_name = row[3].strip()

        instrument, _ = Instrument.objects.get_or_create(
            name=inst_name,
            defaults={
                "type": "e",
                "spectral_resolution": 0.05 if inst_name == "ESPRESSO" else 0.1,
                "observatory": "Paranal" if inst_name in ["ESPRESSO", "FEROS"] else "Keck",
                "is_valid": True
            }
        )

        obs = Observation.objects.create(
            source=source,
            project=project,
            is_valid=True,
            is_community=True,
            jd=hjd,
            comment=f"Imported from {inst_name} high-precision spectrum"
        )

        DataSet.objects.create(
            observation=obs,
            upload=f"uploads/gaiabh1_{inst_name.lower()}.csv",
            flux_col="flux",
            flux_units=flux_u,
            wavelength_col="wavelength",
            wavelength_units=wave_u,
            radial_velocity=rv,
            radial_velocity_error=rv_err,
            is_valid=True
        )
        count += 1

    print(f"Successfully imported {count} radial velocity points for Gaia-BH1.")

    # 4. Pre-run Keplerian fit for Gaia-BH1
    print("Pre-running Keplerian fit for Gaia-BH1...")
    samples, params = run_joker_fit(
        source,
        prior_samples=100000,
        p_guess=185.6,
        k_guess=67.2,
        v0_guess=0.0,
        e_guess=0.45
    )
    if samples is not None:
        print("Fit successful! Generating pre-rendered plot...")
        plot_html = get_rv_plot(source, fit_samples=samples)

        fit = KeplerianFit.objects.filter(source=source).order_by("-created_at").first()
        if fit:
            fit.plot_html = plot_html
            fit.save(update_fields=["plot_html"])
        print("Gaia-BH1 fit and plot cached in the database.")
    else:
        print("Fit failed.")


if __name__ == "__main__":
    import_bh1()
