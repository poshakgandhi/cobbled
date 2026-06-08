from iommi import Header, Page

from app.forms.proposal import ProposalForm
from app.tables.observation import ObservationTable


class ProposalViewPage(Page):
    """
    The basic view for a project.
    """

    header = Header(lambda proposal, **_: proposal)
    detail = ProposalForm(
        auto__exclude=["project"],
        instance=lambda proposal, **_: proposal,
        editable=False,
    )
    observation_table = ObservationTable(
        rows=lambda proposal, **_: proposal.observation_set.all(),
    )
