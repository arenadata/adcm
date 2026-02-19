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

from logging import Logger
from pathlib import Path
from secrets import token_hex
import os

from core import secrets
from django.core.management.utils import get_random_secret_key

SECRET_TOKEN_LENGTH = 20

LOG_PREFIX = "FS secrets: "

V2_EXISTS_MSG = f"{LOG_PREFIX}OK (%s)"
MIGRATED_MSG = f"{LOG_PREFIX}migrated (%s -> %s)"
CREATED_MSG = f"{LOG_PREFIX}created (%s)"


def prepare_secrets_file(secrets_directory: Path, logger: Logger) -> Path:
    secrets_file = secrets_directory / secrets.SECRETS_FILENAME

    if secrets_file.is_file():
        # migrated installation
        logger.info(V2_EXISTS_MSG, secrets_file)

        return secrets_file

    deprecated_secrets = secrets_directory / secrets.SECRETS_FILENAME_DEPRECATED
    # django settings are unavailable here, using same code to retrieve/generate it
    django_secret_key = os.getenv("SECRET_KEY", get_random_secret_key())

    if deprecated_secrets.is_file():
        # migration required
        secrets.migrate_format(
            old_path=deprecated_secrets,
            new_path=secrets_file,
            django_secret_key=django_secret_key,
            status_service_token=token_hex(SECRET_TOKEN_LENGTH),
        )

        logger.info(MIGRATED_MSG, deprecated_secrets, secrets_file)

        return secrets_file

    # new installation, secrets must be generated

    new_secrets = secrets.ADCMSecrets.generate_new_random(
        django_secret=django_secret_key, secret_length=SECRET_TOKEN_LENGTH
    )
    secrets_as_json = secrets.SecretsFileModel(adcm=new_secrets).model_dump_json()
    secrets_file.write_text(secrets_as_json)

    logger.info(CREATED_MSG, secrets_file)

    return secrets_file
