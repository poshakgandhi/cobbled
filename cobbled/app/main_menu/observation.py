"""
Submenu for items relating to projects.
"""

from django.urls import reverse
from iommi import LAST, Field
from iommi.main_menu import EXTERNAL, M

from app.forms.observation import DatasetForm, ObservationForm
from app.pages.observation import ObservationViewPage

observation_submenu = M(
    display_name=lambda observation, **_: f"Observation: {observation.source}",
    path="obs/<observation>/",
    params={"observation"},
    include=lambda user, observation, **_: user.has_perm("app.view_observation", observation),
    url=lambda observation, **_: observation.get_absolute_url(),
    view=ObservationViewPage().as_view(),
    items=dict(
        add_dataset=M(
            display_name="Add Dataset",
            icon="plus",
            include=lambda user, observation, **_: not hasattr(observation, "dataset")
            and user.has_perm("app.change_observation", observation),
            view=DatasetForm.create(
                fields=dict(
                    is_valid=dict(
                        after=LAST,
                        initial=lambda user, **_: user.is_staff,
                        editable=False,
                    )
                ),
                fields__observation=Field.non_rendered(
                    initial=lambda observation, **_: observation
                ),
                extra__redirect_to=lambda observation, **_: observation.get_absolute_url(),
            ),
        ),
        download_dataset=M(
            display_name="Download Data",
            icon="download",
            include=lambda user, observation, **_: hasattr(observation, "dataset")
            and user.has_perm("app.view_dataset", observation.dataset),
            # Slight hack to allow for usage of standard django URL/view config for downloads
            view=EXTERNAL,
            url=lambda observation, **_: reverse("download-dataset", args=[observation.dataset.pk])
            if hasattr(observation, "dataset")
            else "",
        ),
        bibtex=M(
            display_name="BibTeX",
            icon="book",
            include=lambda observation, **_: hasattr(observation, "dataset")
            and observation.dataset.bibtex,
            view=EXTERNAL,
            url=lambda observation, **_: reverse("bibtex", args=[observation.dataset.pk])
            if hasattr(observation, "dataset")
            else "",
        ),
        arxiv=M(
            display_name="arXiV",
            icon="x",
            include=lambda observation, **_: hasattr(observation, "dataset")
            and observation.dataset.arxiv_url,
            view=EXTERNAL,
            url=lambda observation, **_: observation.dataset.get_clean_arxiv_url()
            if hasattr(observation, "dataset")
            else "",
        ),
        ads=M(
            display_name="ADS",
            icon="magnifying-glass",
            include=lambda observation, **_: hasattr(observation, "dataset")
            and observation.dataset.ads_url,
            view=EXTERNAL,
            url=lambda observation, **_: observation.dataset.get_clean_ads_url()
            if hasattr(observation, "dataset")
            else "",
        ),
        change_dataset=M(
            display_name="Change Dataset",
            icon="database",
            include=lambda user, observation, **_: hasattr(observation, "dataset")
            and user.has_perm("app.change_observation", observation),
            view=DatasetForm.edit(
                auto__exclude=["observation", "upload"],
                title="Change Dataset",
                instance=lambda observation, **_: observation.dataset,
                extra__redirect_to=lambda observation, **_: observation.get_absolute_url(),
            ),
        ),
        change_details=M(
            display_name="Change Details",
            icon="pencil",
            include=lambda user, observation, **_: user.has_perm(
                "app.change_observation", observation
            ),
            view=ObservationForm.edit(
                extra__redirect_to=lambda observation, **_: observation.get_absolute_url(),
                title=lambda **_: "Change Observation Details",
                instance=lambda observation, **_: observation,
                auto__exclude=["proposal", "is_valid"],
            ),
        ),
        delete=M(
            display_name=lambda **_: "Delete Observation",
            icon="trash",
            include=lambda user, observation, **_: user.has_perm(
                "app.delete_observation", observation
            ),
            view=ObservationForm.delete(
                instance=lambda observation, **_: observation,
                extra__redirect_to=lambda observation, **_: observation.proposal.get_absolute_url()
                if observation.proposal
                else (
                    observation.project.get_absolute_url()
                    if observation.project
                    else f"/source/{observation.source.pk}/"
                ),
            ),
        ),
    ),
)
