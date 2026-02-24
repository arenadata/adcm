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
from core.files.directories import ADCMBundleDir, BundlesDir
from core.secrets.impl.provider_fs import FSSecretsProvider
from core.settings import Directories
from core.types import CurrentADCMVersion
from dishka import Provider, Scope, provide
from integrations import vault
from pydantic_settings import BaseSettings, SettingsConfigDict
import pydantic


# don't know where to put it yet, so keeping close to usage point
class VaultSettings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="_", env_nested_max_split=1)

    vault: vault.ClientSettings


class EnvironmentProvider(Provider):
    scope = Scope.APP

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
            temp=base_data_dir / "temp",
        )

    @provide
    def secrets_source(self) -> secrets.SecretsSource:
        env_var_name = "SECRET_BACKEND"

        secret_backend_env_value = os.environ.get(env_var_name)

        match secret_backend_env_value:
            case "FileSystemBackend" | None:
                return secrets.SecretsSource.FILE_SYSTEM

            case "VaultBackend":
                return secrets.SecretsSource.VAULT

            case _:
                message = f"Unexpected secrets backend: {env_var_name}={secret_backend_env_value}"
                raise secrets.SecretsError(message)

    @provide
    def adcm_secrets(self, source: secrets.SecretsSource, directories: Directories) -> secrets.ADCMSecrets:
        match source:
            case secrets.SecretsSource.FILE_SYSTEM:
                provider = FSSecretsProvider(path=directories.secrets / secrets.SECRETS_FILENAME)
                return provider.get()

            case secrets.SecretsSource.VAULT:
                try:
                    # ignored, because pyright doesn't know about pydantic settings logic
                    vault_settings = VaultSettings()  # pyright: ignore[reportCallIssue]
                except pydantic.ValidationError as e:
                    message = (
                        "Failed to retrieve vault settings from environment, "
                        "most likely one or more required values are missing. "
                        "See error traceback for more info."
                    )
                    raise RuntimeError(message) from e

                provider = vault.VaultSecretsProvider.from_settings(vault_settings.vault)

                try:
                    return provider.get()
                except secrets.SecretsError as e:
                    message = (
                        "Failed to retrieve all required secrets from vault. "
                        "For details see error traceback. "
                        "If settings are correct, but secrets are absent, "
                        "you need to either add them to your vault storage or migrate from filesystem."
                    )
                    raise RuntimeError(message) from e

    @provide
    def ansible_vault(self, retrieved_secrets: secrets.ADCMSecrets) -> secrets.AnsibleVault:
        return secrets.AnsibleVault(retrieved_secrets.ansible.ansible_vault)

    @provide
    def adcm_version(self) -> CurrentADCMVersion:
        return CurrentADCMVersion(os.getenv("ADCM_VERSION", "2.0.0"))

    @provide
    def adcm_bundle_dir(self, directories: Directories) -> ADCMBundleDir:
        return ADCMBundleDir(directories.base / "conf" / "adcm")

    @provide
    def bundles_root_dir(self, directories: Directories) -> BundlesDir:
        return BundlesDir(directories.bundles)
