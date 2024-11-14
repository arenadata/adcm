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
import io
import re
import tarfile

from adcm.permissions import check_custom_perm, get_object_for_user
from audit.utils import audit
from cm.errors import AdcmEx
from cm.models import ActionType, JobLog, JobStatus, LogStorage, TaskLog
from cm.services.job.run import restart_task, run_task
from cm.utils import str_remove_non_alnum
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django_filters.rest_framework import (
    CharFilter,
    DateTimeFilter,
    DjangoFilterBackend,
    FilterSet,
    NumberFilter,
    OrderingFilter,
)
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from api.base_view import GenericUIViewSet
from api.job.serializers import (
    JobRetrieveSerializer,
    JobSerializer,
    LogStorageRetrieveSerializer,
    LogStorageSerializer,
    TaskRetrieveSerializer,
    TaskSerializer,
)
from api.rbac.viewsets import DjangoOnlyObjectPermissions

VIEW_TASKLOG_PERMISSION = "cm.view_tasklog"
VIEW_JOBLOG_PERMISSION = "cm.view_joblog"
VIEW_LOGSTORAGE_PERMISSION = "cm.view_logstorage"


def get_task_download_archive_name(task: TaskLog) -> str:
    archive_name = f"{task.pk}.tar.gz"

    if not task.action:
        return archive_name

    action_display_name = str_remove_non_alnum(value=task.action.display_name) or str_remove_non_alnum(
        value=task.action.name,
    )
    if action_display_name:
        archive_name = f"{action_display_name}_{archive_name}"

    if task.object_type.name in {
        "adcm",
        "cluster",
        "service",
        "component",
        "host provider",
    }:
        action_prototype_display_name = str_remove_non_alnum(
            value=task.action.prototype.display_name,
        ) or str_remove_non_alnum(value=task.action.prototype.name)
        if action_prototype_display_name:
            archive_name = f"{action_prototype_display_name}_{archive_name}"

    if not task.task_object:
        return archive_name

    obj_name = None
    if task.object_type.name == "cluster":
        obj_name = task.task_object.name
    elif task.object_type.name == "service" or task.object_type.name == "component":
        obj_name = task.task_object.cluster.name
    elif task.object_type.name == "host provider":
        obj_name = task.task_object.name
    elif task.object_type.name == "host":
        obj_name = task.task_object.fqdn

    if obj_name:
        archive_name = f"{str_remove_non_alnum(value=obj_name)}_{archive_name}"

    return archive_name


def get_task_download_archive_file_handler(task: TaskLog) -> io.BytesIO:
    jobs = JobLog.objects.filter(task=task)

    if task.action and task.action.type == ActionType.JOB:
        task_dir_name_suffix = str_remove_non_alnum(value=task.action.display_name) or str_remove_non_alnum(
            value=task.action.name,
        )
    else:
        task_dir_name_suffix = None

    file_handler = io.BytesIO()
    with tarfile.open(fileobj=file_handler, mode="w:gz") as tar_file:
        for job in jobs:
            if task_dir_name_suffix is None:
                dir_name_suffix = str_remove_non_alnum(value=job.display_name or "") or str_remove_non_alnum(
                    value=job.name
                )
            else:
                dir_name_suffix = task_dir_name_suffix

            directory = Path(settings.RUN_DIR, str(job.pk))
            if directory.is_dir():
                files = [item for item in Path(settings.RUN_DIR, str(job.pk)).iterdir() if item.is_file()]
                for log_file in files:
                    tarinfo = tarfile.TarInfo(f'{f"{job.pk}-{dir_name_suffix}".strip("-")}/{log_file.name}')
                    tarinfo.size = log_file.stat().st_size
                    tar_file.addfile(tarinfo=tarinfo, fileobj=io.BytesIO(log_file.read_bytes()))
            else:
                log_storages = LogStorage.objects.filter(job=job, type__in={"stdout", "stderr"})
                for log_storage in log_storages:
                    tarinfo = tarfile.TarInfo(
                        f'{f"{job.pk}-{dir_name_suffix}".strip("-")}' f"/{log_storage.name}-{log_storage.type}.txt",
                    )
                    # using `or ""` here to avoid passing None to `bytes`
                    body = io.BytesIO(bytes(log_storage.body or "", settings.ENCODING_UTF_8))
                    tarinfo.size = body.getbuffer().nbytes
                    tar_file.addfile(tarinfo=tarinfo, fileobj=body)

    return file_handler


class JobFilter(FilterSet):
    action_id = NumberFilter(field_name="action_id", method="filter_by_action_id")
    task_id = NumberFilter(field_name="task_id")
    pid = NumberFilter(field_name="pid")
    status = CharFilter(field_name="status")
    start_date = DateTimeFilter(field_name="start_date")
    finish_date = DateTimeFilter(field_name="finish_date")
    ordering = OrderingFilter(
        fields={"status": "status", "start_date": "start_date", "finish_date": "finish_date"}, label="ordering"
    )

    def filter_by_action_id(self, queryset, name, value):  # noqa: ARG002
        return queryset.filter(task__action_id=value)


