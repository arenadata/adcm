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

import os
import logging

from application.di.providers.environment import EnvironmentProvider
from core.secrets import (
    Secret,
    SecretsBackend,
)
from core.settings import Directories
from core.types import CurrentADCMVersion
import dishka

"""
Environment-dependant settings
"""

container = dishka.make_container(EnvironmentProvider())

# Directories & Logs

DEFAULT_LOG_LEVEL = os.getenv("LOG_LEVEL", logging.getLevelName(logging.ERROR))
DEFAULT_FILE_HANDLER_CLASS = "logging.handlers.WatchedFileHandler"

directories = container.get(Directories)

# Directories re-wiring (most of them aren't required anymore)
BASE_DIR = directories.base
BUNDLE_DIR = directories.bundles
CODE_DIR = directories.code
DOWNLOAD_DIR = directories.downloads
DATA_DIR = directories.data
RUN_DIR = directories.run
FILE_DIR = directories.files
LOG_DIR = directories.logs
TMP_DIR = directories.temp

LOG_FILE = LOG_DIR / "adcm.log"

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
    },
    "handlers": {
        # files
        "adcm_file": {
            "filters": ["require_debug_false"],
            "formatter": "adcm",
            "class": DEFAULT_FILE_HANDLER_CLASS,
            "filename": LOG_FILE,
        },
        "adcm_debug_file": {
            "filters": ["require_debug_false"],
            "formatter": "adcm",
            "class": DEFAULT_FILE_HANDLER_CLASS,
            "filename": LOG_DIR / "adcm_debug.log",
        },
        "task_runner_err_file": {
            "filters": ["require_debug_false"],
            "formatter": "adcm",
            "class": DEFAULT_FILE_HANDLER_CLASS,
            "filename": LOG_DIR / "task_runner.err",
        },
        "background_task_file_handler": {
            "formatter": "adcm",
            "class": DEFAULT_FILE_HANDLER_CLASS,
            "filename": LOG_DIR / "cron_task.log",
        },
        "ldap_file_handler": {
            "class": DEFAULT_FILE_HANDLER_CLASS,
            "formatter": "adcm",
            "filename": LOG_DIR / "ldap.log",
        },
        # streams
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
        # special
        "audit_file_handler": {
            "class": DEFAULT_FILE_HANDLER_CLASS,
            "filename": LOG_DIR / "audit.log",
        },
    },
    "loggers": {
        "adcm": {
            "handlers": ["adcm_file"],
            "level": os.getenv("ADCM_LOG_LEVEL", DEFAULT_LOG_LEVEL),
            "propagate": True,
        },
        "django": {
            "handlers": ["adcm_debug_file"],
            "level": os.getenv("ADCM_LOG_LEVEL", DEFAULT_LOG_LEVEL),
            "propagate": True,
        },
        "background_tasks": {
            "handlers": ["background_task_file_handler"],
            "level": os.getenv("BACKGROUND_TASKS_LOG_LEVEL", DEFAULT_LOG_LEVEL),
            "propagate": True,
        },
        "audit": {
            "handlers": ["audit_file_handler"],
            "level": os.getenv("AUDIT_LOG_LEVEL", logging.getLevelName(logging.INFO)),
            "propagate": True,
        },
        "task_runner_err": {
            "handlers": ["task_runner_err_file"],
            "level": os.getenv("TASK_RUNNER_LOG_LEVEL", DEFAULT_LOG_LEVEL),
            "propagate": True,
        },
        "stream_std": {
            "handlers": ["stream_stdout_handler", "stream_stderr_handler"],
            "level": DEFAULT_LOG_LEVEL,
        },
        "django_auth_ldap": {
            "handlers": ["ldap_file_handler"],
            "level": os.getenv("LDAP_LOG_LEVEL", DEFAULT_LOG_LEVEL),
            "propagate": True,
        },
    },
}

STATIC_ROOT = directories.base / "wwwroot/static/"

# Secrets

secrets_backend = container.get(SecretsBackend)

ADCM_TOKEN = secrets_backend.read(Secret.BACKEND_STATUS_SERVICE_TOKEN)
STATUS_SECRET_KEY = secrets_backend.read(Secret.STATUS_CHECKER_STATUS_SERVICE_TOKEN)
ANSIBLE_SECRET = secrets_backend.read(Secret.ANSIBLE_VAULT)

SECRET_KEY = secrets_backend.read(Secret.DJANGO_SECRET)

ADCM_VERSION = container.get(CurrentADCMVersion)
