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

from typing import Literal

from cm.models import Component, Host
from rest_framework.exceptions import NotFound


def check_hostcomponents_objects_exist(hostcomponent_map: list[dict[Literal["host_id", "component_id"], int]]):
    host_ids = {hc["host_id"] for hc in hostcomponent_map}
    component_ids = {hc["component_id"] for hc in hostcomponent_map}

    host_queryset_ids = Host.objects.filter(id__in=host_ids).values_list("pk", flat=True)
    component_queryset_ids = Component.objects.filter(id__in=component_ids).values_list("pk", flat=True)

    if len(diff := host_ids - set(host_queryset_ids)) != 0:
        missing_ids = ", ".join(str(h_id) for h_id in diff)
        raise NotFound(f"Hosts with ids {missing_ids} do not exist")

    if len(diff := component_ids - set(component_queryset_ids)) != 0:
        missing_ids = ", ".join(str(h_id) for h_id in diff)
        raise NotFound(f"Components with ids {missing_ids} do not exist")
