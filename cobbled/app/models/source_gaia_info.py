from django.core.validators import MinValueValidator
from django.db.models import (
    CASCADE,
    BooleanField,
    FloatField,
    Model,
    OneToOneField,
    TextField,
)
from rules import add_perm, is_active, is_staff

from app.models.source import Source


class SourceGaiaInfo(Model):
    """
    Additional details from Gaia for the source.

    Implemented as separate model to allow for either new telescopes
    to be added later, or this data to vary over time.
    """

    source = OneToOneField(Source, on_delete=CASCADE, primary_key=True, related_name="gaiainfo")
    is_valid = BooleanField(
        default=False, help_text="Entries require approval by site staff before they are visible."
    )
    gaia_id = TextField(
        verbose_name="Gaia ID",
        help_text="The Gaia Source ID of the object.",
        null=False,
        blank=False,
        max_length=32,
    )

    parallax = FloatField(null=True, blank=True, help_text="Parallax in mas")

    parallax_error = FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        help_text="Parallax error in mas.",
    )

    pmra = FloatField(
        null=True, blank=True, verbose_name="PM RA", help_text="Proper motion in RA in mas/yr"
    )

    pmra_error = FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        verbose_name="PM RA error",
        help_text="Proper motion in RA error in mas/yr.",
    )

    pmdec = FloatField(
        null=True, blank=True, verbose_name="PM Dec", help_text="Proper motion in Dec in mas/yr"
    )

    pmdec_error = FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        verbose_name="PM Dec error",
        help_text="Proper motion in Dec error in mas/yr.",
    )

    phot_g_mean_mag = FloatField(
        null=True, blank=True, verbose_name="G-band mean mag", help_text="G-band mean magnitude"
    )

    bp_rp = FloatField(null=True, blank=True, verbose_name="BP-RP", help_text="BP-RP color")

    radial_velocity = FloatField(
        null=True, blank=True, help_text="Gaia RVS radial velocity in km/s."
    )

    radial_velocity_error = FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        help_text="Gaia RVS radial velocity error in km/s.",
    )

    astrometric_excess_noise = FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        help_text="Astrometric excess noise in mas.",
    )

    astrometric_excess_noise_sig = FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        help_text="Significance of the astrometric excess noise.",
    )

    def __str__(self) -> str:
        return f"{self.gaia_id}"

    def __repr__(self) -> str:
        return str(self)

    class Meta:
        verbose_name = "Gaia Info"


# Rules for database interactions with this source
# Conditions are tested on the user wanting to make the change
add_perm("app.add_sourcegaiainfo", is_active)
add_perm("app.change_sourcegaiainfo", is_staff)
add_perm("app.delete_sourcegaiainfo", is_staff)
add_perm("app.view_sourcegaiainfo", is_active)
