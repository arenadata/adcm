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
from pathlib import Path
from typing import Any, Callable, Iterable

from core import config, mapping
from core.action import wizard

from cm.impl.common.config_spec import build_defaults, build_specification
from cm.models import Process, ProcessStep, ProcessStepInput, PrototypeConfig

_BuildDefaults = Callable[[Iterable[PrototypeConfig], config.spec.FullSpec], config.Defaults]


@dataclass(slots=True)
class WizardRepo(wizard.WizardRepoI):
    def get_steps_with_data(
        self,
        process_id: wizard.ProcessID,
        *,
        bundles_dir: Path,
    ) -> list[wizard.StepWithData]:
        bundle_hash = Process.objects.values_list("action__prototype__bundle__hash", flat=True).get(id=process_id)
        bundle_root = bundles_dir / bundle_hash
        # note that defaults aren't encrypted in here as it should be everywhere
        build_defaults_ = partial(build_defaults, encrypt=lambda x: x, bundle_root=bundle_root)
        return get_steps_with_data(process_id=process_id, build_defaults_=build_defaults_)


def get_steps_with_data(process_id: wizard.ProcessID, build_defaults_: _BuildDefaults) -> list[wizard.StepWithData]:
    step_input_relation = "processstepinput"
    query = ProcessStep.objects.select_related(step_input_relation).filter(process_id=process_id).order_by("id")
    serialize = partial(serialize_step, extract_data=return_step_input, build_defaults_=build_defaults_)
    return list(map(serialize, query))


def return_step_input(step: ProcessStep) -> ProcessStepInput | None:
    return getattr(step, "processstepinput", None)


def serialize_step(
    orm_step: ProcessStep,
    extract_data: Callable[[ProcessStep], ProcessStepInput | None],
    build_defaults_: _BuildDefaults,
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
                spec = to_step_config_spec(orm_step.step_spec, build_defaults_=build_defaults_)

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


def to_step_config_spec(spec: list[dict], build_defaults_: _BuildDefaults) -> wizard.ConfigStepSpec:
    prototype_configs = tuple(PrototypeConfig(**rec) for rec in spec)
    specification = build_specification(records=prototype_configs, group_customization_flag=False)
    defaults = build_defaults_(prototype_configs, specification)
    return specification, defaults


def to_step_operation_spec(spec: Any) -> wizard.OperationStepSpec:
    # type is not designed yet, return unusable dummy
    _ = spec
    return 1


def to_step_mapping_spec(spec: Any) -> wizard.MappingStepSpec:
    # type is not designed yet, return unusable dummy
    _ = spec
    return 1


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