class JobViewSet(PermissionListMixin, ListModelMixin, RetrieveModelMixin, GenericUIViewSet):
    queryset = JobLog.objects.select_related("task__action").all()
    serializer_class = JobSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = JobFilter
    ordering_fields = ("status", "start_date", "finish_date")
    ordering = ["-id"]
    permission_required = ["cm.view_joblog"]
    lookup_url_kwarg = "job_pk"

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if not self.request.user.is_superuser:
            # NOT superuser shouldn't have access to ADCM tasks
            queryset = queryset.exclude(task__object_type=ContentType.objects.get(app_label="cm", model="adcm"))
        return queryset

    def get_permissions(self):
        permission_classes = (DjangoModelPermissions,) if self.action == "list" else (DjangoOnlyObjectPermissions,)
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.is_for_ui() or self.action in ("retrieve", "cancel"):
            return JobRetrieveSerializer

        return super().get_serializer_class()

    @audit
    @action(methods=["put"], detail=True)
    def cancel(self, request: Request, job_pk: int) -> Response:
        job: JobLog = get_object_for_user(request.user, VIEW_JOBLOG_PERMISSION, JobLog, id=job_pk)
        check_custom_perm(request.user, "change", JobLog, job_pk)

        job.cancel()

        return Response(status=HTTP_200_OK)


class TaskViewSet(PermissionListMixin, ListModelMixin, RetrieveModelMixin, GenericUIViewSet):
    queryset = TaskLog.objects.select_related("action").all()
    serializer_class = TaskSerializer
    filterset_fields = ("action_id", "pid", "status", "start_date", "finish_date")
    ordering_fields = ("status", "start_date", "finish_date")
    ordering = ["-id"]
    permission_required = [VIEW_TASKLOG_PERMISSION]
    lookup_url_kwarg = "task_pk"

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if not self.request.user.is_superuser:
            # NOT superuser shouldn't have access to ADCM tasks
            queryset = queryset.exclude(object_type=ContentType.objects.get(app_label="cm", model="adcm"))
        return queryset

    def get_serializer_class(self):
        if self.is_for_ui() or self.action in {"retrieve", "restart", "cancel", "download"}:
            return TaskRetrieveSerializer

        return super().get_serializer_class()

    @audit
    @action(methods=["put"], detail=True)
    def restart(self, request: Request, task_pk: int) -> Response:
        task = get_object_for_user(request.user, VIEW_TASKLOG_PERMISSION, TaskLog, id=task_pk)
        check_custom_perm(request.user, "change", TaskLog, task)

        if task.status in (JobStatus.CREATED, JobStatus.RUNNING):
            raise AdcmEx(code="TASK_ERROR", msg=f"task #{task.pk} is running")

        if task.status == JobStatus.SUCCESS:
            run_task(task)
        elif task.status in (JobStatus.FAILED, JobStatus.ABORTED):
            restart_task(task)
        else:
            raise AdcmEx(code="TASK_ERROR", msg=f"task #{task.pk} has unexpected status: {task.status}")

        return Response(status=HTTP_200_OK)

    @audit
    @action(methods=["put"], detail=True)
    def cancel(self, request: Request, task_pk: int) -> Response:
        task = get_object_for_user(request.user, VIEW_TASKLOG_PERMISSION, TaskLog, id=task_pk)
        check_custom_perm(request.user, "change", TaskLog, task)
        task.cancel()

        return Response(status=HTTP_200_OK)

    @audit
    @action(methods=["get"], detail=True)
    def download(self, request: Request, task_pk: int) -> Response:
        task = get_object_for_user(request.user, VIEW_TASKLOG_PERMISSION, TaskLog, id=task_pk)
        response = HttpResponse(
            content=get_task_download_archive_file_handler(task=task).getvalue(),
            content_type="application/tar+gzip",
        )
        response["Content-Disposition"] = f'attachment; filename="{get_task_download_archive_name(task=task)}"'

        return response


class LogStorageViewSet(PermissionListMixin, ListModelMixin, RetrieveModelMixin, GenericUIViewSet):
    queryset = LogStorage.objects.all()
    serializer_class = LogStorageSerializer
    filterset_fields = ("name", "type", "format")
    ordering_fields = ("id", "name")
    permission_required = ["cm.view_logstorage"]
    lookup_url_kwarg = "log_pk"
    ordering = ["id"]

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if "job_pk" in self.kwargs:
            queryset = queryset.filter(job_id=self.kwargs["job_pk"])

        return queryset

    def get_serializer_class(self):
        if self.is_for_ui() or self.action == "retrieve":
            return LogStorageRetrieveSerializer

        return super().get_serializer_class()

    @audit
    @action(methods=["get"], detail=True)
    def download(self, request: Request, job_pk: int, log_pk: int):
        # self is necessary for audit
        log_storage = get_object_for_user(
            user=request.user, perms=VIEW_LOGSTORAGE_PERMISSION, klass=LogStorage, id=log_pk, job__id=job_pk
        )
        if log_storage.type in {"stdout", "stderr"}:
            filename = f"{job_pk}-{log_storage.name}-{log_storage.type}.{log_storage.format}"
        else:
            filename = f"{job_pk}-{log_storage.name}.{log_storage.format}"

        filename = re.sub(r"\s+", "_", filename)
        mime_type = "text/plain" if log_storage.format == "txt" else "application/json"

        if log_storage.body is None:
            file_path = Path(
                settings.RUN_DIR,
                f"{job_pk}",
                f"{log_storage.name}-{log_storage.type}.{log_storage.format}",
            )
            if Path.is_file(file_path):
                with open(file_path, encoding=settings.ENCODING_UTF_8) as f:
                    body = f.read()
                    length = len(body)
            else:
                body = ""
                length = 0
        else:
            body = log_storage.body
            length = len(body)

        response = HttpResponse(body)
        response["Content-Type"] = mime_type
        response["Content-Length"] = length
        response["Content-Encoding"] = settings.ENCODING_UTF_8
        response["Content-Disposition"] = f"attachment; filename={filename}"

        return response
