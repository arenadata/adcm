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

from pathlib import Path
import json

from ansible_plugin.utils import get_checklogs_data_by_job_id
from cm.models import JobLog, JobStatus, LogStorage, TaskLog
from cm.services.job.action import ActionRunPayload, run_action
from django.conf import settings
from rest_framework.reverse import reverse
from rest_framework.serializers import (
    HyperlinkedIdentityField,
    HyperlinkedModelSerializer,
    JSONField,
    SerializerMethodField,
)

from api.action.serializers import ActionJobSerializer
from api.concern.serializers import ConcernItemSerializer


class JobShortSerializer(HyperlinkedModelSerializer):
    display_name = SerializerMethodField()
    terminatable = SerializerMethodField()

    class Meta:
        model = JobLog
        fields = ("id", "display_name", "status", "terminatable", "start_date", "finish_date", "url")
        extra_kwargs = {"url": {"lookup_url_kwarg": "job_pk"}}

    @staticmethod
    def get_display_name(obj: JobLog) -> str | None:
        return obj.display_name

    @staticmethod
    def get_terminatable(obj: JobLog):
        return obj.allow_to_terminate


class TaskSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = TaskLog
        fields = (
            "id",
            "pid",
            "object_id",
            "action_id",
            "status",
            "start_date",
            "finish_date",
            "url",
        )
        extra_kwargs = {"url": {"lookup_url_kwarg": "task_pk"}}


class TaskRetrieveSerializer(HyperlinkedModelSerializer):
    action_url = SerializerMethodField()
    action = ActionJobSerializer(read_only=True)
    objects = SerializerMethodField()
    jobs = JobShortSerializer(many=True, source="joblog_set", read_only=True)
    terminatable = SerializerMethodField()
    object_type = SerializerMethodField()
    lock = ConcernItemSerializer(read_only=True)
    hc = JSONField(required=False)
    restart = HyperlinkedIdentityField(view_name="v1:tasklog-restart", lookup_url_kwarg="task_pk")
    cancel = HyperlinkedIdentityField(view_name="v1:tasklog-cancel", lookup_url_kwarg="task_pk")
    download = HyperlinkedIdentityField(view_name="v1:tasklog-download", lookup_url_kwarg="task_pk")

    class Meta:
        model = TaskLog
        fields = (
            *TaskSerializer.Meta.fields,
            "selector",
            "config",
            "attr",
            "hosts",
            "verbose",
            "action_url",
            "action",
            "objects",
            "jobs",
            "terminatable",
            "object_type",
            "lock",
            "hc",
            "restart",
            "cancel",
            "download",
        )
        read_only_fields = ("object_id", "status", "start_date", "finish_date", "pid", "selector")
        extra_kwargs = {"url": {"lookup_url_kwarg": "task_pk"}}

    def get_action_url(self, obj: TaskLog) -> str | None:
        if not obj.action_id:
            return None

        return reverse(
            viewname="v1:action-detail", kwargs={"action_pk": obj.action_id}, request=self.context["request"]
        )

    @staticmethod
    def get_objects(obj: TaskLog) -> list:
        return [{"type": k, **v} for k, v in obj.selector.items()]

    @staticmethod
    def get_terminatable(obj: TaskLog):
        allow_to_terminate = obj.action.allow_to_terminate if obj.action else False

        if allow_to_terminate and obj.status in {JobStatus.CREATED, JobStatus.RUNNING}:
            return True

        return False

    @staticmethod
    def get_object_type(obj: TaskLog):
        if obj.action:
            return obj.action.prototype.type

        return None


class RunTaskRetrieveSerializer(TaskRetrieveSerializer):
    def create(self, validated_data):
        obj = run_action(
            action=validated_data.get("action"),
            obj=validated_data.get("task_object"),
            payload=ActionRunPayload(
                conf=validated_data.get("config", {}),
                attr=validated_data.get("attr", {}),
                hostcomponent=validated_data.get("hc", []),
                verbose=validated_data.get("verbose", False),
            ),
        )
        obj.jobs = JobLog.objects.filter(task_id=obj.id)

        return obj


class JobSerializer(HyperlinkedModelSerializer):
    action_id = SerializerMethodField()
    sub_action_id = SerializerMethodField()

    class Meta:
        model = JobLog
        fields = (
            "id",
            "pid",
            "task_id",
            "action_id",
            "sub_action_id",
            "status",
            "start_date",
            "finish_date",
            "url",
        )
        extra_kwargs = {"url": {"lookup_url_kwarg": "job_pk"}}

    def get_action_id(self, obj: JobLog):
        try:
            return obj.action.id
        except AttributeError:
            return None

    def get_sub_action_id(self, _: JobLog):
        return None


