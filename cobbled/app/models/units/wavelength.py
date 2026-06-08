from django.db.models import CharField, Model


class WavelengthUnit(Model):
    """
    Model to define units of wavelength.
    """

    name = CharField(
        max_length=32,
        null=False,
        blank=False,
    )

    astropy = CharField(
        max_length=32,
        null=False,
        blank=False,
    )

    symbol = CharField(
        max_length=32,
        null=False,
        blank=False,
    )

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return str(self)
