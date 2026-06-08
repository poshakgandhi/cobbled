from django.db.models import Q
from iommi import Table

from app.models import Source


class SourceTable(Table):
    """
    Class to represent a table of sources.
    """

    class Meta:
        """
        This is stuff that you could otherwise pass as arguments to the constructor
        """

        auto = dict(
            model=Source,
            include=["name", "gaiainfo__gaia_id", "other_names", "ra", "dec"],
        )
        columns = dict(
            name=dict(
                cell__url=lambda row, **_: row.get_absolute_url(),
                filter=dict(  # Enables free-text search on the column names
                    include=True,
                    freetext=True,
                ),
            ),
            gaiainfo_gaia_id=dict(
                filter=dict(
                    include=True,
                    freetext=True,
                ),
            ),
            other_names=dict(
                filter=dict(
                    include=True,
                    freetext=True,
                ),
            ),
        )
        query__advanced__include = False  # We don't want the advanced filter
        rows = lambda request, **_: (
            Source.objects.all() if request.user.is_staff else (
                Source.objects.filter(
                    Q(is_valid=True) | Q(created_by=request.user.researcher)
                ).distinct() if request.user.is_authenticated and hasattr(request.user, "researcher") else Source.objects.filter(is_valid=True)
            )
        )
