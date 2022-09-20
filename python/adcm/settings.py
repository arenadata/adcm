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
import sys
from pathlib import Path

from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).absolute().parent.parent.parent
CONF_DIR = BASE_DIR / "data" / "conf"
SECRET_KEY_FILE = CONF_DIR / "secret_key.txt"
CONFIG_FILE = BASE_DIR / "config.json"
RUN_DIR = BASE_DIR / "data" / "run"

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
)

SOCIAL_AUTH_YANDEX_KEY = os.getenv("SOCIAL_AUTH_YANDEX_KEY")
SOCIAL_AUTH_YANDEX_SECRET = os.getenv("SOCIAL_AUTH_YANDEX_SECRET")
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
    "SECRETS_FILE": BASE_DIR / "data/var/secrets.json",

    # URL of Event Server REST API
    "API_URL": "http://localhost:8020/api/v1",
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
        "stdout": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
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
        "audit": {
            "handlers": ["stdout"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
REGEX_HOST_FQDN = r"^[a-zA-Z0-9][a-zA-Z0-9\.-]*"

CLUSTER_NAME_PATTERN = (
    r"^[a-zA-Z0-9]"  # starts with latin letter (upper/lower case) or digit
    r"[a-zA-Z0-9-\. ]*?"  # latin letters (upper/lower case), digits, hyphens, dots, whitespaces
    r"[a-zA-Z0-9]$"  # ends with latin letter (upper/lower case) or digit
)  # as a result of this pattern min_length = 2
