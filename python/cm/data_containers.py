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

from typing import Any, Optional

from pydantic import BaseModel  # pylint: disable=no-name-in-module


class DBModel(BaseModel):
    id: int

    class Config:
        orm_mode = True


class Empty(BaseModel):
    class Config:
        extra = "forbid"


class RequiresData(BaseModel):
    service: str
    component: Optional[str]


class BoundToData(BaseModel):
    service: str
    component: str


class PrototypeData(DBModel):
    name: str
    display_name: str
    type: str
    version: str
    parent_id: int | None
    requires: list[RequiresData]
    bound_to: BoundToData | Empty
    constraint: list[Any]

    @property
    def reference(self) -> str:
        return f'{self.type} "{self.name}" {self.version}'


class ClusterData(DBModel):
    name: str
    prototype_id: int


class ServiceData(DBModel):
    cluster_id: int
    prototype_id: int


class ComponentData(DBModel):
    service_id: int
    cluster_id: int
    prototype_id: int


class HostData(DBModel):
    fqdn: str
    cluster_id: int
    prototype_id: int
    provider_id: int
    maintenance_mode: str


class HostComponentData(DBModel):
    host_id: int
    component_id: int
    service_id: int
