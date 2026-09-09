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

from collections.abc import Generator
from pathlib import Path
from typing import Literal, TypeAlias
from uuid import UUID, uuid4

from core.action import wizard
from core.types import (
    ActionID,
    ActionProcessID,
    ActionProcessStepID,
    ActionTargetDescriptor,
    ADCMCoreType,
    BundleID,
    ClusterID,
    CoreObjectDescriptor,
    PrototypeID,
    TaskID,
)
from django.conf import settings
from pydantic import RootModel
import core

from cm.converters import core_type_to_model
from cm.legacy.services.action_process.errors import ActionProcessNotFoundError, ActionProcessStepNotFoundError
from cm.legacy.services.action_process.types import (
    ActionProcess,
    MappingStepInput,
    ProcessState,
    ProcessStepState,
    ProcessUpdateDTO,
    Step,
    StepInputDTO,
    StepUpdateDTO,
)
from cm.models import (
    Action,
    Cluster,
    ObjectType,
    Process,
    ProcessStep,
    ProcessStepInput,
    Prototype,
    TaskLog,
)

WasUpdated: TypeAlias = bool

_Stages = RootModel[list[core.action.wizard.Stage]]


def get_bundle_root_from_prototype(prototype_id: PrototypeID) -> Path:
    hash_ = Prototype.objects.values_list("bundle__hash", flat=True).get(id=prototype_id)

    return Path(settings.BUNDLE_DIR, hash_)


def create_process(
    target: ActionTargetDescriptor,
    owner: CoreObjectDescriptor,
    action_id: ActionID,
    stages: list[core.action.wizard.Stage],
) -> ActionProcess:
    process = Process.objects.create(
        action_id=action_id,
        target_id=target.id,
        target_type=target.type.value,
        owner_id=owner.id,
        owner_type=owner.type.value,
        last_completed_step=None,
        flow_spec=_Stages(stages).model_dump(),
        sync_key=uuid4(),
    )

    return ActionProcess.model_validate(process, from_attributes=True)


def retrieve_action_orm(action_id: ActionID) -> Action:
    return Action.objects.get(id=action_id)


def retrieve_step_orm(step_id: ActionProcessStepID) -> ProcessStep:
    return ProcessStep.objects.get(id=step_id)


def retrieve_process_orm(process_id: ActionProcessID) -> Process:
    return Process.objects.get(id=process_id)


def set_process_status(process: ActionProcess, state: ProcessState) -> WasUpdated:
    records_updated = Process.objects.filter(pk=process.id).update(state=state)
    return bool(records_updated)


# For better naming in retrieve names function.
# Remove after rework to dicts / better mechanism.
_StepName: TypeAlias = str
_StepDisplayName: TypeAlias = str
_StepStateAsStr: TypeAlias = str


def retrieve_step_names_id_state_map(
    process_id: ActionProcessID,
) -> dict[tuple[_StepName, _StepDisplayName], tuple[ActionProcessStepID, _StepStateAsStr]]:
    return {
        (name, display_name): (id_, state)
        for name, display_name, id_, state in ProcessStep.objects.values_list(
            "name", "display_name", "id", "state"
        ).filter(process_id=process_id)
    }


def retrieve_step(process_id: ActionProcessID, step_id: ActionProcessStepID) -> Step:
    try:
        return next(retrieve_steps(process_id=process_id, id=step_id))
    except StopIteration as error:
        if not Process.objects.filter(id=process_id).exists():
            raise ActionProcessNotFoundError() from error

        raise ActionProcessStepNotFoundError() from error


def retrieve_running_step_ids(process_id: ActionProcessID) -> set[ActionProcessStepID]:
    return set(
        ProcessStep.objects.filter(process_id=process_id, state=ProcessStepState.RUNNING).values_list("id", flat=True)
    )


def retrieve_steps(process_id: ActionProcessID, **kwargs) -> Generator[Step, None, None]:
    for step_orm in ProcessStep.objects.filter(process_id=process_id, **kwargs).order_by("id"):
        yield Step.model_validate(step_orm, from_attributes=True)


def retrieve_process(process_id: ActionProcessID) -> ActionProcess:
    try:
        process = Process.objects.get(id=process_id)
    except Process.DoesNotExist as error:
        raise ActionProcessNotFoundError() from error

    return ActionProcess.model_validate(process, from_attributes=True)


