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

from cm.impl.common.execution_plan import STORED_VERSION
from cm.models import TaskLog
from cm.transition.status import StatusScenarios
from core import secrets
from core.action.job import JobRepoI, JobShortFilter
from core.errors import NotFoundError
from dishka import FromDishka
from django.conf import settings
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from api_v2.internal.permissions import IsSuperUser
from api_v2.internal.serializers import (
    StatusCheckerTokenSerializer,
    TaskExecutionPlanSerializer,
    represent_execution_plan,
)
from api_v2.permissions import TaskVisibilityMixin
from api_v2.utils.di import inject
from api_v2.views import ADCMGenericViewSet


class StatusServerUpdateView(ADCMGenericViewSet):
    # Endpoints

    @inject
    def create(self, request, *_, status_scenarios: FromDishka[StatusScenarios], **__):  # noqa: ARG002
        self.check_is_allowed(request)
        status_scenarios.update_all()
        return Response(status=HTTP_200_OK)

    # Helpers

    def check_is_allowed(self, request) -> None:
        if request.user is None or request.user.username != settings.ADCM_STATUS_USERNAME:
            raise PermissionDenied()


class StatusCheckerTokenViewSet(ADCMGenericViewSet):
    permission_classes = [IsSuperUser]
    serializer_class = StatusCheckerTokenSerializer

    @inject
    def list(
        self,
        request: Request,  # noqa: ARG002
        *_,
        status_checker_token: FromDishka[secrets.StatusCheckerStatusServiceToken],
        **__,
    ) -> Response:
        serializer = self.get_serializer({"token": status_checker_token})
        return Response(serializer.data)


class TaskExecutionPlanViewSet(TaskVisibilityMixin, ADCMGenericViewSet):
    queryset = TaskLog.objects.only("id")
    serializer_class = TaskExecutionPlanSerializer

    @inject
    def retrieve(
        self,
        request: Request,  # noqa: ARG002
        *args,  # noqa: ARG002
        job_repo: FromDishka[JobRepoI],
        **kwargs,  # noqa: ARG002
    ) -> Response:
        # for visibility/permission checks: an invisible task 404s before any repo read
        task = self.get_object()

        try:
            plan = job_repo.get_execution_plan(task_id=task.pk)
        except NotFoundError:
            raise NotFound() from None

        jobs = job_repo.find_jobs_short(JobShortFilter(task_ids=[task.pk]))
        execution_plan = represent_execution_plan(spec=plan, jobs=jobs, version=STORED_VERSION)

        serializer = self.get_serializer(execution_plan)
        return Response(serializer.data)
