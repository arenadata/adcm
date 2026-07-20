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

"""
Keep here providers that aren't Django-dependant, so they can be used during startup (django init phase)
"""

from pathlib import Path
import os

from core import secrets
from core.ext_utils.pydantic import represent_missing_and_others_errors_without_description
from core.files.directories import ADCMBundleDir, BundlesDir
from core.files.secrets_provider import FSSecretsBackend
from core.settings import Directories
from core.types import CurrentADCMVersion
from dishka import Provider, Scope, provide
from integrations import consul, vault
from integrations.consul import ConsulBackend
from pydantic_settings import BaseSettings, SettingsConfigDict
import pydantic

from application.constants import SECRETS_FILENAME
from application.types import ADCMMaintenanceMode, SecretsSource


# don't know where to put it yet, so keeping close to usage point
class VaultSettings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="_", env_nested_max_split=1)

    vault: vault.ClientSettings


class ConsulSettings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="_", env_nested_max_split=1)

    consul: consul.ClientSettings


class VaultSecretsInitError(Exception):
    ...


class ConsulSettingsInitError(Exception):
    ...


class EnvironmentProvider(Provider):
    scope = Scope.APP

    @provide
    def adcm_maintenance_mode(self) -> ADCMMaintenanceMode:
        env_var_value = os.environ.get("MAINTENANCE_MODE", "0")
        match env_var_value.lower():
            case "0" | "false" | "no":
                return ADCMMaintenanceMode.DISABLED
            case "1" | "true" | "yes":
                return ADCMMaintenanceMode.ENABLED
            case _:
                message = f'Unknown value of maintenance mode: "{env_var_value}"'
                raise RuntimeError(message)

    @provide
    def directories(self) -> Directories:
        base_dir = Path(os.getenv("ADCM_BASE_DIR", Path(__file__).absolute().parent.parent.parent.parent.parent))
        stack_dir = Path(os.getenv("ADCM_STACK_DIR", base_dir))

        base_data_dir = base_dir / "data"
        # feels wrong to have both base dir and stack dir to have "data",
        # yet it's out there for a long time
        stack_data_dir = stack_dir / "data"

        return Directories(
            base=base_dir,
            stack=stack_dir,
            files=stack_data_dir / "file",
            bundles=stack_data_dir / "bundle",
            downloads=stack_data_dir / "download",
            secrets=base_data_dir / "var",
            code=base_dir / "python",
            data=base_data_dir,
            run=base_data_dir / "run",
            logs=base_data_dir / "log",
            temp=base_data_dir / "tmp",
        )

    @provide
    def secrets_source(self) -> SecretsSource:
        env_var_name = "SECRET_BACKEND"

        secret_backend_env_value = os.environ.get(env_var_name)

        match secret_backend_env_value:
            case "FileSystemBackend" | None:
                return SecretsSource.FILE_SYSTEM

            case "VaultBackend":
                return SecretsSource.VAULT

            case _:
                message = f"Unexpected secrets backend: {env_var_name}={secret_backend_env_value}"
                raise secrets.SecretBaseError(message)

    @provide
    def vault_settings(self) -> vault.ClientSettings:
        return parse_vault_settings_from_env().vault

    @provide
    def consul_settings(self) -> consul.ClientSettings | None:
        return parse_consul_settings_from_env()

    @provide
    def secrets_backend(self, source: SecretsSource, directories: Directories) -> secrets.SecretsBackend:
        match source:
            case SecretsSource.FILE_SYSTEM:
                return FSSecretsBackend(path=directories.secrets / SECRETS_FILENAME)

            case SecretsSource.VAULT:
                vault_settings = parse_vault_settings_from_env()
                return vault.VaultSecretsBackend.from_settings(vault_settings.vault)

    @provide
    def consul_backend(self, settings: consul.ClientSettings | None) -> ConsulBackend | None:
        """Return a Consul backend if configured, otherwise None."""
        if settings is None:
            return None
        return ConsulBackend(settings)

    @provide
    def ansible_vault(self, backend: secrets.SecretsBackend) -> secrets.AnsibleVault:
        secret_value = backend.read(secrets.Secret.ANSIBLE_VAULT)
        return secrets.AnsibleVault(secret_value)

    @provide
    def status_checker_sst(self, backend: secrets.SecretsBackend) -> secrets.StatusCheckerStatusServiceToken:
        secret_value = backend.read(secrets.Secret.STATUS_CHECKER_STATUS_SERVICE_TOKEN)
        return secrets.StatusCheckerStatusServiceToken(secret_value)

    @provide
    def status_service_adcm_token(self, backend: secrets.SecretsBackend) -> secrets.StatusServiceADCMToken:
        secret_value = backend.read(secrets.Secret.STATUS_SERVICE_ADCM_TOKEN)
        return secrets.StatusServiceADCMToken(secret_value)

    @provide
    def django_secret_key(self, backend: secrets.SecretsBackend) -> secrets.DjangoSecretKey:
        secret_value = backend.read(secrets.Secret.DJANGO_SECRET)
        return secrets.DjangoSecretKey(secret_value)

    @provide
    def adcm_version(self) -> CurrentADCMVersion:
        return CurrentADCMVersion(os.getenv("ADCM_VERSION", "2.0.0"))

    @provide
    def adcm_bundle_dir(self, directories: Directories) -> ADCMBundleDir:
        return ADCMBundleDir(directories.base / "conf" / "adcm")

    @provide
    def bundles_root_dir(self, directories: Directories) -> BundlesDir:
        return BundlesDir(directories.bundles)


def parse_vault_settings_from_env():
    try:
        # ignored, because pyright doesn't know about pydantic settings logic
        return VaultSettings()  # pyright: ignore[reportCallIssue]
    except pydantic.ValidationError as e:
        message = represent_missing_and_others_errors_without_description(
            errors=e.errors(),
            prefix="Failed to retrieve vault settings from environment.\nSummary:\n",
        )
        raise VaultSecretsInitError(message) from None


def parse_consul_settings_from_env() -> consul.ClientSettings | None:
    # Consul integration is opt-in: without CONSUL_URL there is nothing to configure.
    if not os.getenv("CONSUL_URL"):
        return None

    try:
        # ignored, because pyright doesn't know about pydantic settings logic
        return ConsulSettings().consul  # pyright: ignore[reportCallIssue]
    except pydantic.ValidationError as e:
        message = represent_missing_and_others_errors_without_description(
            errors=e.errors(),
            prefix="Failed to retrieve consul settings from environment.\nSummary:\n",
        )
        raise ConsulSettingsInitError(message) from None
