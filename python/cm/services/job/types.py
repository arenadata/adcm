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

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, TypeAlias, TypedDict

from core.types import ClusterID, ComponentID, HostID, ObjectID, PrototypeID, ProviderID, ServiceID, ShortObjectInfo
from pydantic import BaseModel, Field, Json

Selector: TypeAlias = dict[str, dict[Literal["id", "name"], int | str]]
ComponentComposedKey: TypeAlias = str
ShortHostInfo: TypeAlias = ShortObjectInfo


class ObjectWithHostGroup(BaseModel):
    hostgroup: str


class ServiceActionType(ObjectWithHostGroup):
    action_proto_type: Literal["service"]
    service_id: ServiceID
    service_type_id: PrototypeID


class ComponentActionType(ObjectWithHostGroup):
    action_proto_type: Literal["component"]
    service_id: ServiceID
    component_id: ComponentID
    component_type_id: PrototypeID


class ClusterActionType(ObjectWithHostGroup):
    action_proto_type: Literal["cluster"]


class HostActionType(ObjectWithHostGroup):
    action_proto_type: Literal["host"]
    hostname: str
    host_id: HostID
    host_type_id: PrototypeID
    provider_id: ProviderID


class ProviderActionType(ObjectWithHostGroup):
    action_proto_type: Literal["provider"]
    provider_id: ProviderID


class ADCMActionType(ObjectWithHostGroup):
    action_proto_type: Literal["adcm"]


class JobEnv(BaseModel):
    run_dir: str
    log_dir: str
    tmp_dir: str
    stack_dir: str
    status_api_token: str


class JobData(BaseModel):
    id: ObjectID
    action: str
    job_name: str
    command: str
    script: str
    verbose: bool
    playbook: str
    config: Json | None = None
    params: Json | None = None
    cluster_id: ClusterID | None = None
    action_type_specification: (
        ClusterActionType
        | ServiceActionType
        | ComponentActionType
        | ProviderActionType
        | HostActionType
        | ADCMActionType
    ) = Field(..., discriminator="action_proto_type")


class JobConfig(BaseModel):
    adcm: dict[Literal["config"], dict[str, Any]]
    context: dict[str, Any]
    env: JobEnv
    job: JobData

    def model_dump(self, **kwargs) -> dict[str, Any]:
        result = super().model_dump(**kwargs)

        # legacy of `dict` redefinition for `JobData`:
        # Merge `action_type_specification` fields into root dict,
        # exclude discriminator field.
        # See https://docs.pydantic.dev/1.10/usage/types/#discriminated-unions-aka-tagged-unions
        #
        # Need to rework typing of JobData to remove it
        type_specifics = result["job"].pop("action_type_specification")
        type_specifics.pop("action_proto_type")
        result["job"] |= type_specifics

        return result


class HcAclAction(Enum):
    ADD = "add"
    REMOVE = "remove"


@dataclass(slots=True)
class TaskMappingDelta:
    add: dict[ComponentComposedKey, set[ShortHostInfo]] = field(default_factory=dict)
    remove: dict[ComponentComposedKey, set[ShortHostInfo]] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not (self.add or self.remove)


class ActionHCRule(TypedDict):
    action: Literal["add", "remove"]
    service: str
    component: str
