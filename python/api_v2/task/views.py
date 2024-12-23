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


from adcm.permissions import VIEW_TASKLOG_PERMISSION
from audit.alt.api import audit_update
from cm.models import TaskLog
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.api_schema import DefaultParams, ErrorSerializer
from api_v2.log_storage.utils import (
    get_task_download_archive_file_handler,
    get_task_download_archive_name,
)
from api_v2.task.filters import TaskFilter
from api_v2.task.permissions import TaskPermissions
from api_v2.task.serializers import TaskListSerializer
from api_v2.utils.audit import detect_object_for_task, set_task_name
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    list=extend_schema(
        operation_id="getTasks",
        description="Get a list of ADCM tasks.",
        summary="GET tasks",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(
                name="id",
                description="Filter by id.",
                type=int,
            ),
            OpenApiParameter(
                name="job_name",
                description="Case insensitive and partial filter by job name.",
            ),
            OpenApiParameter(
                name="object_name",
                description="Case insensitive and partial filter by object name.",
            ),
            OpenApiParameter(
                name="status",
                description="Filter by status.",
                enum=["created", "running", "success", "failed", "aborted", "broken", "locked"],
            ),
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                enum=(
                    "name",
                    "-name",
                    "id",
                    "-id",
                    "startTime",
                    "-startTime",
                    "endTime",
                    "-endTime",
                ),
                default="-id",
            ),
        ],
        responses={
            HTTP_200_OK: TaskListSerializer(many=True),
        },
    ),
    terminate=extend_schema(
        operation_id="postTaskTerminate",
        description="Terminate the execution of a specific task.",
        summary="POST task terminate",
        responses={
            HTTP_200_OK: OpenApiResponse(),
            **{err_code: ErrorSerializer for err_code in (HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN, HTTP_409_CONFLICT)},
        },
    ),
    retrieve=extend_schema(
        operation_id="getTask",
        description="Get information about a specific ADCM task.",
        summary="GET task",
        responses={
            HTTP_200_OK: TaskListSerializer(many=False),
            **{err_code: ErrorSerializer for err_code in (HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN)},
        },
    ),
    download=extend_schema(
        operation_id="getTaskLogsDownload",
        description="Download all task logs.",
        summary="GET task logs download",
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Task id.",
            ),
        ],
        responses={
            (HTTP_200_OK, "application/tar+gzip"): {"type": "string", "format": "binary"},
            **{err_code: ErrorSerializer for err_code in (HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)},
        },
    ),
)
class TaskViewSet(PermissionListMixin, ListModelMixin, RetrieveModelMixin, ADCMGenericViewSet):
    queryset = TaskLog.objects.select_related("action").order_by("-pk")
    serializer_class = TaskListSerializer
    filterset_class = TaskFilter
    permission_classes = [TaskPermissions]
    permission_required = [VIEW_TASKLOG_PERMISSION]

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if not self.request.user.is_superuser:
            queryset = queryset.exclude(object_type=ContentType.objects.get(app_label="cm", model="adcm"))
        return queryset

    @audit_update(name="{task_name} cancelled", object_=detect_object_for_task).attach_hooks(on_collect=set_task_name)
    @action(methods=["post"], detail=True, serializer_class=None)
    def terminate(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        task = self.get_object()
        task.cancel()

        return Response(status=HTTP_200_OK, data=TaskListSerializer(instance=task).data)

    @action(methods=["get"], detail=True, url_path="logs/download")
    def download(self, request: Request, *args, **kwargs):  # noqa: ARG001, ARG002
        task = self.get_object()
        response = HttpResponse(
            content=get_task_download_archive_file_handler(task=task).getvalue(),
            content_type="application/tar+gzip",
        )
        response["Content-Disposition"] = f'attachment; filename="{get_task_download_archive_name(task=task)}"'

        return response
