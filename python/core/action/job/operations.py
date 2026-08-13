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

from typing import Literal

from core.action._types import ExecutionStatus

TaskCompletionStatus = Literal[ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.ABORTED]


def calculate_task_final_status(last_job_status: ExecutionStatus, task_is_aborted: bool) -> TaskCompletionStatus:
    if task_is_aborted or last_job_status == ExecutionStatus.ABORTED:
        return ExecutionStatus.ABORTED

    if last_job_status == ExecutionStatus.SUCCESS:
        return ExecutionStatus.SUCCESS

    # most likely need to find a way to "detect" a broken case

    return ExecutionStatus.FAILED


def is_terminatable_status(status: ExecutionStatus) -> bool:
    return status in (ExecutionStatus.CREATED, ExecutionStatus.SCHEDULED, ExecutionStatus.RUNNING)
