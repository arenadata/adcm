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
from typing import Literal, Mapping, TypedDict

from core import config
from core.action import wizard
from core.types import (
    ComponentID,
    ComponentNameKey,
    Descriptor,
    HostID,
    HostName,
    ShortObjectInfo,
)

CurrentStep = dict[Literal["stage", "step"], str]


class ProcessContext(TypedDict):
    current: CurrentStep | None
    stages: dict[str, dict]


@dataclass(slots=True)
class ProcessInfo:
    current: CurrentStep | None
    stages: dict[str, dict]
    cumulative_delta: dict[str, set[tuple[int, str]]]

    def to_context(self) -> ProcessContext:
        return ProcessContext(stages=self.stages, current=self.current)


def construct_process_info(
    process_id: wizard.ProcessID,
    steps_with_data: list[wizard.StepWithData],
    component_map: Mapping[ComponentID, ComponentNameKey],
    host_map: Mapping[HostID, ShortObjectInfo],
    config_service: config.ConfigService,
) -> ProcessInfo:
    current: CurrentStep | None = None
    stages = defaultdict(dict)
    cumulative_delta = {}

    current_step = wizard.steps.detect_current_step(step for step, _ in steps_with_data)
    if current_step:
        stage_name, step_name = current_step.full_name
        current = {"stage": stage_name, "step": step_name}

    latest_cumulative_delta = None

    for step, data in steps_with_data:
        # shortcut to avoid "expensive" match when no data is here
        if data is None:
            continue

        stage_name, step_name = step.full_name

        # for some reason, pyright isn't smart enough to infer that data type will always match step type,
        # so we match on both
        match step, data:
            case wizard.ConfigStep(spec=(config_spec, _)), wizard.ConfigStepData():
                file_owner: tuple[Descriptor[Literal["process"]], Descriptor[Literal["step"]]] = (
                    Descriptor(id=process_id, type="process"),
                    Descriptor(id=step.id, type="step"),
                )
                prepared_config = config_service.prepare_configuration_for_ansible(
                    configuration=data, specification=config_spec, file_owner=file_owner
                )
                stages[stage_name][step_name] = {"config": prepared_config.values}

            case wizard.MappingStep(), wizard.MappingStepData():
                step_delta_groups = _resolve_host_groups(
                    delta=data.delta, component_map=component_map, host_map=host_map
                )
                stages[stage_name][step_name] = {
                    "groups": {
                        group: sorted(names)
                        for group, names in _keep_only_host_names_in_groups(step_delta_groups).items()
                    }
                }
                latest_cumulative_delta = data.cumulative

    if latest_cumulative_delta:
        cumulative_delta = {
            group: set(hosts)
            for group, hosts in _resolve_host_groups(
                delta=latest_cumulative_delta, component_map=component_map, host_map=host_map
            ).items()
        }

    return ProcessInfo(current=current, stages=stages, cumulative_delta=cumulative_delta)


# maybe it can become a callable passed to the function above that resolved delta to groups:
# requires further unification of types
def _resolve_host_groups(
    delta: wizard.Delta,
    component_map: Mapping[ComponentID, ComponentNameKey],
    host_map: Mapping[HostID, ShortObjectInfo],
) -> dict[str, list[tuple[HostID, HostName]]]:
    groups = defaultdict(list)

    for operation, pairs in delta.items():
        for pair in pairs:
            component_key = component_map[pair.component_id]
            group_name = f"{component_key.service}.{component_key.component}.{operation}"

            host = host_map[pair.host_id]
            groups[group_name].append((host.id, host.name))

    return groups


def _keep_only_host_names_in_groups(
    groups_with_ids: dict[str, list[tuple[HostID, HostName]]],
) -> dict[str, list[HostName]]:
    return {key: [name for _, name in hosts] for key, hosts in groups_with_ids.items()}
