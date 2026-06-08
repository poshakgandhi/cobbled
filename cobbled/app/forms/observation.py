from zipfile import BadZipFile, ZipFile

import pandas as pd
from django.contrib import messages
from django.core.files import File as DjangoFile
from iommi import Field, Form

from app.models import DataSet, FluxUnit, Observation, Proposal, Source, WavelengthUnit


class DatasetForm(Form):
    """
    Form to add/view/edit a Dataset instance
    """

    class Meta:
        auto__model = DataSet


class ObservationForm(Form):
    """
    Form to add/view/edit an Observation instance
    """

    class Meta:
        auto__model = Observation


class BulkObservationForm(Form):
    """
    Form to deal with bulk observation upload, int he form of zipped csv files with an accompanying index.csv
    """

    proposal = Field.choice_queryset(choices=Proposal.objects.all(), editable=False)
    source = Field.choice_queryset(
        choices=Source.objects.filter(is_valid=True),
        help_text="The source which was observed in this batch of observations.",
    )
    upload_archive = Field.file(
        help_text="Upload a .zip or a .tar file containing a number of .csv or .fits spectra, along with a csv titled 'index.csv' which contains auxilliary information on each spectrum."
    )
    flux_col = Field(
        initial="flux",
        display_name="Flux Column",
        help_text="The name of the flux column in each spectrum.",
    )
    flux_err_col = Field(
        initial="flux_err",
        required=False,
        display_name="Flux Error Column",
        help_text="The name of the flux error column in each spectrum (set blank if no errors present).",
    )
    flux_units = Field.choice_queryset(choices=FluxUnit.objects.all())
    wavelength_col = Field(
        initial="wavelength",
        display_name="Wavelength Column",
        help_text="The name of the wavelength column in each spectrum.",
    )
    wavelength_units = Field.choice_queryset(choices=WavelengthUnit.objects.all())

    class Meta:
        # Define custom logic for handling bulk uploads
        def actions__submit__post_handler(form, request, user, **_):
            if not form.is_valid():
                return

            # Unpack critical info from form before trying anything fancy
            fields = form.fields

            # Attempt to unzip the archive in memory
            try:
                zipf = ZipFile(fields.upload_archive.value)
            except BadZipFile:
                messages.warning(request, "Could not open zip archive: no observations uploaded!")
                return

            # Attempt to load the index file from the archive and parse it
            try:
                indexfile = zipf.open("index.csv")
                indexdf = pd.read_csv(indexfile)

                # Check mandatory columns are present in the index df
                for key_column in ("file_name", "jd"):
                    assert key_column in indexdf.columns.values

            except KeyError:
                # No Index File error handling here
                messages.warning(request, "Could not find index.csv: no observations uploaded!")
                return

            except AssertionError:
                messages.warning(request, "Could not parse index.csv: no observations uploaded!")
                return

            succesful_observations = 0
            succesful_datafiles = 0

            # Create observation / observation-datafile pairs for each row in index.csv
            for _, row in indexdf.iterrows():
                try:
                    obs_object = Observation(
                        source=fields.source.value,
                        proposal=fields.proposal.value,
                        jd=row["jd"],
                    )

                except ValueError:
                    # If the row data in the index csv is malformed, skip it
                    continue

                if "comment" in indexdf.columns.values:
                    obs_object.comment = row["comment"]

                obs_object.save()
                succesful_observations += 1

                # Now try and handle the linked Datafile
                try:
                    datafile_upload = DjangoFile(
                        zipf.open(row["file_name"], "r"), name=row["file_name"]
                    )

                except KeyError:
                    # If the file isnt present in the zip, skip it
                    print("bad filename")
                    continue

                try:
                    data_object = DataSet(
                        observation=obs_object,
                        upload=datafile_upload,
                        flux_col=fields.flux_col.value,
                        flux_err_col=fields.flux_err_col.value,
                        flux_units=fields.flux_units.value,
                        wavelength_col=fields.wavelength_col.value,
                        wavelength_units=fields.wavelength_units.value,
                        is_valid=user.is_staff,
                    )
                except AssertionError:
                    # If the metadata for the value object is bad, skip it
                    continue

                if "rv" in indexdf.columns.values:
                    data_object.radial_velocity = row["rv"]
                elif "radial_velocity" in indexdf.columns.values:
                    data_object.radial_velocity = row["radial_velocity"]

                if "rv_err" in indexdf.columns.values:
                    data_object.radial_velocity_error = row["rv_err"]
                elif "radial_velocity_error" in indexdf.columns.values:
                    data_object.radial_velocity_error = row["radial_velocity_error"]

                for attr in ("doi", "arxiv_url", "ads_url", "bibtex", "comment"):
                    if attr in indexdf.columns.values:
                        setattr(data_object, attr, row[attr])

                data_object.save()
                succesful_datafiles += 1

            messages.success(request, f"Uploaded {succesful_observations} Observations")
            messages.success(request, f"Uploaded {succesful_datafiles} Datasets")
