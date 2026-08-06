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

from functools import wraps
import logging

from celery import Celery
from core.adcm import ADCMRepoI
from dishka.integrations.base import wrap_injection
import dishka

from jobs.worker.celery.settings import CelerySettings

logger = logging.getLogger("adcm.worker")


class ADCMCelery(Celery):
    def __init__(
        self,
        *args,
        adcm_di_container: dishka.Container,
        adcm_settings: CelerySettings,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        # CelerySettings is the config carrier: every field becomes an ``app.conf``
        # key, both native Celery settings (broker_url, ...) and ADCM ones read by
        # the worker startup hooks (consul, default_adcm_url, ...).
        self.config_from_object(adcm_settings)

        self.di_container = adcm_di_container


# kept DI function in here, because they are deeply dependant on `ADCMCelery` structure


def read_adcm_uuid(repo: ADCMRepoI) -> str | None:
    """Read the ADCM uuid; best-effort (``None`` on failure)."""
    try:
        return repo.get_uuid()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to read ADCM uuid")
        return None


def container_from_argument(*args):
    return args[1]["adcm_di_container"]


def di_task(func):
    func_with_injection = wrap_injection(func=func, is_async=False, container_getter=container_from_argument)

    @wraps(func)
    def enter_request_scope(*args, **kwargs):
        with args[0].app.di_container(scope=dishka.Scope.REQUEST) as container:
            return func_with_injection(*args, adcm_di_container=container, **kwargs)

    return enter_request_scope
