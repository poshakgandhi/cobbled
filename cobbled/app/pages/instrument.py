from iommi import Header, Page

from app.forms.instrument import InstrumentForm


class InstrumentViewPage(Page):
    """
    The basic view for an instrument.

    Needs to include all the plots too!
    """

    header = Header(lambda instrument, **_: instrument)
    detail = InstrumentForm(
        auto__exclude=["is_valid", "name"],
        instance=lambda instrument, **_: instrument,
        editable=False,
    )
