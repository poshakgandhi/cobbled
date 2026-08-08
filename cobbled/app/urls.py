from django.urls import path

from app.views import bibtex_view, download_dataset_view
from app.pages.observation import edit_observation_view, delete_observation_view
from app.pages.source import add_observation_for_source_view

urlpatterns = [
    path("download/<dataset_pk>", download_dataset_view, name="download-dataset"),
    path("bibtex/<dataset_pk>", bibtex_view, name="bibtex"),
    path("obs/<int:obs_id>/edit/", edit_observation_view, name="edit-observation"),
    path("obs/<int:obs_id>/delete/", delete_observation_view, name="delete-observation"),
    path("source/<int:source_id>/add-obs/", add_observation_for_source_view, name="add-obs-for-source"),
]
