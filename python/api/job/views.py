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

import io
import os
import re
import tarfile
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from guardian.mixins import PermissionListMixin
from rest_framework.permissions import DjangoModelPermissions, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND
from rest_framework.views import APIView

from adcm.utils import str_remove_non_alnum
from api.base_view import DetailView, GenericUIView, PaginatedView
from api.job.serializers import (
    JobListSerializer,
    JobSerializer,
    LogSerializer,
    LogStorageListSerializer,
    LogStorageSerializer,
    TaskListSerializer,
    TaskSerializer,
)
from api.utils import check_custom_perm, get_object_for_user
from audit.utils import audit
from cm.config import RUN_DIR
from cm.errors import AdcmEx
from cm.job import cancel_task, get_log, restart_task
from cm.models import ActionType, JobLog, LogStorage, TaskLog
from rbac.viewsets import DjangoOnlyObjectPermissions

VIEW_JOBLOG_PERMISSION = "cm.view_joblog"
VIEW_TASKLOG_PERMISSION = "cm.view_tasklog"


def download_log_file(request, job_id, log_id):
    job = JobLog.obj.get(id=job_id)
    log_storage = LogStorage.obj.get(id=log_id, job=job)

    if log_storage.type in ["stdout", "stderr"]:
        filename = f"{job.id}-{log_storage.name}-{log_storage.type}.{log_storage.format}"
    else:
        filename = f"{job.id}-{log_storage.name}.{log_storage.format}"

    filename = re.sub(r"\s+", "_", filename)
    if log_storage.format == "txt":
        mime_type = "text/plain"
    else:
        mime_type = "application/json"

    if log_storage.body is None:
        body = ""
        length = 0
    else:
        body = log_storage.body
        length = len(body)

    response = HttpResponse(body)
    response["Content-Type"] = mime_type
    response["Content-Length"] = length
    response["Content-Encoding"] = "UTF-8"
    response["Content-Disposition"] = f"attachment; filename={filename}"

    return response


def get_task_download_archive_name(task: TaskLog) -> str:
    archive_name = f"{task.pk}.tar.gz"

    if not task.action:
        return archive_name

    action_display_name = str_remove_non_alnum(
        value=task.action.display_name
    ) or str_remove_non_alnum(value=task.action.name)
    if action_display_name:
        archive_name = f"{action_display_name}_{archive_name}"

    if task.object_type.name in {"adcm", "cluster", "service", "component", "provider"}:
        action_prototype_display_name = str_remove_non_alnum(
            value=task.action.prototype.display_name
        ) or str_remove_non_alnum(value=task.action.prototype.name)
        if action_prototype_display_name:
            archive_name = f"{action_prototype_display_name}_{archive_name}"

    if not task.task_object:
        return archive_name

    obj_name = None
    if task.object_type.name == "cluster":
        obj_name = task.task_object.name
    elif task.object_type.name == "service":
        obj_name = task.task_object.cluster.name
    elif task.object_type.name == "component":
        obj_name = task.task_object.cluster.name
    elif task.object_type.name == "provider":
        obj_name = task.task_object.name
    elif task.object_type.name == "host":
        obj_name = task.task_object.fqdn

    if obj_name:
        archive_name = f"{str_remove_non_alnum(value=obj_name)}_{archive_name}"

    return archive_name


def get_task_download_archive_file_handler(task: TaskLog) -> io.BytesIO:
    jobs = JobLog.objects.filter(task=task)

    if task.action and task.action.type == ActionType.Job:
        dir_name_suffix = str_remove_non_alnum(
            value=task.action.display_name
        ) or str_remove_non_alnum(value=task.action.name)
    else:
        dir_name_suffix = None

    fh = io.BytesIO()
    with tarfile.open(fileobj=fh, mode="w:gz") as tar_file:
        for job in jobs:
            if dir_name_suffix is None:
                dir_name_suffix = str_remove_non_alnum(
                    value=job.sub_action.action.display_name
                ) or str_remove_non_alnum(value=job.sub_action.action.name)

            directory = Path(settings.RUN_DIR, str(job.pk))
            if directory.is_dir():
                for log_file in Path(settings.RUN_DIR, str(job.pk)).iterdir():
                    tarinfo = tarfile.TarInfo(f"{job.pk}-{dir_name_suffix}/{log_file.name}")
                    tarinfo.size = log_file.stat().st_size
                    tar_file.addfile(tarinfo=tarinfo, fileobj=io.BytesIO(log_file.read_bytes()))
            else:
                log_storages = LogStorage.objects.filter(job=job, type__in={"stdout", "stderr"})
                for log_storage in log_storages:
                    tarinfo = tarfile.TarInfo(
                        f"{job.pk}-{dir_name_suffix}/ansible-{log_storage.type}.txt"
                    )
                    body = io.BytesIO(bytes(log_storage.body, "utf-8"))
                    tarinfo.size = body.getbuffer().nbytes
                    tar_file.addfile(tarinfo=tarinfo, fileobj=body)

    return fh


class JobList(PermissionListMixin, PaginatedView):
    queryset = JobLog.objects.order_by("-id")
    serializer_class = JobListSerializer
    serializer_class_ui = JobSerializer
    filterset_fields = ("action_id", "task_id", "pid", "status", "start_date", "finish_date")
    ordering_fields = ("status", "start_date", "finish_date")
    permission_classes = (DjangoModelPermissions,)
    permission_required = [VIEW_JOBLOG_PERMISSION]

    def get_queryset(self, *args, **kwargs):
        if self.request.user.is_superuser:
            exclude_pks = []
        else:
            exclude_pks = JobLog.get_adcm_jobs_qs().values_list("pk", flat=True)

        return super().get_queryset(*args, **kwargs).exclude(pk__in=exclude_pks)


