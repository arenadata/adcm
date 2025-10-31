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


from adcm.feature_flags import use_new_config_processing
from infra.services import get_config_service

from cm import converters
from cm.models import (
    ADCM,
    MainObject,
    ObjectConfig,
    Prototype,
)


# Use `initiate_config_if_required` after update, kept `init_object_config` for simplicity.
# Now it's still used in some places like ADCM init and upgrade for "routing" based on new config processing.
#
# signature refers to original `init_object_config`
def init_object_config(proto: Prototype, obj: MainObject) -> ObjectConfig | None:
    if use_new_config_processing():
        if not isinstance(obj, (ADCM, MainObject)):
            raise TypeError(f"Unexpected type {type(obj)}")

        service = get_config_service()
        descriptor = converters.orm_object_to_core_descriptor(obj)
        config_id = service.create_initial_configuration_if_required(owner=descriptor)

        if config_id:
            obj.refresh_from_db(fields=["config"])
            return obj.config

        return None

    from cm.adcm_config.config import init_object_config as init_object_config_old

    return init_object_config_old(proto, obj)
