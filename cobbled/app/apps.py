from logging import Logger, getLogger

from django.apps import AppConfig
from iommi import register_search_fields
from iommi.path import register_path_decoding

logger: Logger = getLogger(__name__)


class MainAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app"
    verbose_name = "Proposal Management Platform"
    default = True

    def ready(self):
        logger.info("Main app is ready.")

        from app.models import (
            FluxUnit,
            Instrument,
            Observation,
            Project,
            Proposal,
            Researcher,
            Source,
            WavelengthUnit,
        )

        # Iommi path decoding and settings for model searches
        register_search_fields(
            model=Instrument, search_fields=["name", "observatory"], allow_non_unique=True
        )
        register_path_decoding(instrument=Instrument)

        register_path_decoding(observation=Observation)

        register_search_fields(
            model=Project,
            search_fields=["name", "principal_investigator__user__username"],
            allow_non_unique=True,
        )
        register_path_decoding(project=Project)

        register_path_decoding(proposal=Proposal)

        register_search_fields(
            model=Source,
            search_fields=["name", "other_names", "gaiainfo__gaia_id"],
            allow_non_unique=True,
        )
        register_path_decoding(source=Source)

        register_search_fields(
            model=Researcher, search_fields=["user", "affiliations"], allow_non_unique=True
        )
        register_path_decoding(researcher=Researcher)
        register_search_fields(model=WavelengthUnit, search_fields=["name"], allow_non_unique=True)
        register_search_fields(model=FluxUnit, search_fields=["name"], allow_non_unique=True)
