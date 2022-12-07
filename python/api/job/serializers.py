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

import json
from pathlib import Path

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
from cm.ansible_plugin import get_check_log
from cm.errors import AdcmEx
from cm.job import start_task
from cm.models import JobLog, JobStatus, LogStorage, TaskLog


class JobShortSerializer(HyperlinkedModelSerializer):
    display_name = SerializerMethodField()

    class Meta:
        model = JobLog
        fields = ("id", "display_name", "status", "start_date", "finish_date", "url")
        extra_kwargs = {"url": {"lookup_url_kwarg": "job_pk"}}

    @staticmethod
    def get_display_name(obj: JobLog) -> str | None:
        if obj.sub_action:
            return obj.sub_action.display_name
        elif obj.action:
            return obj.action.display_name
        else:
            return None


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
    restart = HyperlinkedIdentityField(view_name="tasklog-restart", lookup_url_kwarg="task_pk")
    cancel = HyperlinkedIdentityField(view_name="tasklog-cancel", lookup_url_kwarg="task_pk")
    download = HyperlinkedIdentityField(view_name="tasklog-download", lookup_url_kwarg="task_pk")

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
        read_only_fields = ("object_id", "status", "start_date", "finish_date")
        extra_kwargs = {"url": {"lookup_url_kwarg": "task_pk"}}

    def get_action_url(self, obj: TaskLog) -> str | None:
        if not obj.action_id:
            return None

        return reverse("action-detail", kwargs={"action_pk": obj.action_id}, request=self.context["request"])

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


class RunTaskRetrieveSerializer(TaskRetrieveSerializer):
    def create(self, validated_data):
        obj = start_task(
            validated_data.get("action"),
            validated_data.get("task_object"),
            validated_data.get("config", {}),
            validated_data.get("attr", {}),
            validated_data.get("hc", []),
            validated_data.get("hosts", []),
            validated_data.get("verbose", False),
        )
        obj.jobs = JobLog.objects.filter(task_id=obj.id)

        return obj


class JobSerializer(HyperlinkedModelSerializer):
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


class JobRetrieveSerializer(HyperlinkedModelSerializer):
    action = ActionJobSerializer()
    display_name = SerializerMethodField()
    objects = SerializerMethodField()
    selector = JSONField()
    log_dir = SerializerMethodField()
    log_files = SerializerMethodField()
    action_url = SerializerMethodField()
    task_url = HyperlinkedIdentityField(
        view_name="tasklog-detail",
        lookup_url_kwarg="task_pk",
    )

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
        )
        extra_kwargs = {"url": {"lookup_url_kwarg": "job_pk"}}

    @staticmethod
    def get_objects(obj: JobLog) -> list | None:
        objects = [{"type": k, **v} for k, v in obj.task.selector.items()]

        return objects

    @staticmethod
    def get_display_name(obj: JobLog) -> str | None:
        if obj.sub_action:
            return obj.sub_action.display_name
        elif obj.action:
            return obj.action.display_name
        else:
            return None

    def get_action_url(self, obj: JobLog) -> str | None:
        if not obj.action_id:
            return None

        return reverse("action-detail", kwargs={"action_pk": obj.action_id}, request=self.context["request"])

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
                        "joblog-detail",
                        kwargs={"job_pk": obj.pk, "log_pk": log_storage.pk},
                        request=self.context["request"],
                    ),
                    "download_url": reverse(
                        "joblog-download",
                        kwargs={"job_pk": obj.pk, "log_pk": log_storage.pk},
                        request=self.context["request"],
                    ),
                }
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
            with open(path_file, "r", encoding=settings.ENCODING_UTF_8) as f:
                content = f.read()
        except FileNotFoundError as e:
            msg = f'File "{obj.name}-{obj.type}.{obj.format}" not found'

            raise AdcmEx("LOG_NOT_FOUND", msg) from e

        return content

    def get_content(self, obj: LogStorage) -> str:
        if obj.type in {"stdout", "stderr"}:
            if obj.body is None:
                obj.body = self._get_ansible_content(obj)
        elif obj.type == "check":
            if obj.body is None:
                obj.body = get_check_log(obj.job_id)
            if isinstance(obj.body, str):
                obj.body = json.loads(obj.body)
        elif obj.type == "custom":
            if obj.format == "json" and isinstance(obj.body, str):
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
            "joblog-detail",
            kwargs={"job_pk": obj.job_id, "log_pk": obj.id},
            request=self.context["request"],
        )
