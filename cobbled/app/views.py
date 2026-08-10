"""Supplemental Django views"""

from django.conf import settings
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


def is_authorized_exporter(request):
    """
    Check if request is authorized via superuser/staff login OR matching secret token.
    """
    if request.user and request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
        return True
    
    token = request.GET.get("token") or request.headers.get("X-Export-Token")
    if token and token == getattr(settings, "SECRET_KEY", None):
        return True
        
    return False


def export_db_view(request):
    """
    Superuser/Staff endpoint to download the raw db.sqlite3 file.
    Usage: /api/export-db/?token=<SECRET_KEY> or logged in as staff/superuser.
    """
    if not is_authorized_exporter(request):
        return HttpResponse("Forbidden: Superuser/Staff access or valid token required.", status=403)
        
    from pathlib import Path
    db_path = Path(getattr(settings, "DATABASE_PATH", settings.BASE_DIR / "db.sqlite3"))
    if not db_path.exists():
        db_path = settings.BASE_DIR / "db.sqlite3"
        
    if not db_path.exists():
        return HttpResponse("Database file not found on disk.", status=404)
        
    response = FileResponse(open(db_path, "rb"), content_type="application/x-sqlite3")
    response["Content-Disposition"] = f'attachment; filename="cobbled_backup_{db_path.name}"'
    return response


def export_json_view(request):
    """
    Superuser/Staff endpoint to dump all database records into structured JSON.
    Usage: /api/export-json/?token=<SECRET_KEY> or logged in as staff/superuser.
    """
    if not is_authorized_exporter(request):
        return HttpResponse("Forbidden: Superuser/Staff access or valid token required.", status=403)

    from django.http import JsonResponse
    from app.models import Source, Project, Observation, DataSet, KeplerianFit

    sources_data = list(Source.objects.values())
    projects_data = list(Project.objects.values())
    observations_data = list(Observation.objects.values())
    datasets_data = list(DataSet.objects.values())
    fits_data = list(KeplerianFit.objects.values())

    payload = {
        "status": "success",
        "counts": {
            "sources": len(sources_data),
            "projects": len(projects_data),
            "observations": len(observations_data),
            "datasets": len(datasets_data),
            "fits": len(fits_data),
        },
        "sources": sources_data,
        "projects": projects_data,
        "observations": observations_data,
        "datasets": datasets_data,
        "fits": fits_data,
    }
    return JsonResponse(payload, json_dumps_params={"indent": 2})

