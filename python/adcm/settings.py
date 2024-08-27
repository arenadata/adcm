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

from json import JSONDecodeError
from pathlib import Path
import os
import sys
import json
import string
import logging

from django.core.management.utils import get_random_secret_key

from adcm.settings_utils import dict_json_get_or_create, get_adcm_token

ENCODING_UTF_8 = "utf-8"

API_URL = "http://localhost:8020/api/v1/"
BASE_DIR = os.getenv("ADCM_BASE_DIR")
BASE_DIR = Path(BASE_DIR) if BASE_DIR else Path(__file__).absolute().parent.parent.parent

STACK_DIR = os.getenv("ADCM_STACK_DIR", BASE_DIR)
BUNDLE_DIR = STACK_DIR / "data" / "bundle"
CODE_DIR = BASE_DIR / "python"
DOWNLOAD_DIR = Path(STACK_DIR, "data", "download")
DATA_DIR = BASE_DIR / "data"
RUN_DIR = DATA_DIR / "run"
FILE_DIR = STACK_DIR / "data" / "file"
LOG_DIR = DATA_DIR / "log"
VAR_DIR = DATA_DIR / "var"
TMP_DIR = DATA_DIR / "tmp"
LOG_FILE = LOG_DIR / "adcm.log"
SECRETS_FILE = VAR_DIR / "secrets.json"
ADCM_TOKEN_FILE = VAR_DIR / "adcm_token"
PYTHON_SITE_PACKAGES = Path(
    sys.exec_prefix,
    f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages",
)

ANSIBLE_VAULT_HEADER = "$ANSIBLE_VAULT;1.1;AES256"
DEFAULT_SALT = b'"j\xebi\xc0\xea\x82\xe0\xa8\xba\x9e\x12E>\x11D'


ADCM_TOKEN = get_adcm_token(ADCM_TOKEN_FILE)
if SECRETS_FILE.is_file():
    with open(SECRETS_FILE, encoding=ENCODING_UTF_8) as f:
        data = json.load(f)
        STATUS_SECRET_KEY = data["token"]
        ANSIBLE_SECRET = data["adcmuser"]["password"]
        # workaround to insert `adcm_internal_token` into existing SECRETS_FILE after startup
        if data.get("adcm_internal_token") is None:
            dict_json_get_or_create(path=SECRETS_FILE, field="adcm_internal_token", value=ADCM_TOKEN)

else:
    STATUS_SECRET_KEY = ""
    ANSIBLE_SECRET = ""

SECRET_KEY = os.getenv("SECRET_KEY", get_random_secret_key())

ADCM_VERSION = os.getenv("ADCM_VERSION", "2.0.0")

DEBUG = os.getenv("DEBUG") in {"1", "True", "true"}
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = [
    "rbac",  # keep it above 'django.contrib.auth' in order to keep "createsuperuser" working
    "django_filters",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "api.apps.APIConfig",
    "rest_framework.authtoken",
    "social_django",
    "guardian",
    "cm.apps.CmConfig",
    "audit",
    "api_v2",
    "corsheaders",
    "drf_spectacular",
    "drf_spectacular_sidecar",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "audit.middleware.LoginMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "djangorestframework_camel_case.middleware.CamelCaseMiddleWare",
    "audit.alt.middleware.AuditMiddleware",
]
if not DEBUG:
    MIDDLEWARE = [*MIDDLEWARE, "csp.middleware.CSPMiddleware"]

CSP_DEFAULT_SRC = ["'self'", "blob:"]
CSP_STYLE_SRC = ["'self'", "'unsafe-inline'", "*.googleapis.com"]
CSP_IMG_SRC = ["'self'", "cdn.redoc.ly", "data:"]
CSP_FONT_SRC = ["'self'", "fonts.gstatic.com"]
CSP_FRAME_ANCESTORS = ["'none'"]

