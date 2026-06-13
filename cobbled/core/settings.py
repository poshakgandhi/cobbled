"""
Django settings for example project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

import random
import string
from pathlib import Path
from typing import Any

from decouple import AutoConfig

# Load .env file from the project root containing secrets
config: AutoConfig = AutoConfig()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
PROJECT_DIR: Path = Path(__file__).parent  # cobbled/core/
BASE_DIR: Path = Path(__file__).parent.parent  # cobbled/

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY: str = config("SECRET_KEY", default=None)
if not SECRET_KEY:
    SECRET_KEY = "".join(random.choice(string.ascii_lowercase) for i in range(32))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG: bool = config("DEBUG", default=False, cast=bool)
TEMPLATE_DEBUG = config("DEBUG", default=False, cast=bool)


TEMPLATES: list[dict[str, Any]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "app" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "app.context_processors.google_oauth2_client_id",
            ],
        },
    },
]

ALLOWED_HOSTS: list[str] = [
    "localhost",
    "127.0.0.1",
    ".hf.space",
    config("URL", default="gaia-cob.rsgsoton.net"),
]

################################################################################
# django: Apps & middleware
# Includes base django, allauth, and Iommi - plus corsheaders for javascript.
#################################################################################
# Application definition
INSTALLED_APPS: list[str] = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.humanize",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.contrib.sites",
    "auditlog",  # Tracks changes to models
    "allauth",  # Coherent user management with social accounts
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.usersessions",
    "iommi",  # Fast page building
    "corsheaders",  # Allow using externally-loaded javascript
    "rules",  # Object-based permissions using rules
    "app.apps.MainAppConfig",
]

# Also, if this is debug mode, include tools to speed up debug
if DEBUG:
    INSTALLED_APPS += [
        # "django_fastdev",  # Disabled to avoid django-allauth form validation crashes
        "django_pycharm_breakpoint",
    ]

MIDDLEWARE: list[str] = [
    "corsheaders.middleware.CorsMiddleware",
    "iommi.live_edit.Middleware",
    "iommi.sql_trace.Middleware",
    "iommi.profiling.Middleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "iommi.middleware",
    "iommi.main_menu.main_menu_middleware",
]

ROOT_URLCONF: str = "core.urls"
WSGI_APPLICATION: str = "core.wsgi.application"

################################################################################
# django: Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases
#################################################################################
DEFAULT_AUTO_FIELD: str = "django.db.models.AutoField"
DATABASE_PATH: Path = Path(config("DATABASE_PATH", default=str(BASE_DIR / "db.sqlite3")))
DATABASES: dict[str, dict[str, str]] = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",  # We're using a SQLite one as it's easy for dev
        "NAME": DATABASE_PATH,
    }
}

################################################################################
# django: Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/
################################################################################
LOCALE_PATHS: list[Path] = [BASE_DIR / "locale"]
TIME_ZONE: str = "UTC"
USE_I18N: bool = True
USE_TZ: bool = True

################################################################################
# django: Sites
################################################################################
# Allows multiple sites on the same server, but we only want 1. Some libraries require sites to work.
SITE_ID: int = 1

################################################################################
# django: Logging
# https://docs.djangoproject.com/en/5.2/topics/logging/
################################################################################
LOGS_ROOT: Path = BASE_DIR / "logs"
LOGS_ROOT.mkdir(parents=True, exist_ok=True)
LOGGING: dict[str, Any] = {
    "version": 1,  # the dictConfig format version
    "disable_existing_loggers": False,  # retain the default loggers
    "handlers": {
        "file_django": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_ROOT / "django.log",
            "maxBytes": 1024 * 1024 * 1,
            "backupCount": 2,
            "formatter": "verbose",
        },
        "file_app": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_ROOT / "django.app.log",
            "maxBytes": 1024 * 1024 * 1,
            "backupCount": 2,
            "formatter": "verbose",
        },
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "": {
            "level": "DEBUG",
            "handlers": ["file_django"],
            "propagate": False,
        },
        "app": {
            "level": "DEBUG",
            "handlers": ["file_app"],
            "propagate": False,
        },
    },
    "formatters": {
        "verbose": {
            "format": "{name} {levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
}

################################################################################
# django: Set the static file (e.g. CSS, Javascript)
# https://docs.djangoproject.com/en/1.7/howto/static-files/
################################################################################
MEDIA_ROOT: Path = Path(config("MEDIA_ROOT", default=str(BASE_DIR / "media")))
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
MEDIA_URL: str = "/media/"

STATIC_ROOT: Path = BASE_DIR / "static"
STATIC_URL: str = "/static/"
STATICFILES_FINDERS: list[str] = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

################################################################################
# django: Set the classes for the messages.
################################################################################
from django.contrib import messages  # noqa: E402

MESSAGE_TAGS = {
    messages.DEBUG: "alert-info",
    messages.INFO: "alert-info",
    messages.SUCCESS: "alert-success",
    messages.WARNING: "alert-warning",
    messages.ERROR: "alert-danger",
}

################################################################################
# django-iommi: Set the default style, and the main menu location.
################################################################################
# Django convention sprinkles imports through the file, so we skip 'import out of place' format warnings.
from iommi.style import Style, register_style  # noqa: E402
from iommi.style_bootstrap5 import bootstrap5, select2_enhanced_forms  # noqa: E402

# Uses font-awesome icons: https://fontawesome.com/search?ic=free&o=r
from iommi.style_font_awesome_6 import font_awesome_6  # noqa: E402

IOMMI_DEBUG: bool = config("DEBUG", default=False, cast=bool)
custom_style = Style(
    bootstrap5,
    select2_enhanced_forms,
    font_awesome_6,
    base_template="app/iommi_base.html",
)
register_style("custom_style", custom_style)
IOMMI_DEFAULT_STYLE: str = "custom_style"
IOMMI_MAIN_MENU: str = "app.main_menu.main_menu"


################################################################################
# django-allauth: Set up social accounts for Google
# https://docs.allauth.org/en/latest/index.html
################################################################################
AUTHENTICATION_BACKENDS: list[str] = [
    "rules.permissions.ObjectPermissionBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# We *only* allow logins via social accounts to minimise local account management.
# We only use google as it has the one-click login box so we can skip lots of templates.
# https://docs.allauth.org/en/latest/socialaccount/providers/google.html
SOCIALACCOUNT_ONLY: bool = config("SOCIALACCOUNT_ONLY", default=True, cast=bool)
SOCIALACCOUNT_ADAPTER: str = "app.adapter.UsernameAdapter"
SOCIALACCOUNT_PROVIDERS: dict[str, Any] = {
    "google": {
        "APP": {
            "client_id": config("GOOGLE_OAUTH2_CLIENT_ID"),
            "secret": config("GOOGLE_OAUTH2_SECRET"),
        },
        "SCOPE": ["profile", "email"],
        "OAUTH_PKCE_ENABLED": True,
    }
}
# Needed to avoid a bug with django-fastdev
SOCIALACCOUNT_FORMS = {
    "signup": "users.forms.SignupForm",
}

# Most of these are superfluous for the social accounts, but local super-user accounts care about them.
# https://docs.allauth.org/en/latest/account/advanced.html
ACCOUNT_ADAPTER: str = "app.adapter.CustomAccountAdapter"
ACCOUNT_LOGIN_METHODS: set[str] = {"email"}
ACCOUNT_SIGNUP_FIELDS: list[str] = ["username*", "email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION: str = "none"
ACCOUNT_UNIQUE_EMAIL: bool = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = "username"
ACCOUNT_LOGOUT_ON_GET: bool = True  # This is so log-out is a one-click process
LOGIN_REDIRECT_URL: str = "/"

################################################################################
# django-cors-headers: Allow javascript from other addresses.
# https://github.com/adamchainz/django-cors-headers
################################################################################
CORS_ALLOW_CREDENTIALS: bool = True
CORS_ALLOW_PRIVATE_NETWORK: bool = True
CORS_ALLOW_HEADERS: list[str] = ["*"]
CORS_ALLOWED_ORIGINS: list[str] = [
    "https://localhost",
    "http://localhost",
    "http://"+config("URL", default="gaia-cob.rsgsoton.net"),
    "https://"+config("URL", default="gaia-cob.rsgsoton.net"),
    "http://www."+config("URL", default="gaia-cob.rsgsoton.net"),
    "https://www."+config("URL", default="gaia-cob.rsgsoton.net"),
    "http://gaia-cob.rsgsoton.net",
    "https://localhost:8000",
    "http://localhost:8000",
    "https://accounts.google.com",
    "http://accounts.google.com",
    "https://aladin.cds.unistra.fr",
    "https://code.jquery.com",
    "https://irsa.ipac.caltech.edu",
]
SECURE_REFERRER_POLICY: str = (
    "no-referrer-when-downgrade"  # Or CORS blocks javascript by passing unnecessary details
)

################################################################################
# App settings: Loads these from the .env file
################################################################################
ALADIN_DEFAULT_FOV: float = config("ALADIN_DEFAULT_FOV", cast=float, default=0.2)
ALADIN_DEFAULT_SURVEY: str = config("ALADIN_DEFAULT_SURVEY", cast=str, default="'P/DSS2/color'")
if ALADIN_DEFAULT_SURVEY[0] != "'":
    ALADIN_DEFAULT_SURVEY = "'" + ALADIN_DEFAULT_SURVEY + "'"
