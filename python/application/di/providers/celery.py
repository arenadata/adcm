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

from celery import Celery
from core.adcm import ADCMRepoI
from dishka import Container, Provider, Scope, provide
from integrations.celery.app import ADCMCelery
from integrations.celery.external_status_service_url import ResolveExternalStatusServiceURL
from integrations.celery.settings import CelerySettings


class CeleryProvider(Provider):
    scope = Scope.APP

    @provide
    def resolve_external_status_service_url(
        self, repo: ADCMRepoI, celery_settings: CelerySettings
    ) -> ResolveExternalStatusServiceURL:
        return ResolveExternalStatusServiceURL(
            repo=repo,
            consul_backend=celery_settings.consul,
            default_adcm_url=celery_settings.default_adcm_url,
            status_base_path=celery_settings.status_service_base_path,
        )

    @provide
    def celery(self, container: Container, celery_settings: CelerySettings) -> Celery:
        app = ADCMCelery(
            adcm_di_container=container,
            adcm_settings=celery_settings,
        )

        # Registers tasks (shared_task) defined in integrations.celery.tasks against this app.
        app.autodiscover_tasks(packages=["integrations.celery"])

        # Control commands (@control_command) self-register into celery's worker control
        # registry on import; autodiscover_tasks only imports the `tasks` submodule, so
        # commands need an explicit import to be registered too. Safe to do unconditionally
        # (here, not just in the worker entrypoint): registering a command has no side
        # effect beyond adding a lookup-table entry, unlike the worker-only signals.
        import integrations.celery.commands  # noqa: F401

        return app
