import os
import sys
import traceback
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

_application = get_wsgi_application()

def application(environ, start_response):
    try:
        return _application(environ, start_response)
    except Exception as exc:
        sys.stderr.write("=== UNHANDLED WSGI EXCEPTION ===\n")
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        raise exc
