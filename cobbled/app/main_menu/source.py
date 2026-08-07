from django.db.models import Q
from iommi import LAST
from iommi.main_menu import EXTERNAL, M

from app.forms.source import SourceForm, SourceGaiaInfoForm
from app.pages.source import SourceViewPage, add_gaiainfo_view
from app.tables.source import SourceTable


class DynamicSourcesMenu(M):
    def bind(self, request, root):
        import copy
        from collections import defaultdict

        from app.models import Project, Source

        obj = copy.copy(self)
        base_items = {}
        for k in ["add", "view"]:
            if k in self.items:
                base_items[k] = self.items[k]
        obj.items = base_items

        user = request.user
        if user.is_authenticated:
            if user.is_staff:
                sources = Source.objects.all().order_by("name")
            elif hasattr(user, "researcher"):
                sources = (
                    Source.objects.filter(Q(is_valid=True) | Q(created_by=user.researcher))
                    .distinct()
                    .order_by("name")
                )
            else:
                sources = Source.objects.filter(is_valid=True).order_by("name")
        else:
            sources = Source.objects.filter(is_valid=True).order_by("name")

        # Group sources by Project
        project_sources = defaultdict(list)
        unassigned_sources = []

        # Pre-fetch all visible projects so we can verify if the user has access
        all_projects = Project.objects.all()
        visible_projects = set()
        for proj in all_projects:
            if user.has_perm("app.view_project", proj):
                visible_projects.add(proj)

        for source in sources:
            # Query projects associated with this source
            source_projects = Project.objects.filter(
                Q(observation__source=source) | Q(proposal__observation__source=source)
            ).distinct()

            # Intersection of associated projects and visible projects
            source_visible_projects = [p for p in source_projects if p in visible_projects]

            if source_visible_projects:
                for proj in source_visible_projects:
                    project_sources[proj].append(source)
            else:
                unassigned_sources.append(source)

        def make_source_item(source):
            return M(
                display_name=source.name,
                url=source.get_absolute_url(),
                view=EXTERNAL,
                icon="minus",
            )

        def dummy_view(request, **kwargs):
            from django.http import HttpResponse

            return HttpResponse("")

        # 1. Grouped by Project (sorted by project name)
        for proj in sorted(project_sources.keys(), key=lambda p: p.name.lower()):
            proj_sources = project_sources[proj]
            proj_items = {}
            for source in sorted(proj_sources, key=lambda s: s.name.lower()):
                source_item = make_source_item(source)
                source_item._set_name(f"source_{source.pk}")
                proj_items[source_item.name] = source_item

            project_menu = M(
                display_name=proj.name,
                icon="folder",
                url=lambda proj_val=proj, **_: proj_val.get_absolute_url(),
                view=dummy_view,
                items=proj_items,
            )
            project_menu.parent = obj
            project_menu._set_name(f"project_group_{proj.pk}")
            obj.items[project_menu.name] = project_menu

        # 2. Independent sources (not linked to any project)
        if unassigned_sources:
            other_items = {}
            for source in sorted(unassigned_sources, key=lambda s: s.name.lower()):
                source_item = make_source_item(source)
                source_item._set_name(f"source_{source.pk}")
                other_items[source_item.name] = source_item

            independent_menu = M(
                display_name="Independent Sources",
                icon="folder-open",
                url=lambda **_: "#",
                view=dummy_view,
                items=other_items,
            )
            independent_menu.parent = obj
            independent_menu._set_name("independent_sources")
            obj.items[independent_menu.name] = independent_menu

        return super(DynamicSourcesMenu, obj).bind(request, root)


source_submenu: M = DynamicSourcesMenu(
    render=False,
    display_name="Sources",
    icon="sun",
    include=lambda user, **_: user.is_authenticated and user.is_active,
    view=SourceTable().as_view(),
    items=dict(
        add=M(
            icon="plus",
            include=lambda user, **_: user.has_perm("app.add_source"),
            view=SourceForm.create(
                fields=dict(
                    is_valid=dict(
                        # We could exclude this (with `auto__exclude=['is_valid']`) but we don't to show the users.
                        after=LAST,
                        initial=lambda user, **_: user.is_staff
                        or (user.is_active and hasattr(user, "researcher")),
                        editable=False,
                    )
                ),
            ),
        ),
        view=M(
            display_name=lambda source, **_: source,
            path="<source>/",
            params={"source"},
            include=lambda user, source, **_: user.has_perm("app.view_source", source),
            url=lambda source, **_: source.get_absolute_url(),
            view=SourceViewPage().as_view(),
            items=dict(
                # Adds the source Gaia info, with the source defaulting to the current one
                add_gaiainfo=M(
                    display_name="Add Gaia info",
                    icon="plus",
                    include=lambda user, source, **_: not hasattr(source, "gaiainfo")
                    and user.has_perm("app.add_sourcegaiainfo"),
                    view=add_gaiainfo_view,
                ),
                view_on_aladin=M(
                    display_name="View on Aladin",
                    icon="bullseye",
                    view=EXTERNAL,
                    url=lambda source, **_: source.aladin_link(),
                ),
                change=M(
                    icon="pencil",
                    include=lambda user, source, **_: user.has_perm("app.change_source", source),
                    view=SourceForm.edit(
                        title=lambda source, **_: f"Change {source}",
                        auto__exclude=["is_valid"],
                        instance=lambda source, **_: source,
                        extra__redirect_to=lambda source, **_: source.get_absolute_url(),
                    ),
                ),
                change_gaiainfo=M(
                    display_name="Change Gaia info",
                    icon="pen-ruler",
                    include=lambda user, source, **_: hasattr(source, "gaiainfo")
                    and user.has_perm("app.change_sourcegaiainfo"),
                    view=SourceGaiaInfoForm.edit(
                        auto__exclude=["is_valid", "source"],
                        instance=lambda source, **_: source.gaiainfo,
                        extra__redirect_to=lambda source, **_: source.get_absolute_url(),
                    ),
                ),
                delete=M(
                    display_name=lambda source, **_: f"Delete {source}",
                    icon="trash",
                    include=lambda user, source, **_: user.has_perm("app.delete_source", source),
                    view=SourceForm.delete(instance=lambda source, **_: source),
                ),
            ),
        ),
    ),
)
