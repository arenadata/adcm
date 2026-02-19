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
from core.settings import Directories
from core.types import CurrentADCMVersion
from dishka import Provider, Scope, provide


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

            case _:
                message = f"Unexpected secrets backend: {env_var_name}={secret_backend_env_value}"
                raise secrets.SecretsError(message)

    @provide
    def adcm_secrets(self, source: secrets.SecretsSource, directories: Directories) -> secrets.ADCMSecrets:
        match source:
            case secrets.SecretsSource.FILE_SYSTEM:
                provider = secrets.FSSecretsProvider(path=directories.secrets / secrets.SECRETS_FILENAME)
            case secrets.SecretsSource.OPEN_BAO:
                raise NotImplementedError()

        return provider.get()

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
