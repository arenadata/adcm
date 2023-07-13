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
from api.base_view import GenericUIViewSet
from api.job.views import VIEW_TASKLOG_PERMISSION
from api_v2.task.serializers import TaskListSerializer
from cm.job import cancel_task
from cm.models import TaskLog
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from adcm.permissions import check_custom_perm, get_object_for_user


class TaskViewSet(
    ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericUIViewSet
):  # pylint: disable=too-many-ancestors
    queryset = TaskLog.objects.select_related("action").all()
    serializer_class = TaskListSerializer

    @action(methods=["post"], detail=True)
    def terminate(self, request: Request, pk: int) -> Response:
        task = get_object_for_user(request.user, VIEW_TASKLOG_PERMISSION, TaskLog, id=pk)
        check_custom_perm(request.user, "change", TaskLog, task)
        cancel_task(task)

        return Response(status=HTTP_200_OK)
