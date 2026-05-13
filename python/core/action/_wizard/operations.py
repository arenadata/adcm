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

from typing import Iterable, TypeAlias
from uuid import UUID, uuid4

from core.action._wizard._types import Stage, StepDefinition, StepState
from core.action._wizard._types_purgatory import SUCCESS_FINAL_PROCESS_STATES, Step
from core.types import ActionProcessStepID

_StepStateIDPair: TypeAlias = tuple[tuple[StepState, ActionProcessStepID], ...]
_ActualSteps: TypeAlias = tuple[ActionProcessStepID | None, ActionProcessStepID | None]


def get_new_process_sync_key() -> UUID:
    return uuid4()


def find_current_and_last_completed_steps(steps: Iterable[Step]) -> _ActualSteps:
    step_info: _StepStateIDPair = tuple((step.state, step.id) for step in steps)
    return get_current_and_last_completed_step_ids(step_info)


def find_step_spec_declaration(step: Step, process_flow_spec: list[Stage]) -> StepDefinition:
    for raw_stage in process_flow_spec:
        if raw_stage.name == step.stage:
            for raw_step in raw_stage.steps:
                if raw_step.name == step.name:
                    return raw_step

    raise RuntimeError(f"Can't find flow_spec for {step}")


def get_step_by_id(*, steps: Iterable[Step], step_id: ActionProcessStepID) -> Step:
    for step in steps:
        if step.id == step_id:
            return step

    raise ValueError(f"Can't find a step with id {step_id}")


def get_current_and_last_completed_step_ids(step_info: _StepStateIDPair) -> _ActualSteps:
    current_id = None
    last_completed_id = None

    sorted_steps = sorted(step_info, key=lambda s: s[1], reverse=True)
    for state, step_id in sorted_steps:
        if state in SUCCESS_FINAL_PROCESS_STATES:
            last_completed_id = step_id
            break
        current_id = step_id

    return current_id, last_completed_id
