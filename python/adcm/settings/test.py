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
import uuid
import logging
import pathlib
import tempfile

from .shared.base import *  # noqa
from .shared.constants import *  # noqa

# Important overrides
MIDDLEWARE.remove("api_v2.utils.di.DishkaMiddleware")  # noqa: F405
MIDDLEWARE.insert(0, "api_v2.tests.setup.overrides.DishkaMiddleware")  # noqa: F405

logging.disable(logging.CRITICAL)

# Definition of important dependant settings

ADCM_TOKEN = "adcm-token-test"
STATUS_SECRET_KEY = "status-secret-key-test"
ANSIBLE_SECRET = "ansible-secret-test"

SECRET_KEY = "secret-key-test"

ADCM_VERSION = os.getenv("ADCM_VERSION", "2.0.0")

# Independent per launch

# for avoiding tempdir creation on start
tempdir_path = pathlib.Path(tempfile.gettempdir(), uuid.uuid4().hex)

BASE_DIR = tempdir_path
DATA_DIR = BASE_DIR
BUNDLE_DIR = DATA_DIR / "bundle"
DOWNLOAD_DIR = DATA_DIR / "download"
RUN_DIR = DATA_DIR / "run"
FILE_DIR = DATA_DIR / "file"
LOG_DIR = DATA_DIR / "log"
TMP_DIR = DATA_DIR / "tmp"
CODE_DIR = pathlib.Path(__file__).parent.parent.parent

DEFAULT_DISHKA_PROVIDERS = "api_v2.tests.setup.overrides.get_default_overridden_providers"

# Strictly for tests

TEST_RUNNER = "adcm.tests.runner.SubTestParallelRunner"
