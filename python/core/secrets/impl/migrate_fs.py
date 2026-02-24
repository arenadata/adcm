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

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

from core.secrets._secrets import (
    ADCMSecrets,
    AnsibleSecrets,
    BackendSecrets,
    DjangoSecrets,
    StatusCheckerSecrets,
    StatusServiceSecrets,
)

NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]


@dataclass(slots=True, frozen=True)
class DeprecatedUserField:
    user: Literal["status"]
    password: NonEmptyStr


class ADCMSecretsDeprecated(BaseModel):
    adcmuser: DeprecatedUserField
    token: NonEmptyStr
    adcm_internal_token: NonEmptyStr


def migrate_format(
    old_path: Path,
    new_path: Path,
    *,
    django_secret_key: str,
    status_service_token: str,
) -> None:
    old_secrets_content = old_path.read_text(encoding="utf-8")
    old_data = ADCMSecretsDeprecated.model_validate_json(old_secrets_content)

    new_data = ADCMSecrets(
        ansible=AnsibleSecrets(ansible_vault=old_data.adcmuser.password),
        django=DjangoSecrets(secret_key=django_secret_key),
        backend=BackendSecrets(status_service_token=status_service_token),
        status_service=StatusServiceSecrets(
            adcm_token=old_data.adcm_internal_token,
        ),
        status_checker=StatusCheckerSecrets(status_service_token=old_data.token),
    )

    new_secrets_content = new_data.model_dump_json()
    new_path.write_text(new_secrets_content, encoding="utf-8")
