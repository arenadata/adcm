# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import string
from pathlib import Path
from secrets import token_hex

from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).absolute().parent.parent.parent
CONF_DIR = BASE_DIR / "data" / "conf"
SECRET_KEY_FILE = CONF_DIR / "secret_key.txt"
CONFIG_FILE = BASE_DIR / "config.json"
RUN_DIR = BASE_DIR / "data" / "run"
SECRETS_FILE = BASE_DIR / "data/var/secrets.json"

if SECRET_KEY_FILE.is_file():
    with open(SECRET_KEY_FILE, encoding="utf_8") as f:
        SECRET_KEY = f.read().strip()
else:
    SECRET_KEY = get_random_secret_key()

if CONFIG_FILE.is_file():
    with open(CONFIG_FILE, encoding="utf_8") as f:
        ADCM_VERSION = json.load(f)["version"]
else:
    ADCM_VERSION = "2019.02.07.00"

DEBUG = False
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = [
    "rbac",  # keep it above 'django.contrib.auth' in order to keep "createsuperuser" working
    "django_generate_secret_key",
    "django_filters",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_swagger",
    "api.apps.APIConfig",
    "corsheaders",
    "rest_framework.authtoken",
    "social_django",
    "guardian",
    "adwp_events",
    "cm.apps.CmConfig",
    "audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "audit.middleware.AuditLoginMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "corsheaders.middleware.CorsMiddleware",
]

ROOT_URLCONF = "adcm.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "adcm.wsgi.application"
LOGIN_URL = "/api/v1/auth/login/"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
    "EXCEPTION_HANDLER": "cm.errors.custom_drf_exception_handler",
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "data/var/cluster.db",
        "OPTIONS": {
            "timeout": 20,
        },
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
    "rbac.ldap.CustomLDAPBackend",
    "adcm.auth_backend.YandexOAuth2",
    "adcm.auth_backend.CustomGoogleOAuth2",
)

YANDEX_OAUTH_AUTH_URL = "https://oauth.yandex.ru/authorize"
YANDEX_OAUTH_TOKEN_URL = "https://oauth.yandex.ru/token"
YANDEX_OAUTH_USER_DATA_URL = "https://login.yandex.ru/info?format=json"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_ROOT = BASE_DIR / "wwwroot/static/"
STATIC_URL = "/static/"

ADWP_EVENT_SERVER = {
    # path to json file with Event Server secret token
    "SECRETS_FILE": SECRETS_FILE,
    # URL of Event Server REST API
    "API_URL": "http://localhost:8020/api/v1",
    "SECRET_KEY": token_hex(20)
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "formatters": {
        "adwp": {
            "format": "{asctime} {levelname} {module} {message}",
            "style": "{",
        },
        "simple_formatter": {"format": "%(asctime)s - %(levelname)s - %(message)s"},
    },
    "handlers": {
        "file": {
            "level": "DEBUG",
            "filters": ["require_debug_false"],
            "formatter": "adwp",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "data/log/adcm_debug.log",
        },
        "adwp_file": {
            "level": "DEBUG",
            "formatter": "adwp",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "data/log/adwp.log",
        },
        "background_task_file_handler": {
            "level": "DEBUG",
            "formatter": "simple_formatter",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": BASE_DIR / "data/log/cron_task.log",
            "when": "midnight",
            "backupCount": 10,
        },
        "audit_file_handler": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": BASE_DIR / "data/log/audit.log",
            "when": "midnight",
            "backupCount": 10,
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "django.template": {
            "level": "ERROR",
        },
        "django.utils.autoreload": {
            "level": "INFO",
        },
        "adwp": {
            "handlers": ["adwp_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "django_auth_ldap": {
            "handlers": ["file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "background_tasks": {
            "handlers": ["background_task_file_handler"],
            "level": "DEBUG",
            "propagate": True,
        },
        "audit": {
            "handlers": ["audit_file_handler"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

LATIN_LETTERS_DIGITS = f"{string.ascii_letters}{string.digits}"

ALLOWED_CLUSTER_NAME_START_END_CHARS = LATIN_LETTERS_DIGITS
ALLOWED_CLUSTER_NAME_MID_CHARS = f"{ALLOWED_CLUSTER_NAME_START_END_CHARS}-. _"

ALLOWED_HOST_FQDN_START_CHARS = LATIN_LETTERS_DIGITS
ALLOWED_HOST_FQDN_MID_END_CHARS = f"{ALLOWED_HOST_FQDN_START_CHARS}-."
