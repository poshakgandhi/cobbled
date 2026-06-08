"""
Submenu for items relating to sources.
"""

from iommi import Action
from iommi.main_menu import M

from app.actions import (
    validate_dataset_by_observation,
    validate_generic,
    validate_user_by_researcher,
)
from app.models import Instrument, Observation, Project, Researcher, Source
from app.pages.validation import ValidationViewPage
from app.tables.instrument import InstrumentTable
from app.tables.observation import ObservationTable
from app.tables.project import ProjectTable
from app.tables.researcher import ResearcherTable
from app.tables.source import SourceTable

validation_submenu: M = M(
    display_name="Validation Queue",
    icon="square-check",
    include=lambda user, **_: user.is_staff,
    view=ValidationViewPage().as_view(),
    items=dict(
        source=M(
            icon="minus",
            view=SourceTable(
                rows=Source.objects.filter(is_valid=False),
                columns__select__include=True,
                bulk__title="Actions",
                bulk__actions__delete__include=True,
                bulk__actions__validate=Action.submit(
                    display_name="Bulk Validate", post_handler=validate_generic
                ),
                query__include=False,
            ).as_view(),
        ),
        instrument=M(
            icon="minus",
            view=InstrumentTable(
                rows=Instrument.objects.filter(is_valid=False),
                columns__select__include=True,
                bulk__title="Actions",
                bulk__actions__delete__include=True,
                bulk__actions__validate=Action.submit(
                    display_name="Bulk Validate", post_handler=validate_generic
                ),
                query__include=False,
            ).as_view(),
        ),
        project=M(
            icon="minus",
            view=ProjectTable(
                rows=Project.objects.filter(is_valid=False),
                columns__select__include=True,
                bulk__title="Actions",
                bulk__actions__delete__include=True,
                bulk__actions__validate=Action.submit(
                    display_name="Bulk Validate", post_handler=validate_generic
                ),
                query__include=False,
            ).as_view(),
        ),
        researcher=M(
            icon="minus",
            view=ResearcherTable(
                rows=Researcher.objects.filter(user__is_active=False),
                columns__select__include=True,
                bulk__title="Actions",
                bulk__actions__validate=Action.submit(
                    display_name="Bulk Validate", post_handler=validate_user_by_researcher
                ),
                query__include=False,
            ).as_view(),
        ),
        dataset=M(
            icon="minus",
            view=ObservationTable(
                rows=Observation.objects.filter(dataset__is_valid=False),
                columns__select__include=True,
                auto__include=["jd", "proposal__instrument", "source"],
                bulk__title="Actions",
                bulk__actions__validate=Action.submit(
                    display_name="Bulk Validate", post_handler=validate_dataset_by_observation
                ),
                query__include=False,
            ).as_view(),
        ),
    ),
)
