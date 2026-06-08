from django.conf import settings
from django.http import HttpRequest


def google_oauth2_client_id(request: HttpRequest) -> dict[str, str]:
    """
    Adds the OAuth app client ID to the context, for the popup on the core template.

    :param request: The current request.
    :return: A dict with the client ID in, for template rendering.
    """
    return {
        "GOOGLE_OAUTH2_CLIENT_ID": settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"],
    }
