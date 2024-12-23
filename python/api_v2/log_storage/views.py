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
import re

from adcm import settings
from adcm.permissions import VIEW_LOGSTORAGE_PERMISSION
from cm.models import JobLog, LogStorage
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from api_v2.api_schema import ErrorSerializer
from api_v2.log_storage.filters import LogFilter
from api_v2.log_storage.permissions import LogStoragePermissions
from api_v2.log_storage.serializers import LogStorageSerializer
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    list=extend_schema(
        operation_id="getLogstorage",
        description="Contains job's logs storage",
        summary="GET logs storage",
        responses={
            HTTP_200_OK: LogStorageSerializer(many=True),
            **{err_code: ErrorSerializer for err_code in (HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN)},
        },
    ),
    retrieve=extend_schema(
        operation_id="getJobslog",
        description="Contains logs by job",
        summary="GET job's log",
        responses={
            HTTP_200_OK: LogStorageSerializer(many=False),
            **{err_code: ErrorSerializer for err_code in (HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN)},
        },
    ),
    download=extend_schema(
        operation_id="getJobLogDownload",
        description="Download specific job log.",
        summary="GET job log download",
        parameters=[
            OpenApiParameter(
                name="jobId",
                type=int,
                location=OpenApiParameter.PATH,
                description="Job id.",
            ),
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Log id.",
            ),
        ],
        responses={
            (HTTP_200_OK, "text/plain"): {"type": "string", "format": "binary"},
            (HTTP_200_OK, "application/json"): {"type": "string", "format": "binary"},
            **{err_code: ErrorSerializer for err_code in (HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)},
        },
    ),
)
class LogStorageViewSet(PermissionListMixin, ListModelMixin, RetrieveModelMixin, ADCMGenericViewSet):
    queryset = LogStorage.objects.select_related("job")
    serializer_class = LogStorageSerializer
    filterset_class = LogFilter
    pagination_class = None
    permission_classes = [LogStoragePermissions]
    permission_required = [VIEW_LOGSTORAGE_PERMISSION]

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        return queryset.filter(job_id=self.kwargs["job_pk"])

    def list(self, request: Request, *args, **kwargs) -> Response:
        if not JobLog.objects.filter(id=self.kwargs["job_pk"]).exists():
            raise NotFound

        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs) -> Response:
        if not JobLog.objects.filter(id=self.kwargs["job_pk"]).exists():
            raise NotFound

        return super().retrieve(request, *args, **kwargs)

    @action(methods=["get"], detail=True)
    def download(self, request: Request, **kwargs) -> HttpResponse:  # noqa: ARG001, ARG002
        log_storage = self.get_object()
        job_pk = log_storage.job.pk

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
