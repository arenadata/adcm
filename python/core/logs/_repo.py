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

from typing import Protocol

from core.logs._types import CheckLogContent, CheckLogResult, GroupCheckLogContent, Severity
from core.types import CheckLogID, GroupCheckLogID, IsCreated, JobID, LogStorageID


class LogsRepoI(Protocol):
    def get_check_logs_by_job_id(self, job_id: JobID) -> list[tuple[GroupCheckLogID | None, CheckLogContent]]:
        ...

    def get_group_check_logs_by_job_id(self, job_id: JobID) -> dict[GroupCheckLogID, GroupCheckLogContent]:
        ...

    def update_log_storage_content_for_job(self, job_id: JobID, content: list[CheckLogContent | GroupCheckLogContent]):
        ...

    def clear_check_logs_for_job(self, job_id: JobID) -> None:
        ...

    def prepare_log_storage_for_check(self, job_id: JobID) -> tuple[LogStorageID, IsCreated]:
        ...

    def prepare_group_check_log(
        self, job_id: JobID, title: str, message: str, result: bool, severity: Severity
    ) -> tuple[GroupCheckLogID, IsCreated]:
        ...

    def create_check_log(
        self,
        job_id: JobID,
        title: str,
        message: str,
        result: bool,
        severity: Severity,
    ) -> CheckLogID:
        ...

    def add_check_log_to_group(self, check_log_id: CheckLogID, group_id: GroupCheckLogID) -> None:
        ...

    def update_group_check_log(self, group_id: GroupCheckLogID, message: str, result: bool, severity: Severity) -> None:
        ...

    def get_check_log_results_for_group(self, group_id: GroupCheckLogID) -> list[CheckLogResult]:
        ...
