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
from cm.models import JobLog, TaskLog
from core.action import TaskRunnerEnvironment
from core.action.job.operations import is_terminatable_status
from core.action.types import ExecutionStatus
from core.object.types import FullSelectorEntry
from core.object.utils import SELECTOR_OBJECT_ORDER, order_selector
from drf_spectacular.utils import extend_schema_field
from rest_framework.fields import CharField, ChoiceField, DateTimeField, IntegerField, SerializerMethodField
from rest_framework.serializers import ModelSerializer

from api_v2.generic.action.serializers import ActionNameSerializer


class TaskObjectsFieldSerializer(EmptySerializer):
    id = IntegerField()
    name = CharField()
    type = ChoiceField(choices=tuple((type_, type_) for type_ in SELECTOR_OBJECT_ORDER))


class TaskGroupTerminateSerializer(EmptySerializer):
    group = CharField(allow_blank=False, help_text="Internal name of group to terminate.")


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
    name = CharField()
    display_name = CharField()
    is_terminatable = SerializerMethodField()
    action = ActionNameSerializer(read_only=True, allow_null=True)
    objects = SerializerMethodField()
    start_time = DateTimeField(source="start_date", allow_null=True, read_only=True)
    end_time = DateTimeField(source="finish_date", allow_null=True, read_only=True)
    description = CharField(allow_null=True, default="")
    execution_environment = SerializerMethodField()

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
            "execution_environment",
        )

    @staticmethod
    def get_is_terminatable(obj: TaskLog) -> bool:
        return is_terminatable_status(ExecutionStatus(obj.status))

    @staticmethod
    @extend_schema_field(field=TaskObjectsFieldSerializer(many=True), component_name="TaskObjectsField")
    def get_objects(obj: TaskLog) -> list[FullSelectorEntry]:
        return order_selector(selector=obj.selector)

    @staticmethod
    @extend_schema_field(
        field=ChoiceField(choices=tuple((env.value, env.value) for env in TaskRunnerEnvironment), allow_null=True)
    )
    def get_execution_environment(obj: TaskLog) -> str | None:
        # environment is known only after the task is queued, see `use_cases.job.scheduler.queue_task`
        return (obj.executor or {}).get("environment")


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
            "execution_environment",
        )
