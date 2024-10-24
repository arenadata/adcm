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

from pathlib import Path
import sys
import base64
import getpass

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from cm.services.transition.load import load
from cm.services.transition.types import TransitionPayload


def decrypt_file(pass_from_user: str, file: str) -> bytes:
    password = pass_from_user.encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=settings.DEFAULT_SALT,
        iterations=390000,
        backend=default_backend(),
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return Fernet(key).decrypt(file.encode())


class Command(BaseCommand):
    """
    Command for load cluster object from JSON file

    Example:
        manage.py loadcluster cluster.json
    """

    help = "Load cluster object from JSON format"

    def add_arguments(self, parser):
        """Parsing command line arguments"""
        parser.add_argument("file_path", nargs="?")

    def handle(self, *_, file_path: str, **_kw):  # noqa: ARG002
        encrypted_dump = Path(file_path)

        if not encrypted_dump.is_file():
            message = f"Dump file doesn't exist or isn't a file at {encrypted_dump}"
            raise ValueError(message)

        password = getpass.getpass()

        self._write("Decrypting dump file...")
        decrypted_string = decrypt_file(password, encrypted_dump.read_text()).decode("utf-8")

        self._write("Validating data...")
        payload = TransitionPayload.model_validate_json(decrypted_string)

        if payload.adcm_version != settings.ADCM_VERSION:
            message = (
                f"ADCM versions do not match, dump version: {payload.adcm_version}, "
                f"load version: {settings.ADCM_VERSION}"
            )
            raise ValueError(message)

        with atomic():
            cluster_id = load(data=payload, report=self._write)

        sys.stdout.write(f"Load successfully ended, cluster {payload.cluster.name} created with id {cluster_id}\n")

    def _write(self, line: str) -> None:
        if not line.endswith("\n"):
            line += "\n"

        sys.stdout.write(line)
