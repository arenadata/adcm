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

from tests.library.api.core import Node, RequestResult


class HostNode(Node):
    def change_maintenance_mode(self, host_id: int, value: Literal["ON", "OFF"]) -> RequestResult:
        return self._requester.post("host", str(host_id), "maintenance-mode", json={"maintenance_mode": value})


class ServiceNode(Node):
    def change_maintenance_mode(self, service_id: int, value: Literal["ON", "OFF"]) -> RequestResult:
        return self._requester.post("service", str(service_id), "maintenance-mode", json={"maintenance_mode": value})


class ComponentNode(Node):
    def change_maintenance_mode(self, component_id: int, value: Literal["ON", "OFF"]) -> RequestResult:
        return self._requester.post(
            "component", str(component_id), "maintenance-mode", json={"maintenance_mode": value}
        )