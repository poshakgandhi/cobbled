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

        # Custom pre_delete and post_delete signals to clean up user data on deletion
        from django.db.models.signals import pre_delete, post_delete
        
        def on_user_pre_delete(sender, instance, **kwargs):
            try:
                if hasattr(instance, 'researcher'):
                    researcher = instance.researcher
                    from django.db.models import Q
                    # Find all projects associated with this researcher
                    projects = Project.objects.filter(
                        Q(principal_investigator=researcher) | Q(members=researcher)
                    ).distinct()

                    projects_to_delete = []
                    projects_to_keep = []
                    projects_to_promote = []

                    for project in list(projects):
                        other_members = list(project.members.exclude(pk=researcher.pk))
                        other_pi = project.principal_investigator if project.principal_investigator != researcher else None
                        has_other_users = (other_pi is not None) or (len(other_members) > 0)
                        
                        if not has_other_users:
                            projects_to_delete.append(project)
                        else:
                            projects_to_keep.append(project)
                            if project.principal_investigator == researcher:
                                projects_to_promote.append((project.pk, other_members[0].pk))

                    # Find all observations where observer == researcher.
                    # We need to decide whether to delete them.
                    obs_by_user = Observation.objects.filter(observer=researcher)
                    obs_to_delete = []
                    for obs in obs_by_user:
                        associated_project = None
                        if obs.project:
                            associated_project = obs.project
                        elif obs.proposal and obs.proposal.project:
                            associated_project = obs.proposal.project
                            
                        if associated_project:
                            if associated_project in projects_to_keep:
                                # Do not delete, as the project has other users and must keep its data.
                                continue
                        
                        obs_to_delete.append(obs)

                    # First delete the observations
                    for obs in obs_to_delete:
                        obs.delete()

                    # Delete the projects that need to be deleted (this cascades to proposals)
                    for project in projects_to_delete:
                        Observation.objects.filter(project=project).delete()
                        project.delete()

                    # Store the projects to promote on the instance so we can update them in post_delete
                    instance._projects_to_promote = projects_to_promote
            except Exception as e:
                logger.error(f"Error in user pre-delete cleanup: {e}", exc_info=True)

        def on_user_post_delete(sender, instance, **kwargs):
            try:
                projects_to_promote = getattr(instance, '_projects_to_promote', [])
                for project_pk, new_pi_pk in projects_to_promote:
                    try:
                        project = Project.objects.get(pk=project_pk)
                        project.principal_investigator_id = new_pi_pk
                        project.save()
                    except Project.DoesNotExist:
                        pass
            except Exception as e:
                logger.error(f"Error in user post-delete cleanup: {e}", exc_info=True)

        from django.contrib.auth import get_user_model
        pre_delete.connect(on_user_pre_delete, sender=get_user_model())
        post_delete.connect(on_user_post_delete, sender=get_user_model())

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
