from iommi import Form

from app.models import Proposal


class ProposalForm(Form):
    """
    Handles the common setup for project-based forms.
    """

    class Meta:
        auto__model = Proposal
