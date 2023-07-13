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

from api_v2.task.serializers import JobListSerializer, TaskRetrieveByJobSerializer
from cm.models import JobLog, LogStorage
from rest_framework.fields import SerializerMethodField


class JobRetrieveSerializer(JobListSerializer):
    parent_task = TaskRetrieveByJobSerializer(source="task")
    log_files = SerializerMethodField()

    class Meta:
        model = JobLog
        fields = (
            "id",
            "name",
            "display_name",
            "parent_task",
            "status",
            "start_date",
            "finish_date",
            "duration",
            "task_id",
            "log_files",
        )

    def get_log_files(self, obj: JobLog) -> list[dict[str, str]]:
        logs = []
        for log_storage in LogStorage.objects.filter(job=obj):
            logs.append(
                {
                    "name": log_storage.name,
                    "type": log_storage.type,
                    "format": log_storage.format,
                    "id": log_storage.pk,
                },
            )

        return logs
