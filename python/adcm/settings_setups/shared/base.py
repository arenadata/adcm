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

"""
Real Django settings that aren't dependant on environment
"""

import os

WSGI_APPLICATION = "adcm.wsgi.application"

ANSIBLE_VAULT_HEADER = "$ANSIBLE_VAULT;1.1;AES256"
DEFAULT_SALT = b'"j\xebi\xc0\xea\x82\xe0\xa8\xba\x9e\x12E>\x11D'

DEBUG = os.getenv("DEBUG") in {"1", "True", "true"}

ALLOWED_HOSTS = ["*"]
COMMON_APPS = [
    "rbac",  # keep it above 'django.contrib.auth' in order to keep "createsuperuser" working
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "social_django",
    "guardian",
    "cm.apps.CmConfig",
    "audit",
    "application",
]

API_APPS = [
    "django_filters",
    "rest_framework",
    "rest_framework.authtoken",
    "api_v2",
    "corsheaders",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "health",
]

INSTALLED_APPS = [*COMMON_APPS, *API_APPS]

MIDDLEWARE = [
    "api_v2.utils.di.DishkaMiddleware",
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

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
    "rbac.ldap.CustomLDAPBackend",
)

ROOT_URLCONF = "adcm.urls"

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
    "EXCEPTION_HANDLER": "api_v2.errors.custom_drf_exception_handler",
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    "DEFAULT_VERSION": "v2",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "JSON_UNDERSCOREIZE": {
        "ignore_fields": ("config", "configSchema", "adcmMeta", "properties"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "ADCM API",
    "DESCRIPTION": "Arenadata Cluster Manager",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v[2-9]",
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "PREPROCESSING_HOOKS": [
        "adcm.api_schema.preprocess_hook_exclude_internal_from_schema",
    ],
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "adcm.api_schema.convert_pks_in_path_to_camel_case_ids",
        # The order is important, `postprocess_hook_exclude_advanced_filters` hook
        # must be called before `camelize_serializer_fields`
        "adcm.api_schema.postprocess_hook_exclude_advanced_filters",
        "drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields",
        "adcm.api_schema.make_all_fields_required_in_response",
        "adcm.api_schema.add_additional_properties",
    ],
    "ENUM_NAME_OVERRIDES": {
        "MaintenanceModeEnum": "cm.models.MaintenanceMode",
        "MaintenanceModeChangeEnum": ("on", "off"),
        "JobStatusEnum": "cm.models.JobStatus",
        "LicenseStatusEnum": "cm.models.LICENSE_STATE",
        "SignatureStatusEnum": "cm.models.SignatureStatus",
        "ObjectStatusEnum": ("up", "down"),
        "ObjectTypeEnum": "cm.models.ObjectType",
        "ClusterServiceEnum": ("cluster", "service"),
        "OriginType": "rbac.models.OriginType",
        "RoleTypeEnum": "rbac.models.RoleTypes",
        "CheckLogStorageTypeEnum": ("check",),
    },
    "GENERIC_ADDITIONAL_PROPERTIES": None,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAuthenticated"],
}

CSP_DEFAULT_SRC = ["'self'", "blob:"]
CSP_STYLE_SRC = ["'self'", "'unsafe-inline'", "*.googleapis.com"]
CSP_IMG_SRC = ["'self'", "cdn.redoc.ly", "data:"]
CSP_FONT_SRC = ["'self'", "fonts.gstatic.com"]
CSP_FRAME_ANCESTORS = ["'none'"]

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"

SESSION_EXPIRE_AT_BROWSER_CLOSE = True


# Recheck if required

LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/admin/intro/"

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

# Remove after ensuring that they are not used during config.json forming

CONSUL_URL = os.getenv("CONSUL_URL")
CONSUL_DATACENTER = os.getenv("CONSUL_DATACENTER")
CONSUL_CACERT_FILE = os.getenv("CONSUL_CACERT_FILE")

STATUS_SERVICE_BASE_PATH = os.getenv("STATUS_SERVICE_BASE_PATH", "/status/api/v1/")
