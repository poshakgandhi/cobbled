from iommi import Form

from app.models import Instrument


class InstrumentForm(Form):
    """
    Handles the common setup for instrument-based forms.
    """

    class Meta:
        auto__model = Instrument
