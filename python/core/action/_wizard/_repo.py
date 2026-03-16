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

from typing import Any, Generator, Protocol
from uuid import UUID

from core.action._wizard._types import ProcessID, ProcessState, Stage, StepWithData
from core.action._wizard._types_purgatory import (
    ActionProcess,
    MappingStepInput,
    ProcessUpdateDTO,
    Step,
    StepInputDTO,
    StepUpdateDTO,
)
from core.types import (
    ActionID,
    ActionProcessID,
    ActionProcessStepID,
    ActionTargetDescriptor,
    BundleID,
    ClusterID,
    CoreObjectDescriptor,
    TaskID,
)


class TaskORM(Protocol):
    id: int
    pk: int


class WizardRepoI(Protocol):
    def get_steps_with_data(self, process_id: ProcessID) -> list[StepWithData]:
        ...

    def create_process(
        self,
        *,
        target: ActionTargetDescriptor,
        owner: CoreObjectDescriptor,
        action_id: ActionID,
        stages: list[Stage],
    ) -> ActionProcess:
        ...

    def create_steps(self, process_id: ActionProcessID, stages: list[Stage]) -> list[Any]:
        ...

    def set_process_status(self, process: ActionProcess, state: ProcessState) -> bool:
        ...

    def retrieve_step(self, process_id: ActionProcessID, step_id: ActionProcessStepID) -> Step:
        ...

    def retrieve_running_step_ids(self, process_id: ActionProcessID) -> set[ActionProcessStepID]:
        ...

    def retrieve_steps(self, process_id: ActionProcessID, **kwargs: Any) -> Generator[Step, None, None]:
        ...

    def retrieve_process(self, process_id: ActionProcessID) -> ActionProcess:
        ...

    def update_step(self, step_id: ActionProcessStepID, data: StepUpdateDTO) -> None:
        ...

    def upsert_step_input(self, step_id: ActionProcessStepID, data: StepInputDTO) -> None:
        ...

    def retrieve_previous_mapping_step_input_with_cumulative_delta(
        self, process_id: ActionProcessID, step_id: ActionProcessStepID
    ) -> MappingStepInput | None:
        ...

    def update_process(self, process_id: ActionProcessID, data: ProcessUpdateDTO) -> None:
        ...

    def update_process_sync_key(self, process_id: ActionProcessID, sync_key: UUID, new_sync_key: UUID) -> bool:
        ...

    # todo candidate for removal, only legacy dependency stays
    def retrieve_task_orm(self, task_id: TaskID) -> TaskORM:
        ...

    def retrieve_next_step_ids(
        self, process_id: ActionProcessID, step_id: ActionProcessStepID
    ) -> tuple[ActionProcessStepID]:
        ...

    def retrieve_step_ids_starting_with(
        self, process_id: ActionProcessID, step_id: ActionProcessStepID
    ) -> tuple[ActionProcessStepID]:
        ...

    def revoke_steps(self, step_ids: set[ActionProcessStepID]) -> None:
        ...

    def retrieve_related_cluster_id_and_cluster_bundle_id(
        self, object_: CoreObjectDescriptor
    ) -> tuple[ClusterID, BundleID]:
        ...
