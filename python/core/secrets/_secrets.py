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
from secrets import choice, token_hex
import json
import string

from core.secrets._types import (
    ADCMSecrets,
    ADCMSecretsDeprecated,
    AnsibleSecrets,
    BackendSecrets,
    DjangoSecrets,
    StatusServiceSecrets,
)

ENV_BACKEND = "SECRET_BACKEND"
FILENAME = "secrets_v2.json"
FILENAME_DEPRECATED = "secrets.json"


class SecretsError(Exception):
    pass


def migrate_format(old_path: Path, new_path: Path, django_secret_key: str) -> None:
    with old_path.open(mode="r") as f:
        old_data = ADCMSecretsDeprecated(**json.load(f))

    new_data = ADCMSecrets(
        ansible=AnsibleSecrets(ansible_vault=old_data.adcmuser.password),
        django=DjangoSecrets(secret_key=django_secret_key),
        backend=BackendSecrets(status_service_token=old_data.adcm_internal_token),
        status_service=StatusServiceSecrets(adcm_token=old_data.token),
    )

    with new_path.open(mode="w") as f:
        json.dump(new_data.model_dump(mode="json"), f)


def new(django_secret: str | None = None, token_length: int = 20) -> dict:
    django_secret = django_secret or _get_random_django_secret_key(length=50)
    return {
        "ansible": {"ansible_vault": token_hex(token_length)},
        "django": {"secret_key": django_secret},
        "backend": {"status_service_token": token_hex(token_length)},
        "status_service": {"adcm_token": token_hex(token_length)},
    }


# copied from django.core.management.utils.get_random_secret_key
def _get_random_django_secret_key(length: int) -> str:
    chars = f"{string.ascii_lowercase}{string.digits}!@#$%^&*(-_=+)"

    return "".join(choice(chars) for _ in range(length))
