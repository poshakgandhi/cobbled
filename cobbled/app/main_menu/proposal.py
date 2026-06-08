"""
Submenu for items relating to projects.
"""

from iommi import LAST
from iommi.main_menu import M

from app.forms.observation import BulkObservationForm, ObservationForm
from app.forms.proposal import ProposalForm
from app.main_menu.observation import observation_submenu
from app.pages.proposal import ProposalViewPage

proposal_submenu = M(
    display_name=lambda proposal, **_: proposal,
    path="proposal/<proposal>/",
    params={"project", "proposal"},
    include=lambda user, proposal, **_: user.has_perm("app.view_proposal", proposal),
    url=lambda proposal, **_: proposal.get_absolute_url(),
    view=ProposalViewPage().as_view(),
    items=dict(
        change=M(
            icon="pencil",
            include=lambda user, proposal, **_: user.has_perm("app.change_proposal", proposal),
            view=ProposalForm.edit(
                extra__redirect_to=lambda proposal, **_: proposal.get_absolute_url(),
                title=lambda project,
                proposal,
                **_: f"Change {project}: Proposal {proposal.get_project_index()}",
                instance=lambda proposal, **_: proposal,
                auto__exclude=["project"],
            ),
        ),
        delete=M(
            display_name=lambda proposal, **_: f"Delete Proposal {proposal.get_project_index()}",
            icon="trash",
            include=lambda user, proposal, **_: user.has_perm("app.delete_proposal", proposal),
            view=ProposalForm.delete(
                instance=lambda proposal, **_: proposal,
                extra__redirect_to=lambda proposal, **_: proposal.project.get_absolute_url(),
            ),
        ),
        add_observation=M(
            icon="plus",
            include=lambda user, proposal, **_: user.has_perm("app.change_proposal", proposal),
            view=ObservationForm.create(
                fields=dict(
                    proposal=dict(
                        initial=lambda proposal, **_: proposal,
                        editable=False,
                    ),
                    is_valid=dict(
                        after=LAST,
                        initial=lambda user, **_: user.is_staff,
                        editable=False,
                    ),
                ),
            ),
        ),
        bulk_add_observations=M(
            icon="plus",
            include=lambda user, proposal, **_: user.has_perm("app.change_proposal", proposal),
            view=BulkObservationForm(
                fields__proposal__initial=lambda proposal, **_: proposal,
                title="Bulk Upload Observations",
            ),
        ),
        view=observation_submenu,
    ),
)
