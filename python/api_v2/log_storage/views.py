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

# pylint: disable=duplicate-code
import io
import re
import tarfile
from pathlib import Path

from api.job.views import VIEW_LOGSTORAGE_PERMISSION
from api_v2.log_storage.serializers import LogStorageSerializer
from api_v2.views import CamelCaseGenericViewSet
from cm.errors import raise_adcm_ex
from cm.models import ActionType, JobLog, LogStorage, TaskLog
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request

from adcm import settings
from adcm.permissions import VIEW_TASKLOG_PERMISSION, get_object_for_user
from adcm.utils import str_remove_non_alnum


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
        "cluster object",
        "service component",
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
    elif task.object_type.name == "cluster object":
        obj_name = task.task_object.cluster.name
    elif task.object_type.name == "service component":
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
                dir_name_suffix = ""
                if job.sub_action:
                    dir_name_suffix = str_remove_non_alnum(value=job.sub_action.display_name) or str_remove_non_alnum(
                        value=job.sub_action.name,
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
                    body = io.BytesIO(bytes(log_storage.body, settings.ENCODING_UTF_8))
                    tarinfo.size = body.getbuffer().nbytes
                    tar_file.addfile(tarinfo=tarinfo, fileobj=body)

    return file_handler


# pylint:disable-next=too-many-ancestors
class LogStorageViewSet(ListModelMixin, RetrieveModelMixin, CamelCaseGenericViewSet):
    queryset = LogStorage.objects.order_by("pk")
    serializer_class = LogStorageSerializer
    filter_backends = []
    pagination_class = None
    permission_required = ["cm.view_logstorage"]
    lookup_url_kwarg = "log_pk"

    def list(self, request, *args, **kwargs):
        if "task_pk" in self.request.parser_context["kwargs"]:
            raise_adcm_ex("LOG_FOR_TASK_VIEW_NOT_ALLOWED", "The task view does not allow to read logs")
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if "task_pk" in self.request.parser_context["kwargs"]:
            raise_adcm_ex("LOG_FOR_TASK_VIEW_NOT_ALLOWED", "The task view does not allow to read logs")
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self, *args, **kwargs):  # pylint: disable=unused-argument
        if "task_pk" in self.request.parser_context["kwargs"]:
            return self.queryset.filter(job__task_id=self.request.parser_context["kwargs"]["task_pk"])
        elif "job_pk" in self.kwargs:
            self.queryset = self.queryset.filter(job_id=self.kwargs["job_pk"])

        return self.queryset


# pylint:disable-next=too-many-ancestors
class LogStorageTaskViewSet(LogStorageViewSet):
    @action(methods=["get"], detail=False)
    def download(self, request: Request, task_pk: int) -> HttpResponse:
        task = get_object_for_user(request.user, VIEW_TASKLOG_PERMISSION, TaskLog, id=task_pk)
        response = HttpResponse(
            content=get_task_download_archive_file_handler(task=task).getvalue(),
            content_type="application/tar+gzip",
        )
        response["Content-Disposition"] = f'attachment; filename="{get_task_download_archive_name(task=task)}"'

        return response


# pylint:disable-next=too-many-ancestors
class LogStorageJobViewSet(LogStorageViewSet):
    @action(methods=["get"], detail=True)
    def download(self, request: Request, **kwargs) -> HttpResponse:
        job_pk, log_pk = kwargs["job_pk"], kwargs["log_pk"]
        log_storage = get_object_for_user(
            user=request.user, perms=VIEW_LOGSTORAGE_PERMISSION, klass=LogStorage, id=log_pk, job__id=job_pk
        )
        if log_storage.type in {"stdout", "stderr"}:
            filename = f"{job_pk}-{log_storage.name}-{log_storage.type}.{log_storage.format}"
        else:
            filename = f"{job_pk}-{log_storage.name}.{log_storage.format}"

        filename = re.sub(r"\s+", "_", filename)
        if log_storage.format == "txt":
            mime_type = "text/plain"
        else:
            mime_type = "application/json"

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
