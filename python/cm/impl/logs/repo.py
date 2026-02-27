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

from dataclasses import asdict
import json

from core import logs
from core.types import CheckLogID, GroupCheckLogID, IsCreated, JobID, LogStorageID

from cm.models import CheckLog, GroupCheckLog, LogStorage


class LogsRepo(logs.LogsRepoI):
    def get_check_logs_by_job_id(self, job_id: JobID) -> list[tuple[GroupCheckLogID | None, logs.CheckLogContent]]:
        return [
            (
                cl["group_id"],
                logs.CheckLogContent(
                    type="check", title=cl["title"], message=cl["message"], result=cl["result"], severity=cl["severity"]
                ),
            )
            for cl in CheckLog.objects.filter(job_id=job_id)
            .values("title", "message", "result", "severity", "group_id")
            .order_by("id")
        ]

    def get_group_check_logs_by_job_id(self, job_id: JobID) -> dict[GroupCheckLogID, logs.GroupCheckLogContent]:
        return {
            gcl["id"]: logs.GroupCheckLogContent(
                title=gcl["title"],
                type="group",
                message=gcl["message"],
                result=gcl["result"],
                severity=gcl["severity"],
                content=[],
            )
            for gcl in GroupCheckLog.objects.filter(job_id=job_id).values(
                "id", "title", "message", "result", "severity"
            )
        }

    def update_log_storage_content_for_job(
        self, job_id: JobID, content: list[logs.CheckLogContent | logs.GroupCheckLogContent]
    ):
        LogStorage.objects.filter(job=job_id, type="check").update(body=json.dumps([asdict(item) for item in content]))

    def clear_check_logs_for_job(self, job_id: JobID) -> None:
        GroupCheckLog.objects.filter(job_id=job_id).delete()
        CheckLog.objects.filter(job_id=job_id).delete()

    def prepare_log_storage_for_check(self, job_id: JobID) -> tuple[LogStorageID, IsCreated]:
        log_storage, is_created = LogStorage.objects.get_or_create(
            job_id=job_id, name="ansible", type="check", format="json"
        )
        return log_storage.pk, is_created

    def prepare_group_check_log(
        self, job_id: JobID, title: str, message: str, result: bool, severity: logs.Severity
    ) -> tuple[GroupCheckLogID, IsCreated]:
        group, is_created = GroupCheckLog.objects.get_or_create(
            job_id=job_id, title=title, message=message, result=result, severity=severity
        )

        return group.pk, is_created

    def create_check_log(
        self,
        job_id: JobID,
        group_id: GroupCheckLogID | None,
        title: str,
        message: str,
        result: bool,
        severity: logs.Severity,
    ) -> CheckLogID:
        check_log = CheckLog.objects.create(
            job_id=job_id, group_id=group_id, title=title, message=message, result=result, severity=severity
        )
        return check_log.pk

    def update_group_check_log(
        self, group_id: GroupCheckLogID, message: str, result: bool, severity: logs.Severity
    ) -> None:
        GroupCheckLog.objects.filter(id=group_id).update(message=message, result=result, severity=severity)

    def get_check_log_results_for_group(self, group_id: GroupCheckLogID) -> list[logs.CheckLogResult]:
        return [
            logs.CheckLogResult(**check_log_result)
            for check_log_result in CheckLog.objects.filter(group_id=group_id).values("result", "severity")
        ]
