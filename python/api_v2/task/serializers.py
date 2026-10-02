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
from core.spec.keys import ensure_full_key, full_key_to_level_keys
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


def spec_key_to_group_name(spec_key: str) -> str | None:
    """
    Return the name of the group a job with given spec key belongs to (its direct parent level).

    Root-level jobs and legacy jobs (empty spec key) don't belong to any group.
    """

    parent_levels = full_key_to_level_keys(ensure_full_key(spec_key))[:-1]

    if not parent_levels:
        return None

    return parent_levels[-1]


class TaskObjectsFieldSerializer(EmptySerializer):
    id = IntegerField()
    name = CharField()
    type = ChoiceField(choices=tuple((v, v) for v in OBJECT_ORDER))


class TaskGroupTerminateSerializer(EmptySerializer):
    group = CharField(allow_blank=False, help_text="Internal name of group to terminate.")


class JobListSerializer(ModelSerializer):
    is_terminatable = SerializerMethodField()
    group = SerializerMethodField()
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
            "group",
        )

    @staticmethod
    def get_is_terminatable(obj: JobLog) -> bool:
        return obj.allow_to_terminate

    @staticmethod
    def get_group(obj: JobLog) -> str | None:
        return spec_key_to_group_name(obj.spec_key)


class TaskSerializer(ModelSerializer):
    name = CharField()
    display_name = CharField()
    is_terminatable = SerializerMethodField()
    action = ActionNameSerializer(read_only=True, allow_null=True)
    objects = SerializerMethodField()
    start_time = DateTimeField(source="start_date", allow_null=True, read_only=True)
    end_time = DateTimeField(source="finish_date", allow_null=True, read_only=True)
    description = CharField(allow_null=True, default="")

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
            "description",
        )

    @staticmethod
    def get_is_terminatable(obj: TaskLog) -> bool:
        allow_to_terminate = obj.action.allow_to_terminate if obj.action else False
        is_active_status = obj.status in {JobStatus.CREATED, JobStatus.RUNNING}

        return allow_to_terminate and is_active_status

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
