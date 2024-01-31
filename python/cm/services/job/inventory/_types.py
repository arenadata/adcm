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

from typing import TypeAlias

from core.types import ComponentID, HostID, ObjectID
from pydantic import BaseModel, Extra, Field

from cm.models import Cluster, ClusterObject, Host, HostProvider, ServiceComponent

HostGroupName: TypeAlias = str
InventoryORMObject: TypeAlias = Cluster | ClusterObject | ServiceComponent | Host | HostProvider

# Inventory/Vars models


class _MultiStateConversionModel(BaseModel):
    def __init__(self, **kwargs):
        input_multi_state = kwargs.pop("multi_state", {})
        multi_state = list(input_multi_state.keys()) if isinstance(input_multi_state, dict) else input_multi_state
        super().__init__(**kwargs, multi_state=multi_state)


class _BeforeUpgradeInventoryNode(BaseModel):
    state: str | None
    config: dict | None = None

    def dict(self, **_) -> dict:
        # can't rely on `exclude_default` here, because it removes the whole `_BeforeUpgradeInventoryNode`
        # when `state` is `None`
        original = super().dict()

        if self.config is None:
            original.pop("config", None)

        return original


class _GenericInventoryNode(_MultiStateConversionModel):
    id: ObjectID
    state: str
    multi_state: list[str]

    before_upgrade: _BeforeUpgradeInventoryNode
    config: dict


class _ClusterNode(_GenericInventoryNode):
    name: str
    version: str
    edition: str

    # todo define type correctly
    imports: dict | list | None = None


class _ServiceNode(_GenericInventoryNode):
    display_name: str
    version: str

    maintenance_mode: bool

    class Config:
        # components are right in the root
        extra = Extra.allow


class _ComponentNode(_GenericInventoryNode):
    id: ComponentID = Field(alias="component_id")
    display_name: str

    maintenance_mode: bool

    class Config:
        allow_population_by_field_name = True


class _HostProviderNode(_MultiStateConversionModel):
    id: ObjectID
    host_prototype_id: ObjectID
    name: str
    state: str
    multi_state: list[str]

    before_upgrade: _BeforeUpgradeInventoryNode
    config: dict


class _HostNode(_MultiStateConversionModel):
    id: HostID = Field(alias="adcm_hostid")
    state: str
    multi_state: list[str]

    cluster: _ClusterNode | None = None
    services: dict[str, _ServiceNode] | None = None

    class Config:
        # config fields are right in the root
        extra = Extra.allow
        allow_population_by_field_name = True


class ClusterVars(BaseModel):
    cluster: _ClusterNode
    services: dict[str, _ServiceNode]
