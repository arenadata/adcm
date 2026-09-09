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

from dataclasses import dataclass, field
from pathlib import Path

from core.result import Fail, Success
from core.secrets import (
    ADCMSecrets,
    AnsibleSecrets,
    BackendSecrets,
    ConfigurationError,
    DjangoSecrets,
    RetrieveError,
    Secret,
    SecretsBackend,
    SourceError,
    StatusCheckerSecrets,
    StatusServiceSecrets,
    UpdateError,
    get_secret_from_adcm_secrets,
)
from requests import RequestException
from typing_extensions import Self
import hvac.exceptions


@dataclass(slots=True)
class ClientSettings:
    # main

    url: str
    token_file: Path
    mount_point: str

    # SSL

    client_cert_file: str | None = None
    client_key_file: str | None = None
    ca_file: str | None = None

    # optional features

    namespace: str | None = None


@dataclass(slots=True)
class VaultSecretsBackend(SecretsBackend):
    # Read/write implementation relies on fact that each node (path) is containing only one field.
    # It is critical for write operations, important for read.
    # When you'll get more than one secret per node, this approach should be revisited.

    client: hvac.Client
    mount_point: str

    _cache: dict[Secret, str] = field(default_factory=dict, repr=False)
    _mount_point_check_result: bool | None = field(default=None)
    """
    None when check wasn't performed, otherwise check result value is stored
    """

    @classmethod
    def from_settings(cls, settings: ClientSettings) -> Self:
        client = _build_client(settings)
        return cls(client=client, mount_point=settings.mount_point)

    def write_all(self, secrets: ADCMSecrets) -> None:
        self._cache.clear()

        for secret in Secret:
            value = get_secret_from_adcm_secrets(secret_to_find=secret, adcm_secrets=secrets)
            self._write_secret(secret=secret, value=value)

    def read_all(
        self,
    ) -> Success[ADCMSecrets] | Fail[tuple[dict[Secret, str], dict[Secret, RetrieveError]]] | Fail[SourceError]:
        retrieved_secrets = {}
        fails = {}

        for secret in Secret:
            try:
                retrieved_secrets[secret] = self.read(secret)
            except RetrieveError as e:
                fails[secret] = e
            except SourceError as e:
                return Fail(e)

        if fails:
            return Fail((retrieved_secrets, fails))

        # it MAY be a good idea to build from retrieved secrets dict and validate it:
        # that way desync in secrets and ADCMSecrets may be revealed,
        # yet use cases aren't stable for now, maybe other approach / return value will be used

        ansible_secrets = AnsibleSecrets(ansible_vault=retrieved_secrets[Secret.ANSIBLE_VAULT])
        backend_secrets = BackendSecrets(status_service_token=retrieved_secrets[Secret.BACKEND_STATUS_SERVICE_TOKEN])
        django_secrets = DjangoSecrets(secret_key=retrieved_secrets[Secret.DJANGO_SECRET])
        status_service_secrets = StatusServiceSecrets(adcm_token=retrieved_secrets[Secret.STATUS_SERVICE_ADCM_TOKEN])
        status_checker_secrets = StatusCheckerSecrets(
            status_service_token=retrieved_secrets[Secret.STATUS_CHECKER_STATUS_SERVICE_TOKEN]
        )
        adcm_secrets = ADCMSecrets(
            ansible=ansible_secrets,
            backend=backend_secrets,
            django=django_secrets,
            status_service=status_service_secrets,
            status_checker=status_checker_secrets,
        )

        return Success(adcm_secrets)

    def read(self, secret: Secret) -> str:
        return self._read_secret(secret)

    def check_connection(self) -> bool:
        """Return ``True`` when the Vault server is reachable and responsive."""
        try:
            return bool(self.client.sys.is_initialized())
        except (hvac.exceptions.VaultError, RequestException):
            return False

    def _read_secret(self, secret: Secret) -> str:
        if secret in self._cache:
            return self._cache[secret]

        secret_value = self._retrieve_secret_from_vault(path=secret.value.group_as_string(), field=secret.value.key)
        self._cache[secret] = secret_value

        return secret_value

    def _write_secret(self, secret: Secret, value: str) -> None:
        self._write_secret_to_vault(path=secret.value.group_as_string(), value={secret.value.key: value})

    def _write_secret_to_vault(self, path: str, value: dict) -> None:
        try:
            self.client.secrets.kv.v2.create_or_update_secret(path=path, secret=value, mount_point=self.mount_point)
        except hvac.exceptions.VaultError as e:
            message = f'Failed to create or update secret "{path}" from mount point "{self.mount_point}"'
            raise UpdateError(message) from e

    def _retrieve_secret_from_vault(self, path: str, field: str) -> str:
        try:
            response = self.client.secrets.kv.v2.read_secret(path, mount_point=self.mount_point)
        except hvac.exceptions.InvalidPath as e:
            if not self._is_mount_point_available():
                message = f'Mount point "{self.mount_point}" is most likely not available'
                raise SourceError(message) from e

            message = f'Failed to retrieve secret "{path}" from mount point "{self.mount_point}"'
            raise RetrieveError(message) from e
        except hvac.exceptions.VaultError as e:
            message = f'Failed to connect to vault during retrieval of "{path}" from mount point "{self.mount_point}"'
            raise SourceError(message) from e

        try:
            value = response["data"]["data"][field]
        except KeyError as e:
            message = (
                f'Storage format was unexpected for "{path}" '
                f'from mount point "{self.mount_point}": failed to get {field}'
            )
            raise RetrieveError(message) from e

        if not isinstance(value, str):
            value_type = type(value)
            message = f"Secret value is not a string ({value_type})"
            raise RetrieveError(message)

        return value

    def _is_mount_point_available(self) -> bool:
        if self._mount_point_check_result is not None:
            return self._mount_point_check_result

        try:
            self.client.secrets.kv.v2.read_configuration(mount_point=self.mount_point)
            self._mount_point_check_result = True
        except hvac.exceptions.InvalidPath:
            self._mount_point_check_result = False
        except hvac.exceptions.VaultError as e:
            message = f'Failed to connect to vault during availability check of mount point "{self.mount_point}"'
            raise SourceError(message) from e

        return self._mount_point_check_result


def _build_client(settings: ClientSettings) -> hvac.Client:
    cert = None
    if settings.client_cert_file or settings.client_key_file:
        if not (settings.client_key_file and settings.client_cert_file):
            message = "Vault client initialization error: both client cert and key files must be specified"
            raise ConfigurationError(message)

        cert = (settings.client_cert_file, settings.client_key_file)

    verify = settings.ca_file
    if verify is None and cert:
        verify = False

    try:
        token = settings.token_file.read_text(encoding="utf-8").strip()
    except OSError as e:
        message = f"Failed to retrieve token from {settings.token_file}"
        raise ConfigurationError(message) from e

    return hvac.Client(
        url=settings.url,
        token=token,
        namespace=settings.namespace,
        cert=cert,
        verify=verify,
    )
