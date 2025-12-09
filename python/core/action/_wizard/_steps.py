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

from typing import Iterable, TypeVar

from core.action._wizard._types import Step, StepState

StepT = TypeVar("StepT", bound=Step)


def detect_current_step(steps: Iterable[StepT]) -> StepT | None:
    for step in steps:
        if step.state != StepState.COMPLETED:
            return step

    return None
