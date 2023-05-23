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

from api_v2.action.serializers import (
    ActionListSerializer,
    ActionRetrieveSerializer,
    ActionRunSerializer,
)
from cm.job import start_task
from cm.models import Action, Cluster
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND
from rest_framework.viewsets import GenericViewSet

from adcm.permissions import VIEW_ACTION_PERM, DjangoModelPermissionsAudit


class ActionViewSet(  # pylint: disable=too-many-ancestors
    PermissionListMixin, GenericViewSet, ListModelMixin, RetrieveModelMixin
):
    queryset = Action.objects.all()
    serializer_class = ActionListSerializer
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_ACTION_PERM]

    def get_queryset(self, *args, **kwargs):
        cluster = Cluster.objects.filter(pk=self.kwargs.get("cluster_pk")).first()
        if not cluster:
            return Action.objects.none()

        return self.queryset.filter(prototype=cluster.prototype)

    def get_serializer_class(
        self,
    ) -> type[ActionRetrieveSerializer] | type[ActionListSerializer] | type[ActionRunSerializer]:
        if self.action == "retrieve":
            return ActionRetrieveSerializer

        if self.action == "run":
            return ActionRunSerializer

        return self.serializer_class

    def list(self, request: Request, *args, **kwargs) -> Response:
        if not Cluster.objects.filter(pk=kwargs["cluster_pk"]).exists():
            return Response(data=f'Cluster with pk "{kwargs.get("cluster_pk")}" not found', status=HTTP_404_NOT_FOUND)

        return super().list(request, *args, **kwargs)

    @action(methods=["post"], detail=True)
    def run(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        cluster_action = Action.objects.filter(pk=kwargs["pk"]).first()
        if not action:
            return Response(data=f'Action with pk "{kwargs["pk"]}" not found', status=HTTP_404_NOT_FOUND)

        cluster = Cluster.objects.filter(pk=kwargs["cluster_pk"]).first()
        if not cluster:
            return Response(data=f'Cluster with pk "{kwargs["cluster_pk"]}" not found', status=HTTP_404_NOT_FOUND)

        start_task(
            action=cluster_action,
            obj=cluster,
            conf=serializer.validated_data["config"],
            attr=serializer.validated_data["attr"],
            hostcomponent=serializer.validated_data["host_component_map"],
            hosts=[],
            verbose=serializer.validated_data["is_verbose"],
        )

        return Response()
