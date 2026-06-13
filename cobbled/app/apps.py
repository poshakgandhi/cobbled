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

        # Ensure all existing users have Researcher profiles on first request
        from django.core.signals import request_started
        
        def on_request_started(sender, **kwargs):
            request_started.disconnect(on_request_started)
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                for user in User.objects.all():
                    if not hasattr(user, 'researcher'):
                        if user.is_staff or user.is_superuser or user.email in ["poshakgandhi@gmail.com", "poshak.gandhi@soton.ac.uk", "jc2a23soton@gmail.com"]:
                            pass
                        else:
                            user.is_active = False
                            user.save()
                        
                        Researcher.objects.create(
                            user=user,
                            affiliations="TBD",
                            orcid="0000-0000-0000-0000"
                        )
            except Exception as e:
                logger.warning(f"Could not check/create missing researcher profiles: {e}")

        request_started.connect(on_request_started)

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
