from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from app.main_menu import main_menu

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/", include("allauth.urls")),
    path("", include("app.urls")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += main_menu.urlpatterns()
