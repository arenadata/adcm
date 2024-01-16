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
from api_v2.log_storage.utils import (
    get_task_download_archive_file_handler,
    get_task_download_archive_name,
)
from api_v2.task.filters import TaskFilter
from api_v2.task.permissions import TaskPermissions
from api_v2.task.serializers import TaskListSerializer
from api_v2.views import CamelCaseGenericViewSet
from audit.utils import audit
from cm.models import TaskLog
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django_filters.rest_framework.backends import DjangoFilterBackend
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from adcm.permissions import VIEW_TASKLOG_PERMISSION


class TaskViewSet(
    PermissionListMixin, ListModelMixin, RetrieveModelMixin, CreateModelMixin, CamelCaseGenericViewSet
):  # pylint: disable=too-many-ancestors
    queryset = TaskLog.objects.select_related("action").order_by("-pk")
    serializer_class = TaskListSerializer
    filterset_class = TaskFilter
    filter_backends = (DjangoFilterBackend,)
    permission_classes = [TaskPermissions]
    permission_required = [VIEW_TASKLOG_PERMISSION]

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if not self.request.user.is_superuser:
            queryset = queryset.exclude(object_type=ContentType.objects.get(app_label="cm", model="adcm"))
        return queryset

    @audit
    @action(methods=["post"], detail=True)
    def terminate(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        task = self.get_object()
        task.cancel()

        return Response(status=HTTP_200_OK, data=TaskListSerializer(instance=task).data)

    @action(methods=["get"], detail=True, url_path="logs/download")
    def download(self, request: Request, *args, **kwargs):  # pylint: disable=unused-argument
        task = self.get_object()
        response = HttpResponse(
            content=get_task_download_archive_file_handler(task=task).getvalue(),
            content_type="application/tar+gzip",
        )
        response["Content-Disposition"] = f'attachment; filename="{get_task_download_archive_name(task=task)}"'

        return response
