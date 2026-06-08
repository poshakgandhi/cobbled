from iommi import Table

from app.models.project import Project


class ProjectTable(Table):
    """
    Class to represent a table of projects.
    """

    class Meta:
        """
        This is stuff that you could otherwise pass as arguments to the constructor
        """

        auto = dict(
            model=Project,
            include=["name", "principal_investigator"],
        )
        columns = dict(
            name=dict(
                cell__url=lambda row, **_: row.get_absolute_url(),
                filter=dict(  # Enables free-text search on the column names
                    include=True,
                    freetext=True,
                ),
            ),
            principal_investigator=dict(
                cell__url=lambda row, **_: row.principal_investigator.get_absolute_url(),
                filter=dict(  # Enables free-text search on the column names
                    include=True,
                    freetext=True,
                ),
            ),
        )
        query__advanced__include = False  # We don't want the advanced filter
        rows = Project.objects.filter(is_valid=True)
