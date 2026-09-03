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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TypeAlias, Union, overload

from core.action import ActionInfo, wizard
from core.types import (
    ActionProcessID,
    ActionTargetDescriptor,
    CoreObjectDescriptor,
    ExtraActionTargetType,
)

if TYPE_CHECKING:
    from cm.impl.bundle.context import ActionArgs
    from cm.models import Action, ActionHostGroup, Cluster, Component, Host, Service


ProcessOwner: TypeAlias = Union["Cluster", "Service", "Component"]
ProcessTarget: TypeAlias = Union["Cluster", "Service", "Component", "Host", "ActionHostGroup"]
ClusterRelativeObjectORM: TypeAlias = Union["Cluster", "Service", "Component", "Host"]

ActionProcess = wizard.ActionProcessModel
Step = wizard.ActionProcessStepModel
MappingInputDTO = wizard.MappingInputDTO
MappingStepInput = wizard.MappingStepInput
ProcessState = wizard.ProcessState
ProcessStepState = wizard.ProcessStepState
ProcessUpdateDTO = wizard.ProcessUpdateDTO
StepInputDTO = wizard.StepInputDTO
StepUpdateDTO = wizard.StepUpdateDTO

__all__ = [
    "ActionProcess",
    "MappingInputDTO",
    "MappingStepInput",
    "ProcessContext",
    "ProcessOwner",
    "ProcessState",
    "ProcessStepState",
    "ProcessTarget",
    "ProcessUpdateDTO",
    "Step",
    "StepInputDTO",
    "StepUpdateDTO",
]


@dataclass(frozen=True, slots=True)
class ProcessContext:
    action: ActionInfo
    action_orm: "Action"
    target: ActionTargetDescriptor
    target_orm: ProcessTarget
    owner: CoreObjectDescriptor
    owner_orm: ProcessOwner

    def build_action_args(self, process_id: ActionProcessID | None) -> "ActionArgs":
        from cm.impl.bundle.context import ActionArgs

        return ActionArgs(
            action=self.action_orm,
            owner_object=self.owner_orm,
            target_object=self.target_orm,
            wizard_process_id=process_id,
        )

    @overload
    def cluster_relative_object(self, as_descriptor: Literal[True]) -> CoreObjectDescriptor:
        ...

    @overload
    def cluster_relative_object(self, as_descriptor: Literal[False] = False) -> ClusterRelativeObjectORM:
        ...

    def cluster_relative_object(self, as_descriptor: bool = False) -> ClusterRelativeObjectORM | CoreObjectDescriptor:
        if self.target.type == ExtraActionTargetType.ACTION_HOST_GROUP:
            return self.owner if as_descriptor else self.owner_orm
        else:
            return CoreObjectDescriptor(id=self.target.id, type=self.target.type) if as_descriptor else self.target_orm
