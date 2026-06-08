from iommi import Header, Page

from app.forms.project import ProjectForm
from app.tables.proposal import ProposalTable


class ProjectViewPage(Page):
    """
    The basic view for a project.
    """

    header = Header(lambda project, **_: project)
    detail = ProjectForm(
        auto__exclude=["is_valid", "name", "members"],
        instance=lambda project, **_: project,
        editable=False,
    )
    proposal_table = ProposalTable(
        auto__exclude=["project"],
        rows=lambda project, **_: project.proposal_set.all(),
        columns__proposal__after=-1,
    )
