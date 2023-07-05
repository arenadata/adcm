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

from datetime import timedelta

from cm.models import Action, JobLog, JobStatus, LogStorage, SubAction, TaskLog
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer


class TaskRetrieveByJobSerializer(ModelSerializer):
    objects = SerializerMethodField()
    terminatable = SerializerMethodField()
    object_type = SerializerMethodField()
    duration = SerializerMethodField()

    class Meta:
        model = TaskLog
        fields = (
            "id",
            "status",
            "start_date",
            "finish_date",
            "duration",
            "objects",
            "terminatable",
            "object_type",
        )

    @staticmethod
    def get_objects(obj: TaskLog) -> list:
        objects = [{"type": k, **v} for k, v in obj.selector.items()]

        return objects

    @staticmethod
    def get_terminatable(obj: TaskLog):
        if obj.action:
            allow_to_terminate = obj.action.allow_to_terminate
        else:
            allow_to_terminate = False

        if allow_to_terminate and obj.status in {JobStatus.CREATED, JobStatus.RUNNING}:
            return True

        return False

    @staticmethod
    def get_object_type(obj: TaskLog):
        if obj.action:
            return obj.action.prototype.type

        return None

    @staticmethod
    def get_duration(obj: JobLog) -> timedelta:
        return obj.finish_date - obj.start_date


class JobListSerializer(ModelSerializer):
    duration = SerializerMethodField()
    name = SerializerMethodField()
    display_name = SerializerMethodField()

    class Meta:
        model = JobLog
        fields = (
            "id",
            "name",
            "display_name",
            "status",
            "start_date",
            "finish_date",
            "duration",
        )

    @staticmethod
    def get_duration(obj: JobLog) -> timedelta:
        return obj.finish_date - obj.start_date

    @classmethod
    def get_display_name(cls, obj: JobLog) -> str | None:
        job_action = cls._get_job_action_obj(obj)
        return job_action.display_name if job_action else None

    @classmethod
    def get_name(cls, obj: JobLog) -> str | None:
        job_action = cls._get_job_action_obj(obj)
        return job_action.name if job_action else None

    @staticmethod
    def _get_job_action_obj(obj: JobLog) -> Action | SubAction | None:
        if obj.sub_action:
            return obj.sub_action
        elif obj.action:
            return obj.action
        else:
            return None


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
