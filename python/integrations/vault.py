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
from typing import Iterable

from core.secrets import ADCMSecrets, SecretsError, SecretsProvider
from typing_extensions import Self
import pydantic
import hvac.exceptions


@dataclass(slots=True)
class ClientSettings:
    # main

    url: str
    token: str
    mount_point: str

    # SSL

    client_cert_file: str | None = None
    client_key_file: str | None = None
    ca_file: str | None = None

    # optional features

    namespace: str | None = None


class _ADCMSecrets(ADCMSecrets):
    # make validation easier to consume settings in more flexible way
    model_config = pydantic.ConfigDict(extra="ignore")


@dataclass(slots=True)
class VaultSecretsProvider(SecretsProvider):
    client: hvac.Client
    mount_point: str

    @classmethod
    def from_settings(cls, settings: ClientSettings) -> Self:
        client = _build_client(settings)
        return cls(client=client, mount_point=settings.mount_point)

    def get(self) -> ADCMSecrets:
        # for now nodes in Vault are expected to follow secrets file structure,
        # so all fields in secrets are actually node names under "adcm"
        nodes: Iterable[str] = ADCMSecrets.model_fields
        data_from_nodes = {node: self.retrieve_secrets_node(path=f"adcm/{node}") for node in nodes}
        # intentionaly don't capture errors in here, because we make a lot of assumptions of secrets structure, e.g.:
        # 1. vault node/data structures follow ADCMSecrets format
        # 2. ADCMSecrets allow extra values set (so we can blindly read all data from node)
        return _ADCMSecrets.model_validate(data_from_nodes)

    def retrieve_secrets_node(self, path: str) -> dict[str, str]:
        try:
            response = self.client.secrets.kv.v2.read_secret(path, mount_point=self.mount_point)
        except hvac.exceptions.VaultError as e:
            message = f'Failed to retrieve secret "{path}" from mount point "{self.mount_point}"'
            raise SecretsError(message) from e

        return response["data"]["data"]


def _build_client(settings: ClientSettings) -> hvac.Client:
    cert = None
    if settings.client_cert_file or settings.client_key_file:
        if not (settings.client_key_file and settings.client_cert_file):
            message = "Vault client initialization error: both client cert and key files must be specified"
            raise SecretsError(message)

        cert = (settings.client_cert_file, settings.client_key_file)

    verify = settings.ca_file
    if verify is None and cert:
        verify = False

    return hvac.Client(
        url=settings.url,
        namespace=settings.namespace,
        cert=cert,
        verify=verify,
    )
