from iommi import Column, Table

from app.models.proposal import Proposal


class ProposalTable(Table):
    """
    Class to represent a table of proposals linked to a given project.
    """

    class Meta:
        """
        This is stuff that you could otherwise pass as arguments to the constructor
        """

        auto = dict(
            model=Proposal,
            include=["project", "instrument", "status"],
        )
        columns = dict(
            proposal=Column(
                cell__value=lambda row, **_: str(row),
                cell__url=lambda row, **_: row.get_absolute_url(),
                after=2,
            )
        )
        query__include = False  # We don't want a filter for these
        rows = Proposal.objects.all()
