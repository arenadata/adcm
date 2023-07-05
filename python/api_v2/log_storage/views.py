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
import re
from pathlib import Path

from api.job.views import VIEW_LOGSTORAGE_PERMISSION
from api_v2.log_storage.serializers import LogStorageSerializer
from cm.models import LogStorage
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ModelViewSet

from adcm import settings
from adcm.permissions import get_object_for_user


# pylint:disable-next=too-many-ancestors
class LogStorageViewSet(ModelViewSet):
    queryset = LogStorage.objects.all()
    serializer_class = LogStorageSerializer
    filterset_fields = ("name", "type", "format")
    ordering_fields = ("id", "name")
    permission_required = ["cm.view_logstorage"]
    lookup_url_kwarg = "log_pk"
    ordering = ["id"]

    def get_queryset(self, *args, **kwargs):  # pylint: disable=unused-argument
        queryset = super().get_queryset()
        if "job_pk" in self.kwargs:
            queryset = queryset.filter(job_id=self.kwargs["job_pk"])

        return queryset

    @action(methods=["post"], detail=True)
    def download(self, request: Request, job_pk: int, log_pk: int):  # pylint: disable=unused-argument
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
