"""
Submenu for items relating to researchers
"""

from django.db.models import Q
from iommi.main_menu import M

from app.forms.researcher import ResearcherForm
from app.models import Observation, Project
from app.tables.observation import ObservationTable
from app.tables.project import ProjectTable
from app.tables.researcher import ResearcherTable

researcher_submenu: M = M(
    display_name="Researchers",
    icon="users",
    include=lambda user, **_: user.is_authenticated and user.is_active,
    view=ResearcherTable(auto__exclude=["orcid"]),
    items=dict(
        view=M(
            display_name=lambda researcher, **_: researcher,
            path="<researcher>/",
            params={"researcher"},
            include=lambda user, researcher, **_: user.has_perm("app.view_researcher", researcher),
            url=lambda researcher, **_: researcher.get_absolute_url(),
            view=ResearcherForm(
                auto__exclude=["user"],
                title=lambda researcher, **_: f"{researcher}",
                instance=lambda researcher, **_: researcher,
                editable=False,
            ).as_view(),
            items=dict(
                change=M(
                    icon="pencil",
                    display_name="Edit",
                    include=lambda user, researcher, **_: user.has_perm(
                        "app.change_researcher", researcher
                    ),
                    view=ResearcherForm.edit(
                        auto__exclude=["user"],
                        title=lambda researcher, **_: f"Change {researcher}",
                        instance=lambda researcher, **_: researcher,
                        extra__redirect_to=lambda researcher, **_: researcher.get_absolute_url(),
                    ),
                ),
                list_projects=M(
                    display_name="List Projects",
                    icon="list",
                    view=ProjectTable(
                        rows=lambda researcher, **_: Project.objects.filter(
                            Q(principal_investigator=researcher) | Q(members__pk=researcher.pk)
                        ),
                        title=lambda researcher, **_: f"{researcher}'s Projects",
                    ).as_view(),
                ),
                list_observations=M(
                    display_name="List Observations",
                    icon="camera",
                    view=ObservationTable(
                        auto=dict(
                            include=["date", "proposal__instrument", "source"],
                        ),
                        rows=lambda researcher, **_: Observation.objects.filter(
                            Q(proposal__project__principal_investigator=researcher)
                            | Q(proposal__project__members__pk=researcher.pk)
                        ),
                        title=lambda researcher, **_: f"{researcher}'s Observations",
                    ).as_view(),
                ),
            ),
        ),
    ),
)
