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
from application.loggers import APILoggingConfig
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


LOGGING = container.get(APILoggingConfig)

STATIC_ROOT = directories.base / "wwwroot/static/"

# Secrets

secrets_backend = container.get(SecretsBackend)

ADCM_TOKEN = secrets_backend.read(Secret.BACKEND_STATUS_SERVICE_TOKEN)
STATUS_SECRET_KEY = secrets_backend.read(Secret.STATUS_CHECKER_STATUS_SERVICE_TOKEN)
ANSIBLE_SECRET = secrets_backend.read(Secret.ANSIBLE_VAULT)

SECRET_KEY = secrets_backend.read(Secret.DJANGO_SECRET)

ADCM_VERSION = container.get(CurrentADCMVersion)