ROOT_URLCONF = "adcm.urls"

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

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
LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/admin/intro/"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "cm.errors.custom_drf_exception_handler",
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    "DEFAULT_VERSION": "v2",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "JSON_UNDERSCOREIZE": {
        "ignore_fields": ("config", "configSchema", "adcmMeta", "properties"),
    },
}


def get_db_options() -> dict:
    db_options = os.getenv("DB_OPTIONS", "{}")
    try:
        parsed = json.loads(db_options)
    except JSONDecodeError as json_error:
        raise RuntimeError("Failed to decode DB_OPTIONS as JSON") from json_error
    if not isinstance(parsed, dict):
        raise RuntimeError("DB_OPTIONS should be dict")  # noqa: TRY004
    return parsed


DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

if all((DB_PASS, DB_NAME, DB_USER, DB_HOST, DB_PORT)):
    DB_DEFAULT = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASS,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
        "CONN_MAX_AGE": 60,
        "OPTIONS": get_db_options(),
    }
else:
    DB_DEFAULT = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "data/var/cluster.db",
        "OPTIONS": {
            "timeout": 20,
        },
    }

DATABASES = {"default": DB_DEFAULT}

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
    "rbac.ldap.CustomLDAPBackend",
    "adcm.auth_backend.CustomYandexOAuth2",
    "adcm.auth_backend.CustomGoogleOAuth2",
)

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_ROOT = BASE_DIR / "wwwroot/static/"
STATIC_URL = "/static/"

ADWP_EVENT_SERVER = {
    "SECRETS_FILE": SECRETS_FILE,
    "API_URL": "http://localhost:8020/api/v1",
    "SECRET_KEY": ADCM_TOKEN,
}

LOG_LEVEL = os.getenv("LOG_LEVEL", logging.getLevelName(logging.ERROR))

