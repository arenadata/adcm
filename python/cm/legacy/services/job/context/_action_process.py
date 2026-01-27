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

from collections import defaultdict
from dataclasses import dataclass

from core.legacy.cluster.types import ClusterTopology
from core.types import Descriptor
from infra.services import get_config_service
import core

from cm.legacy.services.job.context._types import CurrentStep, ProcessContext
from cm.models import Process, ProcessStep


@dataclass(slots=True)
class ProcessInfo:
    current: CurrentStep | None
    stages: dict[str, dict]
    cumulative_delta: dict[str, set[tuple[int, str]]]

    def to_context(self) -> ProcessContext:
        return ProcessContext(stages=self.stages, current=self.current)


def get_action_process_context(process: Process, topology: ClusterTopology) -> ProcessInfo:
    steps_qs = process.steps.all().select_related("processstepinput")

    steps_by_name: dict[str, ProcessStep] = {step.name: step for step in steps_qs}

    # Global cumulative groups
    cumulative_groups: dict[str, set[str]] = defaultdict(set)

    current: CurrentStep | None = None
    stages = {}

    for stage in process.flow_spec:
        stages[stage["name"]] = {}
        for step in stage["steps"]:
            step_data = {}
            step_obj = steps_by_name[step["name"]]

            if process.current_step and step_obj.id == process.current_step.id:
                current = {"step": step["name"], "stage": stage["name"]}

            if hasattr(step_obj, "processstepinput"):
                match step["type"]:
                    case core.action.wizard.StepType.CONFIGURATION:
                        step_data = _build_config_for_step(process=process, step_obj=step_obj)
                    case core.action.wizard.StepType.MAPPING if step_obj.processstepinput.mapping:
                        step_data["groups"], cumulative_groups = _build_mapping_for_step(step_obj, topology)

            if step_data:
                stages[stage["name"]][step["name"]] = step_data

    return ProcessInfo(stages=stages, current=current, cumulative_delta=cumulative_groups)


def _build_config_for_step(process: Process, step_obj: ProcessStep) -> dict:
    config_input = step_obj.processstepinput.configuration

    config_service = get_config_service()

    specification = core.config.spec.FullSpec.model_validate(step_obj.step_spec[0])
    attributes = {key: core.config.Attributes(**value) for key, value in config_input["attributes"].items()}

    configuration = config_service.prepare_configuration_for_ansible(
        configuration=core.config.Configuration(values=config_input["values"], attributes=attributes),
        specification=specification,
        file_owner=(Descriptor(id=process.pk, type="process"), Descriptor(id=step_obj.pk, type="step")),
        inplace=True,
    )

    return {"config": configuration.values}


def _build_mapping_for_step(
    step_obj: ProcessStep, topology: ClusterTopology
) -> tuple[dict[str, list[str]], dict[str, list[tuple[int, str]]]]:
    mapping = step_obj.processstepinput.mapping

    groups = _build_groups(mapping["delta"], topology)
    cumulative_groups = _build_groups(mapping["cumulative_delta"], topology, with_id=True)

    return groups, cumulative_groups


def _build_groups(
    delta_mapping: dict[str, list[dict]], topology: ClusterTopology, with_id: bool = False
) -> dict[str, list[str]] | dict[str, list[tuple[int, str]]]:
    groups = defaultdict(list)
    for operation, pairs in delta_mapping.items():
        for pair in pairs:
            component_key = next(
                k for k, v in topology.component_full_name_id_mapping.items() if v == pair["component_id"]
            )
            host = topology.hosts[pair["host_id"]]
            group_name = f"{component_key.service}.{component_key.component}.{operation}"
            groups[group_name].append((host.id, host.name) if with_id else host.name)
    for group_name in groups:
        groups[group_name].sort()
    return groups
