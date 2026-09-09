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
import dishka

from integrations.celery.settings import CelerySettings


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
