"""A collection of custom actions to pass as pre/post-handlers to Iommi components"""

from django.contrib.auth.models import User
from django.http import HttpResponseRedirect

from app.models import DataSet


def validate_generic(table, request, **_):
    queryset = table.bulk_queryset()
    queryset.update(is_valid=True)
    return HttpResponseRedirect(request.META["HTTP_REFERER"])


def validate_user_by_researcher(table, request, **_):
    researcherset = table.bulk_queryset()
    userset = User.objects.filter(researcher__in=researcherset)
    userset.update(is_active=True)
    return HttpResponseRedirect(request.META["HTTP_REFERER"])


def validate_dataset_by_observation(table, request, **_):
    observationset = table.bulk_queryset()
    datasetset = DataSet.objects.filter(observation__in=observationset)
    datasetset.update(is_valid=True)
    return HttpResponseRedirect(request.META["HTTP_REFERER"])
