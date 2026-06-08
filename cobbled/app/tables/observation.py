from iommi import LAST, Column, Table

from app.models.observation import Observation


class ObservationTable(Table):
    """
    Class to represent a table of observations linked to a given proposal.
    """

    class Meta:
        """
        This is stuff that you could otherwise pass as arguments to the constructor
        """

        auto = dict(
            model=Observation,
            include=["jd", "source"],
        )
        columns = dict(
            jd=Column(
                display_name="Date (JD)",
                cell__value=lambda row, **_: row.get_jd_or_placeholder(),
                cell__url=lambda row, **_: row.get_absolute_url(),
            ),
            status=Column(
                cell__value=lambda row, **_: row.get_data_status(),
                after=LAST,
            ),
        )
        query__include = False  # We don't want a filter for these
        rows = Observation.objects.filter(is_valid=True)
