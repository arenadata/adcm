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

from abc import abstractmethod
from dataclasses import dataclass
from typing import NewType

from core import config
from core.scenarios.config import ConfigScenarios
from core.types import BundleID

DefaultURL = NewType("DefaultURL", str)


@dataclass(slots=True)
class InitializeADCM:
    default_adcm_url: DefaultURL | None

    config_service: config.ConfigService

    @abstractmethod
    def do(self, bundle_id: BundleID):
        ...


@dataclass(slots=True)
class UpgradeADCM:
    config_service: config.ConfigService
    config_scenarios: ConfigScenarios

    @abstractmethod
    def do(self, bundle_id: BundleID):
        ...