class JobDetail(PermissionListMixin, GenericUIView):
    queryset = JobLog.objects.all()
    permission_classes = (DjangoOnlyObjectPermissions,)
    permission_required = [VIEW_JOBLOG_PERMISSION]
    serializer_class = JobSerializer

    def get(self, request, *args, **kwargs):
        """
        Show job
        """
        job = get_object_for_user(request.user, VIEW_JOBLOG_PERMISSION, JobLog, id=kwargs["job_id"])
        job.log_dir = os.path.join(RUN_DIR, f"{job.id}")
        logs = get_log(job)
        for lg in logs:
            log_id = lg["id"]
            lg["url"] = reverse(
                "log-storage", kwargs={"job_id": job.id, "log_id": log_id}, request=request
            )
            lg["download_url"] = reverse(
                "download-log", kwargs={"job_id": job.id, "log_id": log_id}, request=request
            )

        job.log_files = logs
        serializer = self.get_serializer(job, data=request.data)
        serializer.is_valid()

        return Response(serializer.data)


class LogStorageListView(PermissionListMixin, PaginatedView):
    queryset = LogStorage.objects.all()
    permission_required = ["cm.view_logstorage"]
    serializer_class = LogStorageListSerializer
    filterset_fields = ("name", "type", "format")
    ordering_fields = ("id", "name")

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if "job_id" not in self.kwargs:
            return queryset

        return queryset.filter(job_id=self.kwargs["job_id"])


class LogStorageView(PermissionListMixin, GenericUIView):
    queryset = LogStorage.objects.all()
    permission_classes = (IsAuthenticated,)
    permission_required = ["cm.view_logstorage"]
    serializer_class = LogStorageSerializer

    def get(self, request, *args, **kwargs):
        job = get_object_for_user(request.user, VIEW_JOBLOG_PERMISSION, JobLog, id=kwargs["job_id"])
        try:
            log_storage = self.get_queryset().get(id=kwargs["log_id"], job=job)
        except LogStorage.DoesNotExist as e:
            raise AdcmEx(
                "LOG_NOT_FOUND", f"log {kwargs['log_id']} not found for job {kwargs['job_id']}"
            ) from e

        serializer = self.get_serializer(log_storage)

        return Response(serializer.data)


class LogFile(GenericUIView):
    permission_classes = (IsAuthenticated,)
    queryset = LogStorage.objects.all()
    serializer_class = LogSerializer

    def get(self, request, job_id, tag, level, log_type):
        """
        Show log file
        """
        if tag == "ansible":
            _type = f"std{level}"
        else:
            _type = "check"
            tag = "ansible"

        ls = LogStorage.obj.get(job_id=job_id, name=tag, type=_type, format=log_type)
        serializer = self.get_serializer(ls)

        return Response(serializer.data)


class Task(PermissionListMixin, PaginatedView):
    queryset = TaskLog.objects.order_by("-id")
    permission_required = [VIEW_TASKLOG_PERMISSION]
    serializer_class = TaskListSerializer
    serializer_class_ui = TaskSerializer
    filterset_fields = ("action_id", "pid", "status", "start_date", "finish_date")
    ordering_fields = ("status", "start_date", "finish_date")

    def get_queryset(self, *args, **kwargs):
        if self.request.user.is_superuser:
            exclude_pks = []
        else:
            exclude_pks = TaskLog.get_adcm_tasks_qs().values_list("pk", flat=True)

        return super().get_queryset(*args, **kwargs).exclude(pk__in=exclude_pks)


class TaskDetail(PermissionListMixin, DetailView):
    queryset = TaskLog.objects.all()
    permission_required = [VIEW_TASKLOG_PERMISSION]
    serializer_class = TaskSerializer
    lookup_field = "id"
    lookup_url_kwarg = "task_id"
    error_code = "TASK_NOT_FOUND"


class TaskReStart(GenericUIView):
    queryset = TaskLog.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = TaskSerializer

    @audit
    def put(self, request, *args, **kwargs):
        task = get_object_for_user(
            request.user, VIEW_TASKLOG_PERMISSION, TaskLog, id=kwargs["task_id"]
        )
        check_custom_perm(request.user, "change", TaskLog, task)
        restart_task(task)

        return Response(status=HTTP_200_OK)


class TaskCancel(GenericUIView):
    queryset = TaskLog.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = TaskSerializer

    @audit
    def put(self, request, *args, **kwargs):
        task = get_object_for_user(
            request.user, VIEW_TASKLOG_PERMISSION, TaskLog, id=kwargs["task_id"]
        )
        check_custom_perm(request.user, "change", TaskLog, task)
        cancel_task(task)

        return Response(status=HTTP_200_OK)


class TaskDownload(PermissionListMixin, APIView):
    permission_required = [VIEW_TASKLOG_PERMISSION]

    @staticmethod
    def get(request: Request, task_id: int):  # pylint: disable=too-many-locals
        task = TaskLog.objects.filter(pk=task_id).first()
        if not task:
            return Response(status=HTTP_404_NOT_FOUND)

        response = HttpResponse(
            content=get_task_download_archive_file_handler(task=task).getvalue(),
            content_type="application/tar+gzip",
        )
        response[
            "Content-Disposition"
        ] = f'attachment; filename="{get_task_download_archive_name(task=task)}"'

        return response
