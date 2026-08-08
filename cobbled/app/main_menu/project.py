"""
Submenu for items relating to projects.
"""

from collections import defaultdict
from django.db.models import Q
from iommi import LAST, M
from iommi.main_menu import EXTERNAL

from app.forms.project import ProjectForm
from app.forms.proposal import ProposalForm
from app.main_menu.proposal import proposal_submenu
from app.models import Project, Researcher, Source
from app.pages.project import ProjectViewPage
from app.tables.project import ProjectTable
from app.tables.researcher import ResearcherTable


class DynamicProjectsMenu(M):
    def bind(self, request, root):
        obj = super(DynamicProjectsMenu, self).bind(request, root)

        user = request.user
        if not (user.is_authenticated and user.is_active):
            return obj

        visible_projects = [p for p in Project.objects.all() if user.has_perm("app.view_project", p)]
        my_projects = []
        community_projects = []

        researcher = getattr(user, "researcher", None)
        for proj in visible_projects:
            is_my_proj = False
            if researcher:
                if proj.principal_investigator == researcher or proj.members.filter(pk=researcher.pk).exists():
                    is_my_proj = True
            elif user.is_staff and proj.principal_investigator is None:
                is_my_proj = True

            if is_my_proj:
                my_projects.append(proj)
            else:
                community_projects.append(proj)

        # Pre-fetch all visible sources
        if user.is_staff:
            sources = Source.objects.all()
        elif researcher:
            sources = Source.objects.filter(Q(is_valid=True) | Q(created_by=researcher)).distinct()
        else:
            sources = Source.objects.filter(is_valid=True)

        # Map sources to projects
        project_sources = defaultdict(list)
        assigned_source_pks = set()

        for source in sources:
            source_projects = Project.objects.filter(
                Q(observation__source=source) | Q(proposal__observation__source=source)
            ).distinct()
            source_visible_projects = [p for p in source_projects if p in visible_projects]
            if source_visible_projects:
                for proj in source_visible_projects:
                    project_sources[proj].append(source)
                    assigned_source_pks.add(source.pk)

        unassigned_sources = [s for s in sources if s.pk not in assigned_source_pks]

        def folder_dummy_view(request, **kwargs):
            from django.http import HttpResponse
            return HttpResponse("")

        def make_source_item(source):
            return M(
                display_name=source.name,
                url=source.get_absolute_url(),
                view=EXTERNAL,
                icon="minus",
            )

        def make_project_menu_item(proj):
            proj_sources = project_sources[proj]
            proj_items = {}
            for source in sorted(proj_sources, key=lambda s: s.name.lower()):
                source_item = make_source_item(source)
                source_item._set_name(f"source_{source.pk}")
                proj_items[source_item.name] = source_item

            return M(
                display_name=proj.name,
                icon="folder",
                url=lambda **_: "javascript:void(0)",
                view=folder_dummy_view,
                items=proj_items,
            )

        new_items = {}

        # 1. My Projects
        if my_projects:
            my_proj_items = {}
            for proj in sorted(my_projects, key=lambda p: p.name.lower()):
                item = make_project_menu_item(proj)
                item._set_name(f"my_proj_{proj.pk}")
                my_proj_items[item.name] = item

            my_projects_folder = M(
                display_name="My Projects",
                icon="folder-user",
                url=lambda **_: "javascript:void(0)",
                view=folder_dummy_view,
                items=my_proj_items,
            )
            my_projects_folder._set_name("my_projects_group")
            bound_folder = my_projects_folder.bind(request=request, root=root)
            bound_folder.parent = obj
            new_items[my_projects_folder.name] = bound_folder

        # 2. Browse All Projects
        if "view_all" in obj.items:
            new_items["view_all"] = obj.items["view_all"]

        # 3. New Project
        if "add" in obj.items:
            new_items["add"] = obj.items["add"]

        # 4. Community Projects
        if community_projects:
            comm_proj_items = {}
            for proj in sorted(community_projects, key=lambda p: p.name.lower()):
                item = make_project_menu_item(proj)
                item._set_name(f"comm_proj_{proj.pk}")
                comm_proj_items[item.name] = item

            comm_projects_folder = M(
                display_name="Community Projects",
                icon="folder-open",
                url=lambda **_: "javascript:void(0)",
                view=folder_dummy_view,
                items=comm_proj_items,
            )
            comm_projects_folder._set_name("community_projects_group")
            bound_comm_folder = comm_projects_folder.bind(request=request, root=root)
            bound_comm_folder.parent = obj
            new_items[comm_projects_folder.name] = bound_comm_folder

        # 5. Independent Sources
        if unassigned_sources:
            other_items = {}
            for source in sorted(unassigned_sources, key=lambda s: s.name.lower()):
                source_item = make_source_item(source)
                source_item._set_name(f"source_{source.pk}")
                other_items[source_item.name] = source_item

            independent_menu = M(
                display_name="Independent Sources",
                icon="tags",
                url=lambda **_: "javascript:void(0)",
                view=folder_dummy_view,
                items=other_items,
            )
            independent_menu._set_name("independent_sources_group")
            bound_indep_menu = independent_menu.bind(request=request, root=root)
            bound_indep_menu.parent = obj
            new_items[independent_menu.name] = bound_indep_menu

        # Preserve routing view
        if "view" in obj.items:
            new_items["view"] = obj.items["view"]

        obj.items = new_items
        return obj


