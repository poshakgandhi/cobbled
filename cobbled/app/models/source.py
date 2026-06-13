from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import BooleanField, CharField, FloatField, Model, ForeignKey, CASCADE, SET_NULL
from rules import add_perm, is_active, is_staff


class Source(Model):
    """
    Root model for an astrophysical source.
    """

    is_valid = BooleanField(
        default=False, help_text="Entries require approval by site staff before they are visible."
    )

    created_by = ForeignKey(
        "Researcher",
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="created_sources",
        help_text="The researcher who registered/created this source."
    )

    name = CharField(
        max_length=32,
        unique=True,
        null=False,
        help_text="Most common name or identifier of the source",
    )

    other_names = CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Other names or identifiers for the source",
    )

    ra = FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(360.0)],
        verbose_name="RA",
        help_text="Right Ascension (RA) in decimal degrees",
    )

    dec = FloatField(
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)],
        verbose_name="Dec",
        help_text="Declination (Dec) in decimal degrees",
    )

    def get_aladin_coordinates(self) -> str:
        """
        Gets the 'target' coordinates for this source on Aladin.

        :returns: The Aladin-format RA & Dec.
        """
        return f"{self.ra}{self.dec:+g}"

    def aladin_link(self, survey: str | None = None, fov: float | None = None) -> str:
        """
        Gets the link to the source on Aladin

        :param survey: Selection of survey image.
        :param fov: Initial field of view. If none, defaults to value from settings.
        :returns: The link to a view of the source's sky location.
        """
        fov = fov or settings.ALADIN_DEFAULT_FOV
        survey = survey or settings.ALADIN_DEFAULT_SURVEY
        return f"https://aladin.u-strasbg.fr/AladinLite/?target={self.get_aladin_coordinates()}&fov={fov:.1f}&survey={survey}"

    def get_absolute_url(self) -> str:
        return f"/source/{self.pk}/"

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return str(self)


# Rules for database interactions with this source
# Conditions are tested on the user wanting to make the change
add_perm("app.add_source", is_active)
add_perm("app.change_source", is_staff)
add_perm("app.delete_source", is_staff)
add_perm("app.view_source", is_active)
