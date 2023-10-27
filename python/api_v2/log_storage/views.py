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

import re
from pathlib import Path

from api_v2.log_storage.serializers import LogStorageSerializer
from api_v2.views import CamelCaseGenericViewSet
from cm.models import JobLog, LogStorage
from django.http import HttpResponse
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.request import Request

from adcm import settings
from adcm.permissions import VIEW_JOBLOG_PERMISSION, VIEW_LOGSTORAGE_PERMISSION


# pylint:disable-next=too-many-ancestors
class LogStorageViewSet(PermissionListMixin, ListModelMixin, RetrieveModelMixin, CamelCaseGenericViewSet):
    queryset = LogStorage.objects.select_related("job")
    serializer_class = LogStorageSerializer
    filter_backends = []
    pagination_class = None
    permission_classes = [DjangoObjectPermissions]
    permission_required = [VIEW_LOGSTORAGE_PERMISSION]

    def get_queryset(self, *args, **kwargs):
        job = JobLog.objects.filter(id=self.kwargs["job_pk"]).first()

        if job is None or not self.request.user.has_perms(VIEW_JOBLOG_PERMISSION, job):
            raise NotFound

        queryset = super().get_queryset(*args, **kwargs)

        return queryset.filter(job_id=self.kwargs["job_pk"])

    @action(methods=["get"], detail=True)
    def download(self, request: Request, **kwargs) -> HttpResponse:  # pylint: disable=unused-argument
        log_storage = self.get_object()
        job_pk = log_storage.job.pk

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