project_submenu: M = DynamicProjectsMenu(
    display_name="Projects",
    icon="diagram-project",
    include=lambda user, **_: user.is_authenticated and user.is_active,
    view=ProjectTable().as_view(),
    items=dict(
        add=M(
            icon="plus",
            display_name="New Project",
            include=lambda user, **_: user.has_perm("app.add_project"),
            view=ProjectForm.create(
                fields=dict(
                    is_valid=dict(
                        after=LAST,
                        initial=lambda user, **_: user.is_staff or (user.is_active and hasattr(user, "researcher")),
                        editable=False,
                    ),
                    principal_investigator=dict(
                        initial=lambda user, **_: user.researcher,
                    ),
                ),
            ),
        ),
        view_all=M(
            display_name="Browse All Projects",
            icon="table",
            url="/project/",
            view=ProjectTable().as_view(),
        ),
        view=M(
            display_name=lambda project, **_: str(project),
            path="<project>/",
            params={"project"},
            include=lambda user, project, **_: user.has_perm("app.view_project", project),
            url=lambda project, **_: project.get_absolute_url(),
            view=ProjectViewPage().as_view(),
            items=dict(
                list_members=M(
                    icon="users",
                    view=ResearcherTable(
                        rows=lambda project, **_: Researcher.objects.filter(
                            Q(pk__in=project.members.all())
                            | Q(pk=project.principal_investigator.pk)
                        )
                    ).as_view(),
                ),
                change=M(
                    icon="pencil",
                    include=lambda user, project, **_: user.has_perm(
                        "app.change_project", project
                    ),
                    view=ProjectForm.edit(
                        title=lambda project, **_: f'Change Project "{project}"',
                        auto__exclude=["is_valid"],
                        instance=lambda project, **_: project,
                        extra__redirect_to=lambda project, **_: project.get_absolute_url(),
                    ),
                ),
                delete=M(
                    display_name=lambda project, **_: f'Delete Project "{project}"',
                    icon="trash",
                    include=lambda user, project, **_: user.has_perm(
                        "app.delete_project", project
                    ),
                    view=ProjectForm.delete(instance=lambda project, **_: project),
                ),
                add_proposal=M(
                    icon="plus",
                    include=lambda user, project, **_: user.has_perm(
                        "app.change_project", project
                    ),
                    view=ProposalForm.create(
                        fields=dict(
                            project=dict(
                                initial=lambda project, **_: project,
                                editable=False,
                            ),
                        ),
                    ),
                ),
                view=proposal_submenu,
            ),
        ),
    ),
)

