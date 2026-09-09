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

from core.action import ExecutionStatus
from core.types import JobID, TaskID


class JobFailedFlowError(Exception):
    def __init__(self, *args, task_id: TaskID, job_id: JobID, final_status: ExecutionStatus) -> None:
        super().__init__(*args)

        self.task_id = task_id
        self.job_id = job_id
        self.final_status = final_status
