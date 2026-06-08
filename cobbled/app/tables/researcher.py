from django.template import Template
from iommi import Table

from app.models.researcher import Researcher


class ResearcherTable(Table):
    """
    Class to represent a table of sources.
    """

    class Meta:
        """
        This is stuff that you could otherwise pass as arguments to the constructor
        """

        auto = dict(
            model=Researcher,
        )
        columns = dict(
            user=dict(
                cell=dict(
                    value=lambda row, **_: row.user.get_full_name(),
                    url=lambda row, **_: row.get_absolute_url(),
                ),
                filter=dict(  # Enables free-text search on the column
                    include=True,
                    freetext=True,
                ),
            ),
            affiliations=dict(
                cell__template=Template("<td>{{ value | truncatechars:32 }}</td>"),
                filter=dict(
                    include=True,
                    freetext=True,
                ),
            ),
        )
        query__advanced__include = False  # We don't want the advanced filter
        rows = Researcher.objects.filter(user__is_active=True)
