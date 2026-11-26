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

from ansible.parsing.vault import VaultAES256
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .shared.base import *  # noqa
from .shared.constants import *  # noqa
from .shared.database import *  # noqa

# Important overrides
MIDDLEWARE.remove("api_v2.utils.di.DishkaMiddleware")  # noqa: F405
MIDDLEWARE.insert(0, "tests.dependencies.DishkaMiddleware")  # noqa: F405

# default PBKDF2 costs "a lot" per hash/check, which is paid on each user creation and login
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


# same for ansible vault: its PBKDF2 (10k iterations) is paid on every secret encrypt/decrypt.
# Ciphertexts become unreadable for real ansible, so tests running ansible-playbook on secrets won't work.
def _cheap_vault_key(b_password: bytes, b_salt: bytes, key_length: int, iv_length: int) -> bytes:
    return PBKDF2HMAC(algorithm=SHA256(), length=2 * key_length + iv_length, salt=b_salt, iterations=1).derive(
        b_password
    )


VaultAES256._create_key_cryptography = staticmethod(_cheap_vault_key)

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
