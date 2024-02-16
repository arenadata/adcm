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

from functools import lru_cache
from typing import NamedTuple

from core.rbac.types import PasswordRequirements

from cm.models import ADCM, ConfigLog


class ConfigAttrPair(NamedTuple):
    config: dict
    attr: dict


def get_adcm_config_id() -> int:
    return ADCM.objects.values_list("config__current", flat=True).get()


@lru_cache(maxsize=2)
def adcm_config(config_id: int) -> ConfigAttrPair:
    return ConfigAttrPair(**ConfigLog.objects.values("config", "attr").get(id=config_id))


def retrieve_password_requirements() -> PasswordRequirements:
    auth_policy = adcm_config(get_adcm_config_id()).config["auth_policy"]
    return PasswordRequirements(
        min_length=auth_policy["min_password_length"], max_length=auth_policy["max_password_length"]
    )
