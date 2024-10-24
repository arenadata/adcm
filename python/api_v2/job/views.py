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


from adcm.permissions import VIEW_JOBLOG_PERMISSION
from adcm.serializers import EmptySerializer
from audit.alt.api import audit_update
from cm.models import JobLog
from django.contrib.contenttypes.models import ContentType
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
from api_v2.job.filters import JobFilter
from api_v2.job.permissions import JobPermissions
from api_v2.job.serializers import JobRetrieveSerializer
from api_v2.task.serializers import JobListSerializer
from api_v2.utils.audit import detect_object_for_job, set_job_name
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    list=extend_schema(
        operation_id="getJobs",
        description="Get a list of ADCM jobs.",
        summary="GET jobs",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(
                name="ordering",
                required=False,
                location=OpenApiParameter.QUERY,
                description="Field to sort by. To sort in descending order, precede the attribute name with a '-'.",
                type=str,
                enum=["id", "status", "-id", "-status", "startTime", "-startTime", "endTime", "-endTime"],
            ),
            OpenApiParameter(
                name="status",
                required=False,
                location=OpenApiParameter.QUERY,
                description="Job status.",
                type=str,
                enum=["created", "running", "success", "failed", "terminated", "cancelled"],
            ),
        ],
    ),
    terminate=extend_schema(
        operation_id="postJobTerminate",
        description="Terminate the execution of a specific job.",
        summary="POST job terminate",
        responses={
            HTTP_200_OK: OpenApiResponse(description="OK"),
            **{err_code: ErrorSerializer for err_code in (HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN, HTTP_409_CONFLICT)},
        },
    ),
    retrieve=extend_schema(
        operation_id="getJob",
        description="Get information about a specific ADCM job.",
        summary="GET job",
        responses={
            HTTP_200_OK: JobRetrieveSerializer,
            **{err_code: ErrorSerializer for err_code in (HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN)},
        },
    ),
)
class JobViewSet(PermissionListMixin, ListModelMixin, RetrieveModelMixin, ADCMGenericViewSet):
    queryset = JobLog.objects.select_related("task__action").order_by("pk")
    filterset_class = JobFilter
    permission_classes = [JobPermissions]
    permission_required = [VIEW_JOBLOG_PERMISSION]

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if not self.request.user.is_superuser:
            queryset = queryset.exclude(task__object_type=ContentType.objects.get(app_label="cm", model="adcm"))
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return JobRetrieveSerializer

        if self.action == "terminate":
            return EmptySerializer

        return JobListSerializer

    @audit_update(name="{job_name} terminated", object_=detect_object_for_job).attach_hooks(on_collect=set_job_name)
    @action(methods=["post"], detail=True)
    def terminate(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        job = self.get_object()
        job.cancel()

        return Response(status=HTTP_200_OK)
