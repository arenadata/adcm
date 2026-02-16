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
from functools import partial
from typing import Any, Callable

from core import action, config, mapping
from core.action import wizard

from cm.models import ProcessStep, ProcessStepInput


@dataclass(slots=True)
class WizardRepo(wizard.WizardRepoI):
    def get_steps_with_data(self, process_id: wizard.ProcessID) -> list[wizard.StepWithData]:
        return get_steps_with_data(process_id=process_id)


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

    common_args = {"id": orm_step.pk, "state": state, "full_name": full_name}

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
