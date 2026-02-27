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

from core.logs._operations import aggregate_check_logs_results_for_group
from core.logs._repo import LogsRepoI
from core.logs._types import CheckLogArguments, CheckLogContent, GroupCheckLogContent
from core.types import IsCreated, JobID, LogStorageID


@dataclass(slots=True)
class LogsService:
    repo: LogsRepoI

    def retrieve_check_logs_content_for_job(self, job_id: JobID) -> list[CheckLogContent | GroupCheckLogContent]:
        check_logs = self.repo.get_check_logs_by_job_id(job_id=job_id)
        group_check_logs = self.repo.get_group_check_logs_by_job_id(job_id=job_id)

        data = []
        added_groups = set()

        for group_id, check_log in check_logs:
            if group_id is None:
                data.append(check_log)
            else:
                if group_id not in added_groups:
                    added_groups.add(group_id)
                    data.append(group_check_logs[group_id])

                group_check_logs[group_id].content.append(check_log)

        return data

    def add_check_log_for_job(self, job_id: JobID, check_log_arguments: CheckLogArguments) -> None:
        group_id = None

        if check_log_arguments.group:
            group = check_log_arguments.group
            group_id, group_is_created = self.repo.prepare_group_check_log(
                job_id=job_id,
                title=check_log_arguments.group.title,
                message=group.success_msg if check_log_arguments.result else group.fail_msg,
                result=check_log_arguments.result,
                severity=check_log_arguments.severity,
            )

            if not group_is_created:
                group_check_log_result = aggregate_check_logs_results_for_group(
                    check_log_results=self.repo.get_check_log_results_for_group(group_id=group_id)
                )

                self.repo.update_group_check_log(
                    group_id=group_id,
                    message=group.success_msg if group_check_log_result.result else group.fail_msg,
                    result=group_check_log_result.result,
                    severity=group_check_log_result.severity,
                )

        self.repo.create_check_log(
            job_id=job_id,
            group_id=group_id,
            title=check_log_arguments.title,
            message=check_log_arguments.success_msg if check_log_arguments.result else check_log_arguments.fail_msg,
            result=check_log_arguments.result,
            severity=check_log_arguments.severity,
        )

    def add_log_storage_for_check_log(self, job_id: JobID) -> tuple[LogStorageID, IsCreated]:
        return self.repo.prepare_log_storage_for_check(job_id=job_id)

    def finish_updating_check_logs_for_job(self, job_id: JobID) -> None:
        content = self.retrieve_check_logs_content_for_job(job_id=job_id)

        if not content:
            return

        self.repo.update_log_storage_content_for_job(job_id=job_id, content=content)
        self.repo.clear_check_logs_for_job(job_id=job_id)
