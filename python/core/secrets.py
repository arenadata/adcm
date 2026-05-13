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
from operator import attrgetter
from typing import Annotated, NewType, Protocol

from pydantic import StringConstraints

from core.result import Fail, Success

# Errors


class SecretBaseError(Exception):
    ...


class ConfigurationError(SecretBaseError):
    """
    Raised when backend can't be configured
    """


class SourceError(SecretBaseError):
    """
    Raised when backend's source is unavailable or corrupted
    """


class UpdateError(SecretBaseError):
    """
    Raised when mutating operation with secrets failed for other reasons than covered by `SourceError`
    """


class RetrieveError(SecretBaseError):
    """
    Raised when backend's source is available, but secret can't be retrieved (missing or else)
    """


# "Business" secrets types

# these are for retrieval


@dataclass(slots=True, frozen=True)
class _Secret:
    path: tuple[str, ...]
    """
    Full "canonical" path to secret, including all "groups" (e.g. "adcm") and secret own key
    """

    @property
    def group(self) -> tuple[str, ...]:
        """
        Full path to group with the secret, including prefix (e.g. "adcm"), excluding key
        """
        return self.path[:-1]

    def group_as_string(self, sep: str = "/") -> str:
        return sep.join(self.group)

    @property
    def key(self) -> str:
        """
        Key for secret in group
        """
        return self.path[-1]


class Secret(Enum):
    ANSIBLE_VAULT = _Secret(path=("adcm", "ansible", "ansible_vault"))
    DJANGO_SECRET = _Secret(path=("adcm", "django", "secret_key"))
    BACKEND_STATUS_SERVICE_TOKEN = _Secret(path=("adcm", "backend", "status_service_token"))
    STATUS_SERVICE_ADCM_TOKEN = _Secret(path=("adcm", "status_service", "adcm_token"))
    STATUS_CHECKER_STATUS_SERVICE_TOKEN = _Secret(path=("adcm", "status_checker", "status_service_token"))


# these are mostly for DI

AnsibleVault = NewType("AnsibleVault", str)
DjangoSecretKey = NewType("DjangoSecretKey", str)
StatusCheckerStatusServiceToken = NewType("StatusCheckerStatusServiceToken", str)
StatusServiceADCMToken = NewType("StatusServiceADCMToken", str)


# Secrets "structure"

NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]


@dataclass(slots=True, frozen=True, repr=False)
class AnsibleSecrets:
    ansible_vault: NonEmptyStr


@dataclass(slots=True, frozen=True, repr=False)
class DjangoSecrets:
    secret_key: NonEmptyStr


@dataclass(slots=True, frozen=True, repr=False)
class BackendSecrets:
    status_service_token: NonEmptyStr
    """
    Token to authorize ADCM operations in Status Server
    """


@dataclass(slots=True, frozen=True, repr=False)
class StatusServiceSecrets:
    adcm_token: NonEmptyStr
    """
    Token to authorized Status Server operations in ADCM
    """


@dataclass(slots=True, frozen=True, repr=False)
class StatusCheckerSecrets:
    status_service_token: NonEmptyStr
    """
    Token to authorize Status Checker operations in Status Server
    """


@dataclass(slots=True)
class ADCMSecrets:
    """
    Represents all major secret groups used in ADCM one way or another.

    Follows FS storing structure, be careful if changing for flexibility.
    """

    ansible: AnsibleSecrets
    django: DjangoSecrets
    backend: BackendSecrets
    status_service: StatusServiceSecrets
    status_checker: StatusCheckerSecrets


def get_secret_from_adcm_secrets(secret_to_find: Secret, adcm_secrets: ADCMSecrets) -> str:
    prefix, *path = secret_to_find.value.path
    if prefix != "adcm":
        # safeguard for case if we've got non-adcm prefixed secrets in secrets:
        # error, because it's unhandled case by current design
        message = f"Unexpected secret for ADCM secrets: {'/'.join(secret_to_find.value.path)}"
        raise RuntimeError(message)

    dotted_path = ".".join(path)
    get_secret_from_nested_object = attrgetter(dotted_path)
    return get_secret_from_nested_object(adcm_secrets)


# Public interfaces


class SecretsBackend(Protocol):
    # management

    def write_all(self, secrets: ADCMSecrets) -> None:
        """
        Write all given secrets to a backend.
        Atomicity is not guaranteed.
        No checks on possible rewrites.
        Must throw exceptions on failure.
        """
        ...

    def read_all(
        self,
    ) -> Success[ADCMSecrets] | Fail[tuple[dict[Secret, str], dict[Secret, RetrieveError]]] | Fail[SourceError]:
        """
        Read all possible secrets from source and gather them in serialized object.

        Implementation must guarantee:
        1. Return Success only when all secrets are read successfuly.
        2. Fail with `SourceError` if at least one read failed unexpectedly.
        3. Specifying errors for all secrets on other types of failures.

        Support (and picking cases for it) of partial read
        (when both success and failure tuples are in Fail)
        is up to implementation.
        """
        ...

    # runtime retrieval

    def read(self, secret: Secret) -> str:
        """
        Read given secret.
        Must throw exceptions on failure.
        """
        ...