def update_step(step_id: ActionProcessStepID, data: StepUpdateDTO) -> None:
    # patch for serialization of config (because of exclude_unset)
    if data.step_spec is not None:
        match data.step_spec:
            case (core.config.spec.FullSpec(), _):
                data.step_spec = (data.step_spec[0].model_dump(), data.step_spec[1])

    ProcessStep.objects.filter(id=step_id).update(**data.model_dump(exclude_unset=True))


def upsert_step_input(step_id: ActionProcessStepID, data: StepInputDTO) -> None:
    dto_data = data.model_dump()
    inputs_qs = ProcessStepInput.objects.filter(step_id=step_id)

    if not inputs_qs.exists():
        create_data = {"step_id": step_id, **dto_data}
        ProcessStepInput.objects.create(**create_data)
    else:
        inputs_qs.update(**dto_data)


def retrieve_previous_mapping_step_input_with_cumulative_delta(
    process_id: ActionProcessID, step_id: ActionProcessStepID
) -> MappingStepInput | None:
    candidates: set[ActionProcessStepID] = set()
    for step in retrieve_steps(
        process_id=process_id, id__lt=step_id, state__in=[ProcessStepState.COMPLETED, ProcessStepState.RUNNING]
    ):
        if step.type == wizard.StepType.MAPPING:
            candidates.add(step.id)

    if (
        input_ := ProcessStepInput.objects.filter(step_id__in=candidates, mapping__isnull=False)
        .order_by("-created_at")
        .first()
    ):
        return MappingStepInput.model_validate(input_, from_attributes=True)

    return None


def update_process(process_id: ActionProcessID, data: ProcessUpdateDTO) -> None:
    Process.objects.filter(id=process_id).update(**data.model_dump(exclude_unset=True))


def update_process_sync_key(process_id: ActionProcessID, sync_key: UUID, new_sync_key: UUID) -> WasUpdated:
    rows_matched = Process.objects.filter(id=process_id, sync_key=sync_key).update(sync_key=new_sync_key)
    return bool(rows_matched)


def find_step_spec_declaration(
    step: Step, process_flow_spec: list[core.action.wizard.Stage]
) -> core.action.wizard.StepDefinition:
    if not process_flow_spec:
        raise RuntimeError("process.flow_spec is empty")

    for raw_stage in process_flow_spec:
        for raw_step in raw_stage.steps:
            if (raw_stage.name, raw_step.name) == (step.stage, step.name):
                return raw_step

    raise RuntimeError(f"Can't find flow_spec for {step}")


def retrieve_task_orm(task_id: TaskID) -> TaskLog:
    return TaskLog.objects.get(id=task_id)


def retrieve_next_step_ids(process_id: ActionProcessID, step_id: ActionProcessStepID) -> tuple[ActionProcessStepID]:
    return tuple(
        ProcessStep.objects.filter(process_id=process_id, id__gt=step_id).values_list("id", flat=True).order_by("id")
    )


def retrieve_cluster_component_definition_keys(cluster_id: ClusterID) -> set[tuple[Literal["component"], str, str]]:
    """returns set of component names in format `("component", service_name, component_name)`"""

    bundle_id = Cluster.objects.values_list("prototype__bundle_id", flat=True).get(id=cluster_id)
    prototype_qs = Prototype.objects.values_list("name", "parent__name").filter(
        bundle_id=bundle_id, type=ObjectType.COMPONENT
    )

    return {("component", parent_name, name) for name, parent_name in prototype_qs}


def retrieve_related_cluster_id_and_cluster_bundle_id(object_: CoreObjectDescriptor) -> tuple[ClusterID, BundleID]:
    values = ("cluster_id", "cluster__prototype__bundle_id")
    if object_.type == ADCMCoreType.CLUSTER:
        values = ("id", "prototype__bundle_id")

    return core_type_to_model(object_.type).objects.values_list(*values).get(id=object_.id)


def get_bundle_context_from_prototype(prototype_id: PrototypeID) -> core.bundle.BundleContext:
    bundle_id, hash_, contract_version = Prototype.objects.values_list(
        "bundle_id", "bundle__hash", "bundle__contract_version"
    ).get(id=prototype_id)
    path = Path(settings.BUNDLE_DIR, hash_)

    return core.bundle.BundleContext(id=bundle_id, root=path, contract_version=contract_version)
