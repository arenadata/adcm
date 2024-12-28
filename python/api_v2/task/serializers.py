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

from adcm.serializers import EmptySerializer
from cm.models import JobLog, JobStatus, TaskLog
from drf_spectacular.utils import extend_schema_field
from rest_framework.fields import CharField, ChoiceField, DateTimeField, IntegerField, SerializerMethodField
from rest_framework.serializers import ModelSerializer

from api_v2.generic.action.serializers import ActionNameSerializer

OBJECT_ORDER = {
    "adcm": 0,
    "cluster": 1,
    "service": 2,
    "component": 3,
    "provider": 4,
    "host": 5,
    "action_host_group": 6,
}


class TaskObjectsFieldSerializer(EmptySerializer):
    id = IntegerField()
    name = CharField()
    type = ChoiceField(choices=tuple((v, v) for v in OBJECT_ORDER))


class JobListSerializer(ModelSerializer):
    is_terminatable = SerializerMethodField()
    start_time = DateTimeField(source="start_date", allow_null=True, read_only=True)
    end_time = DateTimeField(source="finish_date", allow_null=True, read_only=True)

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

    @staticmethod
    def get_is_terminatable(obj: JobLog) -> bool:
        return obj.allow_to_terminate


class TaskSerializer(ModelSerializer):
    name = CharField(source="action.name", allow_null=True)
    display_name = CharField(source="action.display_name", allow_null=True)
    is_terminatable = SerializerMethodField()
    action = ActionNameSerializer(read_only=True, allow_null=True)
    objects = SerializerMethodField()
    start_time = DateTimeField(source="start_date", allow_null=True, read_only=True)
    end_time = DateTimeField(source="finish_date", allow_null=True, read_only=True)

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
    def get_is_terminatable(obj: TaskLog) -> bool:
        allow_to_terminate = obj.action.allow_to_terminate if obj.action else False

        if allow_to_terminate and obj.status in {JobStatus.CREATED, JobStatus.RUNNING}:
            return True

        return False

    @staticmethod
    @extend_schema_field(field=TaskObjectsFieldSerializer(many=True), component_name="TaskObjectsField")
    def get_objects(obj: TaskLog) -> list[dict[str, int | str]]:
        return [{"type": k, **v} for k, v in sorted(obj.selector.items(), key=lambda k: OBJECT_ORDER[k[0]])]


class TaskListSerializer(TaskSerializer):
    child_jobs = SerializerMethodField()

    class Meta:
        model = TaskLog
        fields = (
            *TaskSerializer.Meta.fields,
            "child_jobs",
        )

    @staticmethod
    @extend_schema_field(field=JobListSerializer(many=True))
    def get_child_jobs(obj: TaskLog) -> list:
        return JobListSerializer(instance=obj.joblog_set.order_by("pk"), many=True, read_only=True).data


class TaskRetrieveByJobSerializer(TaskSerializer):
    action = ActionNameSerializer(read_only=True, allow_null=True)
    start_time = DateTimeField(source="start_date", allow_null=True, read_only=True)
    end_time = DateTimeField(source="finish_date", allow_null=True, read_only=True)

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
