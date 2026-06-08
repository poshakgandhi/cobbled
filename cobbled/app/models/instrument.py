from django.core.validators import MinValueValidator
from django.db.models import BooleanField, CharField, FloatField, Model, TextChoices
from django.utils.translation import gettext_lazy as _
from rules import add_perm, is_active, is_staff


class Instrument(Model):
    """
    Model for an instrument (e.g. telescope).
    """

    class Type(TextChoices):
        """
        The allowed entries for the Type field.
        """

        ECHELLE = "e", _("Echelle")
        LONG_SLIT = "ls", _("Long-Slit")
        FIBRE = "f", _("Fibre")
        IMAGING = "i", _("Imagine")

    name = CharField(
        max_length=128, null=False, blank=False, help_text="The name of the instrument."
    )

    type = CharField(
        max_length=2, choices=Type, default=Type.ECHELLE, help_text="The instrument type."
    )

    spectral_resolution = FloatField(
        null=True,
        blank=True,
        verbose_name="Spectral Resolution",
        help_text="The spectral resolution (Δλ/λ) of the instrument.",
        validators=[MinValueValidator(0.0)],
    )

    observatory = CharField(
        null=False,
        blank=False,
        max_length=255,
        help_text="The observatory to which the instrument belongs.",
    )

    is_valid = BooleanField(
        default=False, help_text="Entries require approval by site staff before they are visible."
    )

    def get_absolute_url(self) -> str:
        return f"/instrument/{self.pk}/"

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return str(self)


# Rules for database interactions with this source
# Conditions are tested on the user wanting to make the change
add_perm("app.add_instrument", is_active)
add_perm("app.change_instrument", is_staff)
add_perm("app.delete_instrument", is_staff)
add_perm("app.view_instrument", is_active)
