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
from secrets import token_hex
from typing import Annotated, Literal, NewType

from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]

# "Business" secrets types

AnsibleVault = NewType("AnsibleVault", str)

# Secrets "structure"


@dataclass(slots=True, frozen=True)
class AnsibleSecrets:
    ansible_vault: NonEmptyStr


@dataclass(slots=True, frozen=True)
class DjangoSecrets:
    secret_key: NonEmptyStr


@dataclass(slots=True, frozen=True)
class BackendSecrets:
    status_service_token: NonEmptyStr
    """
    Token to authorize ADCM operations in Status Server
    """


@dataclass(slots=True, frozen=True)
class StatusServiceSecrets:
    adcm_token: NonEmptyStr
    """
    Token to authorized Status Server operations in ADCM
    """


@dataclass(slots=True, frozen=True)
class StatusCheckerSecrets:
    status_service_token: NonEmptyStr
    """
    Token to authorize Status Checker operations in Status Server
    """


class ADCMSecrets(BaseModel):
    """
    Represents all major secret groups used in ADCM one way or another.

    Follows FS storing structure, be careful if changing for flexibility.
    """

    ansible: AnsibleSecrets
    django: DjangoSecrets
    backend: BackendSecrets
    status_service: StatusServiceSecrets
    status_checker: StatusCheckerSecrets

    model_config = ConfigDict(extra="forbid", frozen=True)

    @classmethod
    def generate_new_random(cls, django_secret: str, secret_length: int):
        return cls(
            ansible=AnsibleSecrets(ansible_vault=token_hex(secret_length)),
            django=DjangoSecrets(secret_key=django_secret),
            backend=BackendSecrets(status_service_token=token_hex(secret_length)),
            status_service=StatusServiceSecrets(adcm_token=token_hex(secret_length)),
            status_checker=StatusCheckerSecrets(status_service_token=token_hex(secret_length)),
        )


class SecretsFileModel(BaseModel):
    """
    Represents structure of secrets file on FS (with extra nesting level)
    """

    adcm: ADCMSecrets

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
    FILE_SYSTEM = "FileSystemBackend"
    OPEN_BAO = "..."
