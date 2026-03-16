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

from typing import Any

from cm.legacy.adcm_config.config import get_option_value
from cm.models import Cluster, Prototype, Service

# Helper functions for ansible plugins


def get_service_by_name(cluster_id, service_name):
    cluster = Cluster.obj.get(id=cluster_id)
    proto = Prototype.obj.get(type="service", name=service_name, bundle=cluster.prototype.bundle)
    return Service.obj.get(cluster=cluster, prototype=proto)


def cast_to_type(field_type: str, value: Any, limits: dict) -> Any:
    match field_type:
        case "float":
            return float(value)
        case "integer":
            return int(value)
        case "option":
            return get_option_value(value=value, limits=limits)
        case _:
            return value
