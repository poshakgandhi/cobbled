"""
Submenu for items relating to instruments.
"""

from iommi import LAST
from iommi.main_menu import M

from app.forms.instrument import InstrumentForm
from app.pages.instrument import InstrumentViewPage
from app.tables.instrument import InstrumentTable
from app.tables.proposal import ProposalTable

instrument_submenu: M = M(
    display_name="Instruments",
    icon="satellite",
    include=lambda user, **_: user.is_authenticated and user.is_active,
    view=InstrumentTable().as_view(),
    items=dict(
        add=M(
            icon="plus",
            include=lambda user, **_: user.has_perm("app.add_instrument"),
            view=InstrumentForm.create(
                fields=dict(
                    is_valid=dict(
                        after=LAST,
                        initial=lambda user, **_: user.is_staff,
                        editable=False,
                    )
                ),
            ),
        ),
        view=M(
            display_name=lambda instrument, **_: str(instrument),
            path="<instrument>/",
            params={"instrument"},
            include=lambda user, instrument, **_: user.has_perm("app.view_instrument", instrument),
            url=lambda instrument, **_: instrument.get_absolute_url(),
            view=InstrumentViewPage().as_view(),
            items=dict(
                list_proposals=M(
                    display_name="List Proposals",
                    icon="list",
                    view=ProposalTable(
                        rows=lambda instrument, **_: instrument.proposal_set.all(),
                        title=lambda instrument, **_: f"{instrument} Proposals",
                    ).as_view(),
                ),
                change=M(
                    icon="pencil",
                    display_name="edit",
                    include=lambda user, instrument, **_: user.has_perm(
                        "app.change_instrument", instrument
                    ),
                    view=InstrumentForm.edit(
                        title=lambda instrument, **_: f"Change {instrument}",
                        auto__exclude=["is_valid"],
                        instance=lambda instrument, **_: instrument,
                        extra__redirect_to=lambda instrument, **_: instrument.get_absolute_url(),
                    ),
                ),
                delete=M(
                    icon="trash",
                    include=lambda user, instrument, **_: user.has_perm(
                        "app.delete_instrument", instrument
                    ),
                    view=InstrumentForm.delete(instance=lambda instrument, **_: instrument),
                ),
            ),
        ),
    ),
)