class JobRetrieveSerializer(HyperlinkedModelSerializer):
    action_id = SerializerMethodField()
    sub_action_id = SerializerMethodField()
    action = ActionJobSerializer()
    selector = SerializerMethodField()
    objects = SerializerMethodField()
    log_dir = SerializerMethodField()
    log_files = SerializerMethodField()
    action_url = SerializerMethodField()
    task_url = HyperlinkedIdentityField(
        view_name="v1:tasklog-detail",
        lookup_url_kwarg="task_pk",
    )
    terminatable = SerializerMethodField()

    def get_selector(self, obj: JobLog):
        try:
            return obj.task.selector
        except AttributeError:
            return {}

    def get_action_id(self, obj: JobLog):
        try:
            return obj.task.action.id
        except AttributeError:
            return None

    def get_sub_action_id(self, _: JobLog):
        return None

    @staticmethod
    def get_terminatable(obj: JobLog):
        return obj.allow_to_terminate

    class Meta:
        model = JobLog
        fields = (
            *JobSerializer.Meta.fields,
            "action",
            "display_name",
            "objects",
            "selector",
            "log_dir",
            "log_files",
            "action_url",
            "task_url",
            "terminatable",
        )
        extra_kwargs = {"url": {"lookup_url_kwarg": "job_pk"}}

    @staticmethod
    def get_objects(obj: JobLog) -> list | None:
        return [{"type": k, **v} for k, v in obj.task.selector.items()]

    def get_action_url(self, obj: JobLog) -> str | None:
        if not obj.action:
            return None

        return reverse(
            viewname="v1:action-detail", kwargs={"action_pk": obj.action.id}, request=self.context["request"]
        )

    @staticmethod
    def get_log_dir(obj: JobLog) -> str:
        return str(Path(settings.RUN_DIR, str(obj.pk)))

    def get_log_files(self, obj: JobLog) -> list[dict[str, str]]:
        logs = []
        for log_storage in LogStorage.objects.filter(job=obj):
            logs.append(
                {
                    "name": log_storage.name,
                    "type": log_storage.type,
                    "format": log_storage.format,
                    "id": log_storage.pk,
                    "url": reverse(
                        "v1:logstorage-detail",
                        kwargs={"job_pk": obj.pk, "log_pk": log_storage.pk},
                        request=self.context["request"],
                    ),
                    "download_url": reverse(
                        "v1:logstorage-download",
                        kwargs={"job_pk": obj.pk, "log_pk": log_storage.pk},
                        request=self.context["request"],
                    ),
                },
            )

        return logs


class LogStorageRetrieveSerializer(HyperlinkedModelSerializer):
    content = SerializerMethodField()

    class Meta:
        model = LogStorage
        fields = (
            "id",
            "name",
            "type",
            "format",
            "content",
        )
        extra_kwargs = {"url": {"lookup_url_kwarg": "log_pk"}}

    @staticmethod
    def _get_ansible_content(obj):
        path_file = settings.RUN_DIR / f"{obj.job.id}" / f"{obj.name}-{obj.type}.{obj.format}"
        try:
            with open(path_file, encoding=settings.ENCODING_UTF_8) as f:
                content = f.read()
        except FileNotFoundError:
            content = ""

        return content

    def get_content(self, obj: LogStorage) -> str:
        if obj.type in {"stdout", "stderr"}:
            if obj.body is None:
                obj.body = self._get_ansible_content(obj)
        elif obj.type == "check":
            if obj.body is None:
                obj.body = get_checklogs_data_by_job_id(obj.job_id)
            if isinstance(obj.body, str):
                obj.body = json.loads(obj.body)
        elif obj.type == "custom" and obj.format == "json" and isinstance(obj.body, str):
            try:
                custom_content = json.loads(obj.body)
                obj.body = json.dumps(custom_content, indent=4)
            except json.JSONDecodeError:
                pass

        return obj.body


class LogStorageSerializer(LogStorageRetrieveSerializer):
    url = SerializerMethodField()

    class Meta:
        model = LogStorage
        fields = (*LogStorageRetrieveSerializer.Meta.fields, "url")

    def get_url(self, obj):
        return reverse(
            "v1:logstorage-detail",
            kwargs={"job_pk": obj.job_id, "log_pk": obj.id},
            request=self.context["request"],
        )
