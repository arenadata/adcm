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

from core.types import ClusterID, ComponentID, HostID, ObjectID, PrototypeID, ProviderID, ServiceID
from pydantic import BaseModel, ConfigDict


class DBModel(BaseModel):
    id: ObjectID
    model_config = ConfigDict(from_attributes=True)


class Empty(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequiresData(BaseModel):
    service: str
    component: str | None = None


class BoundToData(BaseModel):
    service: str
    component: str


class PrototypeData(DBModel):
    name: str
    display_name: str
    type: str
    version: str
    parent_id: PrototypeID | None = None
    requires: list[RequiresData]
    bound_to: BoundToData | Empty
    constraint: list[Any]

    @property
    def reference(self) -> str:
        return f'{self.type} "{self.name}" {self.version}'


class ClusterData(DBModel):
    name: str
    prototype_id: PrototypeID


class ServiceData(DBModel):
    cluster_id: ClusterID
    prototype_id: PrototypeID


class ComponentData(DBModel):
    service_id: ServiceID
    cluster_id: ClusterID
    prototype_id: PrototypeID


class HostData(DBModel):
    fqdn: str
    cluster_id: ClusterID
    prototype_id: PrototypeID
    provider_id: ProviderID
    maintenance_mode: str


class HostComponentData(DBModel):
    host_id: HostID
    component_id: ComponentID
    service_id: ServiceID
