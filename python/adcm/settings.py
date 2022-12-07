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
import os
import string
import sys
from pathlib import Path

from django.core.management.utils import get_random_secret_key

from cm.utils import dict_json_get_or_create, get_adcm_token

ENCODING_UTF_8 = "utf-8"

BASE_DIR = os.getenv("ADCM_BASE_DIR")
if BASE_DIR:
    BASE_DIR = Path(BASE_DIR)
else:
    BASE_DIR = Path(__file__).absolute().parent.parent.parent

CONF_DIR = BASE_DIR / "data" / "conf"
CONFIG_FILE = BASE_DIR / "config.json"
SECRET_KEY_FILE = CONF_DIR / "secret_key.txt"
STACK_DIR = os.getenv("ADCM_STACK_DIR", BASE_DIR)
BUNDLE_DIR = STACK_DIR / "data" / "bundle"
CODE_DIR = BASE_DIR / "python"
DOWNLOAD_DIR = Path(STACK_DIR, "data", "download")
RUN_DIR = BASE_DIR / "data" / "run"
FILE_DIR = STACK_DIR / "data" / "file"
LOG_DIR = BASE_DIR / "data" / "log"
LOG_FILE = LOG_DIR / "adcm.log"
SECRETS_FILE = BASE_DIR / "data" / "var" / "secrets.json"
ADCM_TOKEN_FILE = BASE_DIR / "data/var/adcm_token"
PYTHON_SITE_PACKAGES = Path(
    sys.exec_prefix, f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
)

ANSIBLE_VAULT_HEADER = "$ANSIBLE_VAULT;1.1;AES256"
DEFAULT_SALT = b'"j\xebi\xc0\xea\x82\xe0\xa8\xba\x9e\x12E>\x11D'

ADCM_TOKEN = get_adcm_token()
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

if SECRET_KEY_FILE.is_file():
    with open(SECRET_KEY_FILE, encoding=ENCODING_UTF_8) as f:
        SECRET_KEY = f.read().strip()
else:
    SECRET_KEY = get_random_secret_key()

if CONFIG_FILE.is_file():
    with open(CONFIG_FILE, encoding=ENCODING_UTF_8) as f:
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
LOGIN_REDIRECT_URL = "/admin/intro/"

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
    # path to json file with Event Server secret token
    "SECRETS_FILE": SECRETS_FILE,
    # URL of Event Server REST API
    "API_URL": "http://localhost:8020/api/v1",
    "SECRET_KEY": ADCM_TOKEN,
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
