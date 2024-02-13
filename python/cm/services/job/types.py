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
from enum import Enum
from typing import Any, Literal, Optional, TypeAlias, Union

from core.types import ClusterID, ComponentID, HostID, HostProviderID, ObjectID, PrototypeID, ServiceID
from pydantic import BaseModel, Field, Json

Selector: TypeAlias = dict[str, dict[Literal["id", "name"], int | str]]


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
    provider_id: HostProviderID


class HostProviderActionType(ObjectWithHostGroup):
    action_proto_type: Literal["provider"]
    provider_id: HostProviderID


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
    config: Optional[Json]
    params: Optional[Json]
    cluster_id: Optional[ClusterID]
    action_type_specification: (
        ClusterActionType
        | ServiceActionType
        | ComponentActionType
        | HostProviderActionType
        | HostActionType
        | ADCMActionType
    ) = Field(..., discriminator="action_proto_type")

    def dict(
        self,
        *,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,  # noqa: F821
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,  # noqa: F821
        by_alias: bool = False,
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> dict[str, Any]:
        result: dict[str, Any] = super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

        for key, value in result.pop("action_type_specification").items():
            # Merge `action_type_specification` fields into root dict,
            # exclude discriminator field.
            # See https://docs.pydantic.dev/1.10/usage/types/#discriminated-unions-aka-tagged-unions
            if key == "action_proto_type":
                continue

            result[key] = value

        return result


class JobConfig(BaseModel):
    adcm: dict[Literal["config"], dict[str, Any]]
    context: dict[str, Any]
    env: JobEnv
    job: JobData


class HcAclAction(Enum):
    ADD = "add"
    REMOVE = "remove"
