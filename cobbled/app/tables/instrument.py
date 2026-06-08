from iommi import Table

from app.models.instrument import Instrument


class InstrumentTable(Table):
    """
    Class to represent a table of instruments.
    """

    class Meta:
        """
        This is stuff that you could otherwise pass as arguments to the constructor
        """

        auto = dict(
            model=Instrument,
            include=["name", "observatory", "type"],
        )
        columns = dict(
            name=dict(
                cell__url=lambda row, **_: row.get_absolute_url(),
                filter=dict(  # Enables free-text search on the column names
                    include=True,
                    freetext=True,
                ),
            ),
            observatory=dict(
                filter=dict(
                    include=True,
                    freetext=True,
                ),
            ),
            type=dict(
                filter=dict(
                    include=False,
                    freetext=False,
                ),
            ),
        )
        query__advanced__include = False  # We don't want the advanced filter
        rows = Instrument.objects.filter(is_valid=True)
