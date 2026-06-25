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

from core import adcm
from core.scenarios.adcm import ADCMUUID

from cm.models import ADCM


@dataclass(slots=True)
class ADCMRepo(adcm.ADCMRepoI):
    def get_uuid(self) -> ADCMUUID | None:
        # ADCM is a singleton, but the row may be recreated on upgrade: limit to a single value.
        uuid = ADCM.objects.values_list("uuid", flat=True).first()
        if uuid:
            return ADCMUUID(str(uuid))

        return None
