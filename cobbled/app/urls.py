from django.urls import path

from app.views import bibtex_view, download_dataset_view

urlpatterns = [
    path("download/<dataset_pk>", download_dataset_view, name="download-dataset"),
    path("bibtex/<dataset_pk>", bibtex_view, name="bibtex"),
]
