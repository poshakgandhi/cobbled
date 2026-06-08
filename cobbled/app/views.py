"""Supplemental Django views"""

from django.core.exceptions import PermissionDenied
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404

from app.models.dataset import DataSet


def bibtex_view(request, dataset_pk):
    dataset = get_object_or_404(DataSet, pk=dataset_pk)

    return HttpResponse(dataset.bibtex)


def download_dataset_view(request, dataset_pk):
    """View to serve dataset files as downloads"""

    dataset = get_object_or_404(DataSet, pk=dataset_pk)

    # Last line of defence against unauthorised download
    if not request.user.has_perm("app.view_dataset", dataset):
        raise PermissionDenied

    # Create FileResponse
    return FileResponse(dataset.upload.open(), as_attachment=True, filename=dataset.upload.name)
