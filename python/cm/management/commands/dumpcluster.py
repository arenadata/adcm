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

from cm.models import Cluster
from cm.services.transition.dump import dump


def encrypt_data(pass_from_user: str, result: str) -> bytes:
    password = pass_from_user.encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=settings.DEFAULT_SALT,
        iterations=390000,
        backend=default_backend(),
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    f = Fernet(key)
    return f.encrypt(result.encode("utf-8"))


class Command(BaseCommand):
    """
    Command for dump cluster object to JSON format

    Example:
        manage.py dumpcluster --cluster_id 1 --output cluster.json
    """

    help = "Dump cluster object to JSON format"

    def add_arguments(self, parser):
        """
        Parsing command line arguments
        """
        parser.add_argument(
            "-c",
            "--cluster_id",
            action="store",
            dest="cluster_id",
            required=True,
            type=int,
            help="Cluster ID",
        )
        parser.add_argument("-o", "--output", help="Specifies file to which the output is written.")

    def handle(self, *_, cluster_id: int, output: str | None = None, **_kw) -> None:
        if not Cluster.objects.filter(id=cluster_id).exists():
            message = f"Cluster with {cluster_id} doesn't exist"
            raise ValueError(message)

        data_string = dump(cluster_id=cluster_id).model_dump_json()

        password = getpass.getpass()

        encrypted = encrypt_data(password, data_string)

        if output is not None:
            with Path(output).open(mode="wb") as f:
                f.write(encrypted)

            sys.stdout.write(f"Dump successfully done to file {output}\n")
        else:
            sys.stdout.write(encrypted.decode(settings.ENCODING_UTF_8))
