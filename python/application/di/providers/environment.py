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

from typing import Annotated, TypeVar
import os

from adcm.feature_flags import use_new_job_scheduler
from core import secrets
from core.ext_utils.pydantic import represent_missing_and_others_errors_without_description
from core.files.directories import ADCMBundleDir, BundlesDir
from core.files.secrets_provider import FSSecretsBackend
from core.scenarios.adcm import DefaultURL
from core.settings import Directories
from core.types import CurrentADCMVersion
from dishka import Provider, Scope, provide
from django.conf import settings as django_settings
from integrations import consul, vault
from integrations.celery.pg.transport import make_broker_url
from integrations.celery.settings import CelerySettings
from integrations.consul import ConsulBackend
from jobs.scheduler.settings import SchedulerSettings
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL
import pydantic

from application.constants import SECRETS_FILENAME
from application.environment import directories_from_env
from application.types import ADCMMaintenanceMode, SecretsSource, TaskRunnerMode

_EnvSettingsT = TypeVar("_EnvSettingsT", bound=BaseSettings)


# don't know where to put it yet, so keeping close to usage point
class VaultSettings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="_", env_nested_max_split=1)

    vault: vault.ClientSettings


class ConsulSettings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="_", env_nested_max_split=1)

    consul: consul.ClientSettings


class EnvDBSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="db_")

    user: str
    # prefix looks to be ignored when alias is used
    password: Annotated[SecretStr, Field(alias="db_pass")]
    name: str
    host: str
    port: str

    options: Annotated[dict, Field(default_factory=dict)]


class VaultSecretsInitError(Exception):
    ...


class ConsulSettingsInitError(Exception):
    ...


class WorkerSettingsInitError(Exception):
    ...


class EnvironmentProvider(Provider):
    scope = Scope.APP

    @provide
    def default_adcm_url(self) -> DefaultURL | None:
        adcm_url = os.getenv("DEFAULT_ADCM_URL")
        if adcm_url:
            return DefaultURL(adcm_url)

        return None

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
        return directories_from_env()

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
    def task_runner_mode(self) -> TaskRunnerMode:
        if use_new_job_scheduler():
            return TaskRunnerMode.SCHEDULLER

        return TaskRunnerMode.INSTANT

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
    def celery_settings(
        self,
        consul_backend: ConsulBackend | None,
        default_adcm_url: DefaultURL | None,
    ) -> CelerySettings:
        db = parse_settings_from_env(EnvDBSettings, "database")
        # Build via URL.create so credentials/host/db and options are properly
        # percent-encoded — a password containing @ : / ? # would otherwise
        # break URL parsing and authentication.
        connection_str = URL.create(
            "postgresql+psycopg",
            username=db.user,
            password=db.password.get_secret_value(),
            host=db.host,
            port=int(db.port),
            database=db.name,
            query={key: str(value) for key, value in db.options.items()},
        ).render_as_string(hide_password=False)

        return CelerySettings(
            db_url=connection_str,
            # PostgreSQL LISTEN/NOTIFY broker; control commands ride native
            # Celery pidbox over its fanout (see integrations.celery.pg).
            broker_url=make_broker_url(connection_str),
            result_backend=f"db+{connection_str}",
            consul=consul_backend,
            default_adcm_url=str(default_adcm_url) if default_adcm_url else None,
            status_service_base_path=django_settings.STATUS_SERVICE_BASE_PATH,
        )

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

    @provide
    def scheduler_settings(self) -> SchedulerSettings:
        return parse_settings_from_env(SchedulerSettings, "scheduler")


def parse_settings_from_env(settings_cls: type[_EnvSettingsT], name: str) -> _EnvSettingsT:
    try:
        return settings_cls()
    except pydantic.ValidationError as e:
        message = represent_missing_and_others_errors_without_description(
            errors=e.errors(),
            prefix=f"Failed to retrieve {name} settings from environment.\nSummary:\n",
        )
        raise WorkerSettingsInitError(message) from None


def parse_vault_settings_from_env() -> VaultSettings:
    return parse_settings_from_env(settings_cls=VaultSettings, name="vault")


def parse_consul_settings_from_env() -> consul.ClientSettings | None:
    # Consul integration is opt-in: without CONSUL_URL there is nothing to configure.
    if not os.getenv("CONSUL_URL"):
        return None

    return parse_settings_from_env(settings_cls=ConsulSettings, name="consul").consul
