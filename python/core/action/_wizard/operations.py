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

from typing import Iterable
from uuid import UUID, uuid4

from core.action._wizard._types import Stage, StepDefinition
from core.action._wizard._types_purgatory import ProcessStepState, Step
from core.types import ActionProcessStepID


def get_new_process_sync_key() -> UUID:
    return uuid4()


def find_current_and_last_completed_steps(
    steps: Iterable[Step],
) -> tuple[ActionProcessStepID | None, ActionProcessStepID | None]:
    current = None
    last_completed = None

    for step in sorted(steps, key=lambda s: s.id, reverse=True):
        if step.state in {ProcessStepState.CREATED, ProcessStepState.RUNNING}:
            current = step.id

        if last_completed is None and step.state == ProcessStepState.COMPLETED:
            last_completed = step.id

        if current and last_completed:
            break

    return current, last_completed


def find_step_spec_declaration(step: Step, process_flow_spec: list[Stage]) -> StepDefinition:
    for raw_stage in process_flow_spec:
        if raw_stage.name == step.stage:
            for raw_step in raw_stage.steps:
                if raw_step.name == step.name:
                    return raw_step

    raise RuntimeError(f"Can't find flow_spec for {step}")
