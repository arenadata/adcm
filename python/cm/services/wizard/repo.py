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

from pathlib import Path
from typing import TypeAlias
from uuid import uuid4

from core.bundle_alt.schema import WizardStage, WizardStep
from core.types import ActionID, ActionProcessID, ActionProcessStepID, CoreObjectDescriptor, PrototypeID, TaskID
from django.conf import settings

from cm.models import Action, Process, ProcessStep, Prototype, TaskLog
from cm.services.wizard.types import (
    ActionProcess,
    ProcessState,
    ProcessToChangeDTO,
    Step,
    StepUpdateDTO,
)

WasUpdated: TypeAlias = bool


def get_bundle_root_from_prototype(prototype_id: PrototypeID) -> Path:
    hash_ = Prototype.objects.values_list("bundle__hash", flat=True).get(id=prototype_id)

    return Path(settings.BUNDLE_DIR, hash_)


def create_process(object_: CoreObjectDescriptor, action_id: ActionID, stages: list[WizardStage]) -> ActionProcess:
    process = Process.objects.create(
        action_id=action_id,
        obejct_id=object_.id,
        object_type=object_.type.value,
        last_completed_step=None,
        flow_spec=[stage.model_dump(exclude_defaults=True, exclude_unset=True) for stage in stages],
        hash=uuid4(),
    )

    return ActionProcess.model_validate(process, from_attributes=True)


def create_stages(process_id: ActionProcessID, stages: list[WizardStage]) -> None:
    objects = []
    for stage in stages:
        for step in stage.steps:
            objects.append(
                ProcessStep(
                    process_id=process_id,
                    name=step.name,
                    display_name=step.display_name,
                    step_spec=None,
                )
            )

    ProcessStep.objects.bulk_create(objects)


def retrieve_action_orm(action_id: ActionID) -> Action:
    return Action.objects.get(id=action_id)


def set_process_status(process: ProcessToChangeDTO, state: ProcessState) -> WasUpdated:
    records_updated = Process.objects.filter(
        pk=process.id,
        hash=process.sync_key,
    ).update(state=state)
    return bool(records_updated)


def retrieve_step_names_id_map(process_id: ActionProcessID) -> dict[tuple[str, str], int]:
    return {
        (name, display_name): id_
        for name, display_name, id_ in ProcessStep.objects.values_list("name", "display_name", "id").filter(
            process_id=process_id
        )
    }


def retrieve_step(process_id: ActionProcessID, step_id: ActionProcessStepID) -> Step:
    process = retrieve_process(process_id=process_id)
    step = ProcessStep.objects.get(id=step_id, process_id=process_id)
    step_spec_raw = find_step_spec(step=step, process_flow_spec=process.flow_spec)
    step.type = step_spec_raw.step_type

    return Step.model_validate(step, from_attributes=True)


def retrieve_process(process_id: ActionProcessID) -> ActionProcess:
    process = Process.objects.get(id=process_id)

    return ActionProcess.model_validate(process, from_attributes=True)


def update_step(step_id: ActionProcessStepID, data: StepUpdateDTO) -> None:
    ProcessStep.objects.filter(id=step_id).update(**data.model_dump(exclude_unset=True))


def find_step_spec(step: Step, process_flow_spec: list[WizardStage]) -> WizardStep:
    if not process_flow_spec:
        raise RuntimeError("process.flow_spec is empty")

    for raw_stage in process_flow_spec:
        for raw_step in raw_stage.steps:
            if (raw_step.name, raw_step.display_name) == (step.name, step.display_name):
                return raw_step

    raise RuntimeError(f"Can't find flow_spec for {step}")


def retrieve_task_orm(task_id: TaskID) -> TaskLog:
    return TaskLog.objects.get(id=task_id)


def retrieve_next_step_ids(process_id: ActionProcessID, step_id: ActionProcessStepID) -> set[ActionProcessStepID]:
    # Here we rely on process steps bulk_create behavior:
    # ids of created rows are preserves the definition order in process.flow_spec
    return set(ProcessStep.objects.filter(process_id=process_id, id__gt=step_id).values_list("id", flat=True))
