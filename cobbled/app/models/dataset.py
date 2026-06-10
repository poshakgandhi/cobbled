import pandas as pd
from django.contrib.auth import get_user_model
from django.db.models import (
    CASCADE,
    RESTRICT,
    BooleanField,
    CharField,
    FileField,
    FloatField,
    ForeignKey,
    Model,
    OneToOneField,
    TextField,
)
from rules import add_perm, is_active, is_staff, predicate

from app.models.observation import Observation
from app.models.units.flux import FluxUnit
from app.models.units.wavelength import WavelengthUnit


class DataSet(Model):
    """
    Details for the Dataset returned from an Observation.
    """

    observation = OneToOneField(
        Observation, on_delete=CASCADE, primary_key=True, related_name="dataset"
    )

    upload = FileField(
        upload_to="uploads/",
        verbose_name="Upload Dataset",
        help_text="Upload a .csv or .FITS formatted dataset for this observation.",
    )

    flux_col = CharField(
        max_length=32,
        default="flux",
        null=False,
        blank=False,
        verbose_name="Flux Column",
        help_text="The name of the flux column in the dataset.",
    )

    flux_err_col = CharField(
        max_length=32,
        default="flux_err",
        null=True,
        blank=True,
        verbose_name="Flux Error Column",
        help_text="The name of the flux error column in the dataset (set blank if no errors present).",
    )

    flux_units = ForeignKey(
        FluxUnit,
        on_delete=RESTRICT,
        verbose_name="Flux Units",
        help_text="The unit for the flux columns of the dataset.",
    )

    wavelength_col = CharField(
        max_length=32,
        default="wavelength",
        null=False,
        blank=False,
        verbose_name="Wavelength Column",
        help_text="The name of the wavelength column in the dataset.",
    )

    wavelength_units = ForeignKey(
        WavelengthUnit,
        on_delete=RESTRICT,
        verbose_name="Wavelength Units",
        help_text="The unit for the wavelength column of the dataset.",
    )

    radial_velocity = FloatField(
        verbose_name="Radial Velocity (km/s)",
        help_text="The radial velocity of the source in km/s",
        null=True,
        blank=True,
    )

    radial_velocity_error = FloatField(
        verbose_name="Radial Velocity Error (km/s)",
        help_text="The error on the radial velocity of the source in km/s",
        null=True,
        blank=True,
    )

    doi = CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name="DOI",
        help_text="The DOI of the dataset, if available.",
    )

    arxiv_url = CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name="arXiv URL",
        help_text="The full URL to an associated arXiv pre-print associated with this dataset, if it exists.",
    )

    ads_url = CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name="ADS URL",
        help_text="The full URL to the ADS page of a publication associated with this dataset, if it exists.",
    )

    bibtex = TextField(
        null=True,
        blank=True,
        verbose_name="BibTeX",
        help_text="The formatted BibTeX used to cite this dataset.",
    )

    comment = TextField(null=True, blank=True, help_text="Additional comments on the dataset.")

    is_valid = BooleanField(
        default=False, help_text="Entries require approval by site staff before they are visible."
    )

    def get_clean_arxiv_url(self):
        # Attempt some basic auto-formatting to allow for different styles of user-entered arxiv links
        if not self.arxiv_url:
            return "#"
        if self.arxiv_url[:8] != "https://" and self.arxiv_url[:7] != "http://":
            return f"https://{self.arxiv_url}"
        return self.arxiv_url.replace("http://", "https://")

    def get_clean_ads_url(self):
        # Attempt some basic auto-formatting to allow for different styles of user-entered ads links
        if not self.ads_url:
            return "#"
        if self.ads_url[:8] != "https://" and self.ads_url[:7] != "http://":
            return f"https://{self.ads_url}"
        return self.ads_url.replace("http://", "https://")

    def get_df(self):
        # Only works on CSVs for now
        try:
            ext = self.upload.name.split(".")[-1]
            if ext == "csv":
                df = pd.read_csv(self.upload.file)
            else:
                raise NotImplementedError("Unrecognised filetype")

            df.rename(
                columns={
                    self.flux_col: "flux",
                    self.wavelength_col: "wavelength",
                },
                errors="raise",
                inplace=True,
            )

            # Fetch errors if an error column header is provided
            if self.flux_err_col:
                df.rename({self.flux_err_col: "flux_err"}, errors="raise", inplace=True)

            return df

        # Could fail for any number of reasons
        except Exception as e:
            raise ValueError(e)


User = get_user_model()


@predicate
def is_linked_project_member(user: User, dataset: DataSet) -> bool:
    """
    Does this user account correspond to a researcher who is a member of the project linked to this dataset?
    If not, does the dataset have an ArXiV link (i.e. the data is public)?

    :param user: User to check.
    :param dataset: The DataSet to check.
    :return: True if authorized, else False.
    """
    if dataset.arxiv_url:
        return user and user.is_active

    if not user or not hasattr(user, "researcher"):
        return False

    researcher = user.researcher
    obs = dataset.observation

    # 1. Direct observer check
    if obs.observer and obs.observer == researcher:
        return True

    # 2. Check via proposal's project
    if obs.proposal:
        project = obs.proposal.project
        if project.principal_investigator == researcher or researcher in project.members.all():
            return True

    # 3. Check direct project link
    if obs.project:
        project = obs.project
        if project.principal_investigator == researcher or researcher in project.members.all():
            return True

    return False



# Rules for database interactions with this source
# Conditions are tested on the user wanting to make the change
add_perm("app.add_dataset", is_active)
add_perm("app.change_dataset", is_linked_project_member | is_staff)
add_perm("app.delete_dataset", is_linked_project_member | is_staff)
add_perm("app.view_dataset", is_linked_project_member | is_staff)
