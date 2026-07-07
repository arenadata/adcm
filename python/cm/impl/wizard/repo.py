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

from collections.abc import Callable, Generator
from dataclasses import dataclass
from functools import partial
from typing import Any, cast
from uuid import UUID, uuid4

from core import action, config, mapping
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
    TaskID,
)
from pydantic import RootModel
import core

from cm.converters import core_type_to_model
from cm.legacy.services.action_process.errors import ActionProcessNotFoundError, ActionProcessStepNotFoundError
from cm.models import (
    Process,
    ProcessStep,
    ProcessStepInput,
    TaskLog,
)

ActionProcess = wizard.ActionProcessModel
Step = wizard.ActionProcessStepModel
MappingStepInput = wizard.MappingStepInput
ProcessState = wizard.ProcessState
ProcessStepState = wizard.ProcessStepState
ProcessUpdateDTO = wizard.ProcessUpdateDTO
StepInputDTO = wizard.StepInputDTO
StepUpdateDTO = wizard.StepUpdateDTO

_Stages = RootModel[list[core.action.wizard.Stage]]


@dataclass(slots=True)
class WizardRepo(wizard.WizardRepoI):
    def get_steps_with_data(self, process_id: wizard.ProcessID) -> list[wizard.StepWithData]:
        return get_steps_with_data(process_id=process_id)

    def create_process(
        self,
        *,
        target: ActionTargetDescriptor,
        owner: CoreObjectDescriptor,
        action_id: ActionID,
        stages: list[wizard.Stage],
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

    def create_steps(self, process_id: ActionProcessID, stages: list[wizard.Stage]) -> list[ProcessStep]:
        objects: list[ProcessStep] = []
        for stage in stages:
            for step in stage.steps:
                objects.append(
                    ProcessStep(
                        process_id=process_id,
                        type=step.type.value,
                        name=step.name,
                        stage=stage.name,
                        description=step.extra.description,
                        display_name=step.extra.display_name,
                        step_spec=None,
                        required=step.required,
                    )
                )
        return ProcessStep.objects.bulk_create(objects)

    def set_process_status(self, process: ActionProcess, state: ProcessState) -> bool:
        records_updated = Process.objects.filter(pk=process.id).update(state=state)
        return bool(records_updated)

    def retrieve_step(self, process_id: ActionProcessID, step_id: ActionProcessStepID) -> Step:
        try:
            return next(self.retrieve_steps(process_id=process_id, id=step_id))
        except StopIteration as error:
            if not Process.objects.filter(id=process_id).exists():
                raise ActionProcessNotFoundError() from error

            raise ActionProcessStepNotFoundError() from error

    def retrieve_running_step_ids(self, process_id: ActionProcessID) -> set[ActionProcessStepID]:
        return set(
            ProcessStep.objects.filter(process_id=process_id, state=ProcessStepState.RUNNING).values_list(
                "id", flat=True
            )
        )

    def retrieve_steps(self, process_id: ActionProcessID, **kwargs: Any) -> Generator[Step, None, None]:
        for step_orm in ProcessStep.objects.filter(process_id=process_id, **kwargs).order_by("id"):
            yield Step.model_validate(step_orm, from_attributes=True)

    def retrieve_process(self, process_id: ActionProcessID) -> ActionProcess:
        try:
            process = Process.objects.get(id=process_id)
        except Process.DoesNotExist as error:
            raise ActionProcessNotFoundError() from error

        return ActionProcess.model_validate(process, from_attributes=True)

    def update_step(self, step_id: ActionProcessStepID, data: StepUpdateDTO) -> None:
        if data.step_spec is not None:
            match data.step_spec:
                case (core.config.spec.FullSpec(), _):
                    data.step_spec = (data.step_spec[0].model_dump(), data.step_spec[1])

        ProcessStep.objects.filter(id=step_id).update(**data.model_dump(exclude_unset=True))

    def upsert_step_input(self, step_id: ActionProcessStepID, data: StepInputDTO) -> None:
        dto_data = data.model_dump()
        inputs_qs = ProcessStepInput.objects.filter(step_id=step_id)

        if not inputs_qs.exists():
            create_data = {"step_id": step_id, **dto_data}
            ProcessStepInput.objects.create(**create_data)
        else:
            inputs_qs.update(**dto_data)

    def retrieve_previous_mapping_step_input_with_cumulative_delta(
        self, process_id: ActionProcessID, step_id: ActionProcessStepID
    ) -> MappingStepInput | None:
        candidates: set[ActionProcessStepID] = set()
        for step in self.retrieve_steps(
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

    def update_process(self, process_id: ActionProcessID, data: ProcessUpdateDTO) -> None:
        Process.objects.filter(id=process_id).update(**data.model_dump(exclude_unset=True))

    def update_process_sync_key(self, process_id: ActionProcessID, sync_key: UUID, new_sync_key: UUID) -> bool:
        rows_matched = Process.objects.filter(id=process_id, sync_key=sync_key).update(sync_key=new_sync_key)
        return bool(rows_matched)

    def retrieve_task_orm(self, task_id: TaskID) -> wizard.TaskORM:
        return cast(wizard.TaskORM, TaskLog.objects.get(id=task_id))

    def retrieve_next_step_ids(
        self, process_id: ActionProcessID, step_id: ActionProcessStepID
    ) -> tuple[ActionProcessStepID]:
        return tuple(
            ProcessStep.objects.filter(process_id=process_id, id__gt=step_id)
            .values_list("id", flat=True)
            .order_by("id")
        )

    def retrieve_step_ids_starting_with(
        self, process_id: ActionProcessID, step_id: ActionProcessStepID
    ) -> tuple[ActionProcessStepID]:
        return tuple(
            ProcessStep.objects.filter(process_id=process_id, id__gte=step_id)
            .values_list("id", flat=True)
            .order_by("id")
        )

    def revoke_steps(self, step_ids: set[ActionProcessStepID]) -> None:
        if not step_ids:
            return
        ProcessStepInput.objects.filter(step_id__in=step_ids).delete()
        ProcessStep.objects.filter(id__in=step_ids).update(state=ProcessStepState.CREATED, step_spec=None)

    def retrieve_related_cluster_id_and_cluster_bundle_id(
        self, object_: CoreObjectDescriptor
    ) -> tuple[ClusterID, BundleID]:
        values = ("cluster_id", "cluster__prototype__bundle_id")
        if object_.type == ADCMCoreType.CLUSTER:
            values = ("id", "prototype__bundle_id")

        return core_type_to_model(object_.type).objects.values_list(*values).get(id=object_.id)


def get_steps_with_data(process_id: wizard.ProcessID) -> list[wizard.StepWithData]:
    step_input_relation = "processstepinput"
    query = ProcessStep.objects.select_related(step_input_relation).filter(process_id=process_id).order_by("id")
    serialize = partial(serialize_step, extract_data=return_step_input)
    return list(map(serialize, query))


def return_step_input(step: ProcessStep) -> ProcessStepInput | None:
    return getattr(step, "processstepinput", None)


def serialize_step(
    orm_step: ProcessStep,
    extract_data: Callable[[ProcessStep], ProcessStepInput | None],
) -> wizard.StepWithData:
    type_ = wizard.StepType(orm_step.type)
    state = wizard.StepState(orm_step.state)
    full_name = (orm_step.stage, orm_step.name)
    required = orm_step.required
    extra = wizard.StepExtra(display_name=orm_step.display_name, description=orm_step.description)

    common_args = {"id": orm_step.pk, "state": state, "full_name": full_name, "extra": extra, "required": required}

    data = None
    spec = None

    step_input = extract_data(orm_step)

    match type_:
        case wizard.StepType.CONFIGURATION:
            if orm_step.step_spec is not None:
                spec = to_step_config_spec(orm_step.step_spec)

            if step_input is not None:
                data = to_step_config_data(step_input)

            step = wizard.ConfigStep(**common_args, type=type_, spec=spec)

            return step, data

        case wizard.StepType.OPERATION:
            if orm_step.step_spec is not None:
                spec = to_step_operation_spec(orm_step.step_spec)

            if step_input is not None:
                data = to_step_operation_data(step_input)

            step = wizard.OperationStep(**common_args, type=type_, spec=spec)
            return step, data

        case wizard.StepType.MAPPING:
            if orm_step.step_spec is not None:
                spec = to_step_mapping_spec(orm_step.step_spec)

            if step_input is not None:
                data = to_step_mapping_data(step_input)

            step = wizard.MappingStep(**common_args, type=type_, spec=spec)

            return step, data


def to_step_config_spec(spec: list[dict]) -> wizard.ConfigStepSpec:
    spec_raw, defaults_raw = spec
    return config.spec.FullSpec.model_validate(spec_raw), config.Defaults(**defaults_raw)


def to_step_operation_spec(spec: Any) -> wizard.OperationStepSpec:
    return [action.JobSpec.model_validate(rec) for rec in spec]


def to_step_mapping_spec(spec: Any) -> wizard.MappingStepSpec:
    return [mapping.MappingRule(**record) for record in spec]


def to_step_config_data(data: ProcessStepInput) -> wizard.ConfigStepData:
    return wizard.ConfigStepData(
        values=data.configuration["values"],
        attributes={key: config.Attributes(**attrs) for key, attrs in data.configuration["attributes"].items()},
    )


def to_step_operation_data(data: ProcessStepInput) -> wizard.OperationStepData:
    # type is not designed yet, return unusable dummy
    _ = data
    return 1


def to_step_mapping_data(data: ProcessStepInput) -> wizard.MappingStepData:
    delta = {
        operation: [mapping.MappingPair(**rec) for rec in pairs] for operation, pairs in data.mapping["delta"].items()
    }
    cumulative_delta = {
        operation: [mapping.MappingPair(**rec) for rec in pairs]
        for operation, pairs in data.mapping["cumulative_delta"].items()
    }

    return wizard.MappingStepData(delta=delta, cumulative=cumulative_delta)
