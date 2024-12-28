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

from core.types import ADCMCoreType, ComponentID, HostID, ObjectID
from pydantic import BaseModel, ConfigDict, Field

HostGroupName: TypeAlias = str

ObjectsInInventoryMap: TypeAlias = dict[ADCMCoreType, set[ObjectID]]

# Inventory/Vars models


class _MultiStateConversionModel(BaseModel):
    def __init__(self, **kwargs):
        input_multi_state = kwargs.pop("multi_state", {})
        multi_state = list(input_multi_state.keys()) if isinstance(input_multi_state, dict) else input_multi_state
        super().__init__(**kwargs, multi_state=multi_state)


class _BeforeUpgradeInventoryNode(BaseModel):
    state: str | None
    config: dict | None = None

    def model_dump(self, **_) -> dict:
        # can't rely on `exclude_default` here, because it removes the whole `_BeforeUpgradeInventoryNode`
        # when `state` is `None`
        original = super().model_dump()

        if self.config is None:
            original.pop("config", None)

        return original


class _GenericInventoryNode(_MultiStateConversionModel):
    id: ObjectID
    state: str
    multi_state: list[str]

    before_upgrade: _BeforeUpgradeInventoryNode
    config: dict


class ClusterNode(_GenericInventoryNode):
    name: str
    version: str
    edition: str

    imports: dict | list | None = None


class ServiceNode(_GenericInventoryNode):
    display_name: str
    version: str

    maintenance_mode: bool
    model_config = ConfigDict(extra="allow")


class ComponentNode(_GenericInventoryNode):
    id: ComponentID = Field(alias="component_id")
    display_name: str

    maintenance_mode: bool
    model_config = ConfigDict(populate_by_name=True)


class ProviderNode(_MultiStateConversionModel):
    id: ObjectID
    host_prototype_id: ObjectID
    name: str
    state: str
    multi_state: list[str]

    before_upgrade: _BeforeUpgradeInventoryNode
    config: dict


class HostNode(_MultiStateConversionModel):
    id: HostID = Field(alias="adcm_hostid")
    state: str
    multi_state: list[str]

    cluster: ClusterNode | None = None
    services: dict[str, ServiceNode] | None = None
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ClusterVars(BaseModel):
    cluster: ClusterNode
    services: dict[str, ServiceNode]
