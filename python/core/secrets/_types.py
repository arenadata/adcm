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
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]


@dataclass(slots=True, frozen=True)
class AnsibleSecrets:
    ansible_vault: NonEmptyStr


@dataclass(slots=True, frozen=True)
class DjangoSecrets:
    secret_key: NonEmptyStr


@dataclass(slots=True, frozen=True)
class BackendSecrets:
    status_service_token: NonEmptyStr


@dataclass(slots=True, frozen=True)
class StatusServiceSecrets:
    adcm_token: NonEmptyStr


class ADCMSecrets(BaseModel):
    ansible: AnsibleSecrets
    django: DjangoSecrets
    backend: BackendSecrets
    status_service: StatusServiceSecrets

    model_config = ConfigDict(extra="forbid", frozen=True)


@dataclass(slots=True, frozen=True)
class DeprecatedUserField:
    user: Literal["status"]
    password: NonEmptyStr


class ADCMSecretsDeprecated(BaseModel):
    adcmuser: DeprecatedUserField
    token: NonEmptyStr
    adcm_internal_token: NonEmptyStr


class SecretsSource(str, Enum):
    FS = "FileSystemBackend"
    OPEN_BAO = "..."
