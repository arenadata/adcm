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

from api_v2.action.serializers import ActionNameSerializer
from cm.models import Action, JobLog, JobStatus, SubAction, TaskLog
from rest_framework.fields import (
    CharField,
    DateTimeField,
    DurationField,
    SerializerMethodField,
)
from rest_framework.serializers import ModelSerializer


class JobListSerializer(ModelSerializer):
    name = SerializerMethodField()
    display_name = SerializerMethodField()
    is_terminatable = SerializerMethodField()
    start_time = DateTimeField(source="start_date")
    end_time = DateTimeField(source="finish_date")
    duration = DurationField()

    class Meta:
        model = JobLog
        fields = (
            "id",
            "name",
            "display_name",
            "status",
            "start_time",
            "end_time",
            "duration",
            "is_terminatable",
        )

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

    @staticmethod
    def get_is_terminatable(obj: JobLog):
        if obj.sub_action is None:
            return False

        return obj.sub_action.allowed_to_terminate


class TaskSerializer(ModelSerializer):
    name = CharField(source="action.name", allow_null=True)
    display_name = CharField(source="action.display_name", allow_null=True)
    is_terminatable = SerializerMethodField()
    duration = DurationField()
    action = ActionNameSerializer(read_only=True, allow_null=True)
    objects = SerializerMethodField()
    start_time = DateTimeField(source="start_date")
    end_time = DateTimeField(source="finish_date")

    class Meta:
        model = TaskLog
        fields = (
            "id",
            "name",
            "display_name",
            "action",
            "status",
            "start_time",
            "end_time",
            "duration",
            "is_terminatable",
            "child_jobs",
            "objects",
        )

    @staticmethod
    def get_is_terminatable(obj: TaskLog):
        if obj.action:
            allow_to_terminate = obj.action.allow_to_terminate
        else:
            allow_to_terminate = False

        if allow_to_terminate and obj.status in {JobStatus.CREATED, JobStatus.RUNNING}:
            return True

        return False

    @staticmethod
    def get_objects(obj: TaskLog) -> list[dict[str, int | str]]:
        return [{"type": k, **v} for k, v in obj.selector.items()]


class TaskListSerializer(TaskSerializer):
    child_jobs = SerializerMethodField()

    class Meta:
        model = TaskLog
        fields = (
            *TaskSerializer.Meta.fields,
            "child_jobs",
        )

    @staticmethod
    def get_child_jobs(obj: TaskLog) -> list:
        return JobListSerializer(instance=obj.joblog_set.order_by("pk"), many=True, read_only=True).data


class TaskRetrieveByJobSerializer(TaskSerializer):
    action = ActionNameSerializer(read_only=True, allow_null=True)
    start_time = DateTimeField(source="start_date")
    end_time = DateTimeField(source="finish_date")
    duration = DurationField()

    class Meta:
        model = TaskLog
        fields = (
            "id",
            "name",
            "display_name",
            "action",
            "status",
            "start_time",
            "end_time",
            "duration",
            "objects",
            "is_terminatable",
        )
