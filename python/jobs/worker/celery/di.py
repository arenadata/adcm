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

from typing import TypeVar

from celery import Celery
from core.ext_utils.pydantic import represent_missing_and_others_errors_without_description
from core.scenarios.adcm import DefaultURL
from dishka import Container, Provider, Scope, provide
from django.conf import settings
from integrations.consul import ConsulBackend
from pydantic_settings import BaseSettings
from sqlalchemy import URL
import pydantic

from jobs.worker.celery import forksafe, status_service
from jobs.worker.celery.consul_registration import ConsulRegistrationStep
from jobs.worker.celery.custom import ADCMCelery
from jobs.worker.celery.pg.transport import make_broker_url
from jobs.worker.celery.settings import CelerySettings, EnvDBSettings

_EnvSettingsT = TypeVar("_EnvSettingsT", bound=BaseSettings)


class WorkerSettingsInitError(Exception):
    ...


def parse_settings_from_env(settings_cls: type[_EnvSettingsT], name: str) -> _EnvSettingsT:
    try:
        return settings_cls()
    except pydantic.ValidationError as e:
        message = represent_missing_and_others_errors_without_description(
            errors=e.errors(),
            prefix=f"Failed to retrieve {name} settings from environment.\nSummary:\n",
        )
        raise WorkerSettingsInitError(message) from None


class CeleryProvider(Provider):
    scope = Scope.APP

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
            # Celery pidbox over its fanout (see jobs.worker.celery.pg).
            broker_url=make_broker_url(connection_str),
            result_backend=f"db+{connection_str}",
            consul=consul_backend,
            default_adcm_url=str(default_adcm_url) if default_adcm_url else None,
            status_service_base_path=settings.STATUS_SERVICE_BASE_PATH,
        )

    @provide
    def celery(self, container: Container, celery_settings: CelerySettings) -> Celery:
        forksafe.install()
        status_service.install()

        app = ADCMCelery(
            adcm_di_container=container,
            adcm_settings=celery_settings,
        )

        app.autodiscover_tasks(packages=["jobs.worker"])

        if celery_settings.consul is not None:
            app.steps["worker"].add(ConsulRegistrationStep)  # pyright: ignore[reportOptionalSubscript]

        return app