if not DEBUG:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "require_debug_false": {
                "()": "django.utils.log.RequireDebugFalse",
            },
        },
        "formatters": {
            "adcm": {
                "format": "{asctime} {levelname} {module} {message}",
                "style": "{",
            },
            "ldap": {
                "format": "{levelname} {module}: {message}",
                "style": "{",
            },
        },
        "handlers": {
            "adcm_file": {
                "filters": ["require_debug_false"],
                "formatter": "adcm",
                "class": "logging.FileHandler",
                "filename": LOG_FILE,
            },
            "adcm_debug_file": {
                "filters": ["require_debug_false"],
                "formatter": "adcm",
                "class": "logging.FileHandler",
                "filename": LOG_DIR / "adcm_debug.log",
            },
            "task_runner_err_file": {
                "filters": ["require_debug_false"],
                "formatter": "adcm",
                "class": "logging.FileHandler",
                "filename": LOG_DIR / "task_runner.err",
            },
            "background_task_file_handler": {
                "formatter": "adcm",
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": LOG_DIR / "cron_task.log",
                "when": "midnight",
                "backupCount": 10,
            },
            "audit_file_handler": {
                "class": "adcm.custom_loggers.LockingTimedRotatingFileHandler",
                "filename": LOG_DIR / "audit.log",
                "when": "midnight",
                "backupCount": 10,
            },
            "stream_stdout_handler": {
                "class": "logging.StreamHandler",
                "formatter": "adcm",
                "stream": "ext://sys.stdout",
            },
            "stream_stderr_handler": {
                "class": "logging.StreamHandler",
                "formatter": "adcm",
                "stream": "ext://sys.stderr",
            },
            "ldap_file_handler": {
                "class": "logging.FileHandler",
                "formatter": "adcm",
                "filename": LOG_DIR / "ldap.log",
            },
        },
        "loggers": {
            "adcm": {
                "handlers": ["adcm_file"],
                "level": LOG_LEVEL,
                "propagate": True,
            },
            "django": {
                "handlers": ["adcm_debug_file"],
                "level": LOG_LEVEL,
                "propagate": True,
            },
            "background_tasks": {
                "handlers": ["background_task_file_handler"],
                "level": LOG_LEVEL,
                "propagate": True,
            },
            "audit": {
                "handlers": ["audit_file_handler"],
                "level": "INFO",
                "propagate": True,
            },
            "task_runner_err": {
                "handlers": ["task_runner_err_file"],
                "level": LOG_LEVEL,
                "propagate": True,
            },
            "stream_std": {
                "handlers": ["stream_stdout_handler", "stream_stderr_handler"],
                "level": LOG_LEVEL,
            },
            "django_auth_ldap": {"handlers": ["ldap_file_handler"], "level": LOG_LEVEL, "propagate": True},
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

LATIN_LETTERS_DIGITS = f"{string.ascii_letters}{string.digits}"

ALLOWED_CLUSTER_NAME_START_END_CHARS = LATIN_LETTERS_DIGITS
ALLOWED_CLUSTER_NAME_MID_CHARS = f"{ALLOWED_CLUSTER_NAME_START_END_CHARS}-. _"

ALLOWED_HOST_FQDN_START_CHARS = LATIN_LETTERS_DIGITS
ALLOWED_HOST_FQDN_MID_END_CHARS = f"{ALLOWED_HOST_FQDN_START_CHARS}-."

ADCM_TURN_ON_MM_ACTION_NAME = "adcm_turn_on_maintenance_mode"
ADCM_TURN_OFF_MM_ACTION_NAME = "adcm_turn_off_maintenance_mode"
ADCM_HOST_TURN_ON_MM_ACTION_NAME = "adcm_host_turn_on_maintenance_mode"
ADCM_HOST_TURN_OFF_MM_ACTION_NAME = "adcm_host_turn_off_maintenance_mode"
ADCM_DELETE_SERVICE_ACTION_NAME = "adcm_delete_service"
ADCM_SERVICE_ACTION_NAMES_SET = {
    ADCM_TURN_ON_MM_ACTION_NAME,
    ADCM_TURN_OFF_MM_ACTION_NAME,
    ADCM_HOST_TURN_ON_MM_ACTION_NAME,
    ADCM_HOST_TURN_OFF_MM_ACTION_NAME,
    ADCM_DELETE_SERVICE_ACTION_NAME,
}
ADCM_MM_ACTION_FORBIDDEN_PROPS_SET = {"config", "hc_acl", "ui_options"}
ADCM_HIDDEN_USERS = {"status", "system"}

STACK_COMPLEX_FIELD_TYPES = {"json", "structure", "list", "map", "secretmap"}
STACK_FILE_FIELD_TYPES = {"file", "secretfile"}
STACK_NUMERIC_FIELD_TYPES = {"integer", "float"}
SECURE_PARAM_TYPES = {"password", "secrettext"}

EMPTY_REQUEST_STATUS_CODE = 32
VALUE_ERROR_STATUS_CODE = 8
EMPTY_STATUS_STATUS_CODE = 4
STATUS_REQUEST_TIMEOUT = 0.1

JOB_TYPE = "job"
TASK_TYPE = "task"

SPECTACULAR_SETTINGS = {
    "TITLE": "ADCM API",
    "DESCRIPTION": "Arenadata Cluster Manager",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]",
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "adcm.api_schema.convert_pks_in_path_to_camel_case_ids",
        "drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields",
        "adcm.api_schema.make_all_fields_required_in_response",
    ],
}

USERNAME_MAX_LENGTH = 150

STDOUT_STDERR_LOG_CUT_LENGTH = 1500
STDOUT_STDERR_LOG_LINE_CUT_LENGTH = 1000
STDOUT_STDERR_LOG_MAX_UNCUT_LENGTH = STDOUT_STDERR_LOG_CUT_LENGTH * STDOUT_STDERR_LOG_LINE_CUT_LENGTH
STDOUT_STDERR_TRUNCATED_LOG_MESSAGE = "<Truncated. Download full version via link>"

TEST_RUNNER = "adcm.tests.runner.SubTestParallelRunner"
