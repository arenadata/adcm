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

from typing import Annotated, TypeAlias

from pydantic import BaseModel, Field

ComponentName: TypeAlias = str
GroupName: TypeAlias = str
HostName: TypeAlias = str
ListOfHosts = Annotated[list[HostName], Field(default_factory=list)]
ServiceName: TypeAlias = str


class _RawConfig(BaseModel):
    data: dict
    attributes: dict


class _BaseBeforeUpgrade(BaseModel):
    state: str | None = None
    config_id: int | None = None


class _BaseDeletedBeforeUpgrade(BaseModel):
    state: str | None = None
    config: _RawConfig | None = None


class _WithBundleID(BaseModel):
    bundle_id: int


class _ConfigHostGroupWithRawConfig(BaseModel):
    config: _RawConfig | None = None
    hosts: ListOfHosts


class ConfigHostGroupWithIdConfigBeforeUpgrade(BaseModel):
    config_id: int | None = None
    hosts: ListOfHosts


class ActionHostGroupBeforeUpgrade(BaseModel):
    hosts: ListOfHosts


class _WithConfigHostGroupRawConfig(BaseModel):
    config_host_groups: Annotated[dict[GroupName, _ConfigHostGroupWithRawConfig], Field(default_factory=dict)]


class _WithConfigHostGroupIdConfig(BaseModel):
    config_host_groups: Annotated[
        dict[GroupName, ConfigHostGroupWithIdConfigBeforeUpgrade], Field(default_factory=dict)
    ]


class _WithActionHostGroup(BaseModel):
    action_host_groups: Annotated[dict[GroupName, ActionHostGroupBeforeUpgrade], Field(default_factory=dict)]


class ServiceHostComponentMapBeforeUpgrade(BaseModel):
    service: str
    component: str
    host: str


class ServiceBeforeUpgrade(_BaseBeforeUpgrade, _WithConfigHostGroupIdConfig, _WithActionHostGroup):
    ...


class ComponentBeforeUpgrade(_BaseBeforeUpgrade, _WithConfigHostGroupIdConfig, _WithActionHostGroup):
    ...


class DeletedObjectBeforeUpgrade(_BaseDeletedBeforeUpgrade, _WithConfigHostGroupRawConfig, _WithActionHostGroup):
    ...


class ProviderBeforeUpgrade(_WithBundleID, _BaseBeforeUpgrade, _WithConfigHostGroupIdConfig):
    ...


class HostBeforeUpgrade(_BaseBeforeUpgrade):
    ...


class DeletedServiceBeforeUpgrade(DeletedObjectBeforeUpgrade):
    components: Annotated[dict[ComponentName, DeletedObjectBeforeUpgrade], Field(default_factory=dict)]


class ClusterBeforeUpgrade(_WithBundleID, _BaseBeforeUpgrade, _WithConfigHostGroupIdConfig, _WithActionHostGroup):
    hc: Annotated[list[ServiceHostComponentMapBeforeUpgrade], Field(default_factory=list)]
    services: Annotated[list[ServiceName], Field(default_factory=list)]
    deleted_services: Annotated[dict[ServiceName, DeletedServiceBeforeUpgrade], Field(default_factory=dict)]
    service_deleted_components: Annotated[
        dict[ServiceName, dict[ComponentName, DeletedObjectBeforeUpgrade]], Field(default_factory=dict)
    ]


BeforeUpgrade: TypeAlias = (
    ClusterBeforeUpgrade | ServiceBeforeUpgrade | ComponentBeforeUpgrade | ProviderBeforeUpgrade | HostBeforeUpgrade
)
