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
from uuid import UUID

from core.action._wizard import operations
from core.action._wizard._errors import ActionProcessOperationError, SyncKeyMismatchError
from core.action._wizard._repo import WizardRepoI
from core.action._wizard._types import ProcessID, ProcessState, Stage, StepID, StepWithData
from core.action._wizard._types_purgatory import (
    ActionProcess,
    HostComponentMapDeltaSets,
    MappingInputDTO,
    ProcessStepState,
    ProcessUpdateDTO,
    StepInputDTO,
    StepUpdateDTO,
)
from core.settings import Directories
from core.types import ActionID, ActionProcessStepID, ActionTargetDescriptor, CoreObjectDescriptor


@dataclass(slots=True)
class WizardService:
    repo: WizardRepoI
    directories: Directories

    def retrieve_steps_and_data_for_process(self, process_id: ProcessID) -> list[StepWithData]:
        return self.repo.get_steps_with_data(process_id=process_id)

    def initiate_process(
        self,
        *,
        target: ActionTargetDescriptor,
        owner: CoreObjectDescriptor,
        action_id: ActionID,
        stages: list[Stage],
    ) -> tuple[ProcessID, StepID]:
        process = self.repo.create_process(
            target=target,
            owner=owner,
            action_id=action_id,
            stages=stages,
        )

        steps = self.repo.create_steps(process_id=process.id, stages=stages)
        current_step_id = steps[0].id

        self.repo.update_process(
            process_id=process.id,
            data=ProcessUpdateDTO(current_step=current_step_id),
        )
        return process.id, current_step_id

    def update_process_sync_key(self, *, process_id: ProcessID, sync_key: UUID, new_sync_key: UUID) -> None:
        if not self.repo.update_process_sync_key(process_id=process_id, sync_key=sync_key, new_sync_key=new_sync_key):
            raise SyncKeyMismatchError(f"There is no #{process_id} process with sync_key {sync_key}")

    def update_step(self, *, step_id: ActionProcessStepID, state: ProcessStepState) -> None:
        self.repo.update_step(step_id=step_id, data=StepUpdateDTO(state=state))

    def complete_process(self, process: ActionProcess) -> None:
        for step in self.repo.retrieve_steps(process_id=process.id):
            if step.state != ProcessStepState.COMPLETED:
                raise ActionProcessOperationError("All steps must be completed")

        self.repo.set_process_status(process=process, state=ProcessState.COMPLETED)

    def reset_step(
        self, *, process_id: ProcessID, step_id: ActionProcessStepID
    ) -> tuple[ActionProcessStepID | None, ActionProcessStepID | None]:
        step_ids = set(self.repo.retrieve_step_ids_starting_with(process_id=process_id, step_id=step_id))
        self.repo.revoke_steps(step_ids)

        current_id, last_completed_id = operations.find_current_and_last_completed_steps(
            steps=self.repo.retrieve_steps(process_id=process_id)
        )

        self.repo.update_process(
            process_id=process_id,
            data=ProcessUpdateDTO(current_step=current_id, last_completed_step=last_completed_id),
        )

        return current_id, last_completed_id

    def complete_step(
        self,
        *,
        process_id: ProcessID,
        step_id: ActionProcessStepID,
    ) -> ActionProcessStepID | None:
        self.repo.update_step(step_id=step_id, data=StepUpdateDTO(state=ProcessStepState.COMPLETED))

        current_id, last_completed_id = operations.find_current_and_last_completed_steps(
            steps=self.repo.retrieve_steps(process_id=process_id)
        )
        self.repo.update_process(
            process_id=process_id,
            data=ProcessUpdateDTO(current_step=current_id, last_completed_step=last_completed_id),
        )
        return current_id

    def revoke_next_steps(self, *, process_id: ProcessID, step_id: ActionProcessStepID) -> set[ActionProcessStepID]:
        step_ids = set(self.repo.retrieve_next_step_ids(process_id=process_id, step_id=step_id))
        self.repo.revoke_steps(step_ids)
        return step_ids

    def perform_mapping(
        self,
        *,
        process_id: ProcessID,
        step_id: ActionProcessStepID,
        step_input_data: StepInputDTO,
    ) -> None:
        mapping_input = step_input_data.mapping
        if not mapping_input or not mapping_input.delta:
            # Nothing to process — just upsert and return
            self.repo.upsert_step_input(step_id=step_id, data=step_input_data)
            return

        cumulative_delta = HostComponentMapDeltaSets()

        previous_mapping_input = self.repo.retrieve_previous_mapping_step_input_with_cumulative_delta(
            process_id=process_id, step_id=step_id
        )
        if previous_mapping_input and previous_mapping_input.mapping.cumulative_delta:
            prev_cumulative_delta = previous_mapping_input.mapping.cumulative_delta
            cumulative_delta.add.update(prev_cumulative_delta.add)
            cumulative_delta.remove.update(prev_cumulative_delta.remove)

        # Apply the new delta for the current step
        cumulative_delta.add.update(mapping_input.delta.add)
        cumulative_delta.remove.difference_update(mapping_input.delta.add)

        for rule in mapping_input.delta.remove:
            if rule in cumulative_delta.add:
                cumulative_delta.add.discard(rule)
            else:
                cumulative_delta.remove.add(rule)

        # Convert sets back to list of dicts
        step_input_data.mapping = MappingInputDTO(
            delta=mapping_input.delta, cumulative_delta=cumulative_delta.to_list_delta()
        )

        self.repo.upsert_step_input(step_id=step_id, data=step_input_data)
