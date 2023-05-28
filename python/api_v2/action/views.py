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

from api_v2.action.filters import ActionFilter
from api_v2.action.serializers import (
    ActionListSerializer,
    ActionRetrieveSerializer,
    ActionRunSerializer,
)
from api_v2.action.utils import check_run_perms, filter_actions_by_user_perm
from cm.job import start_task
from cm.models import Action, Cluster, ClusterObject
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND
from rest_framework.viewsets import GenericViewSet

from adcm.permissions import (
    VIEW_ACTION_PERM,
    VIEW_SERVICE_PERM,
    DjangoModelPermissionsAudit,
    get_object_for_user,
)


class BaseActionViewSet(  # pylint: disable=too-many-ancestors
    PermissionListMixin, GenericViewSet, ListModelMixin, RetrieveModelMixin
):
    queryset = Action.objects.all()
    serializer_class = ActionListSerializer
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_ACTION_PERM]
    filterset_class = ActionFilter

    def get_serializer_class(
        self,
    ) -> type[ActionRetrieveSerializer] | type[ActionListSerializer] | type[ActionRunSerializer]:
        if self.action == "retrieve":
            return ActionRetrieveSerializer

        if self.action == "run":
            return ActionRunSerializer

        return self.serializer_class


class ClusterActionViewSet(BaseActionViewSet):  # pylint: disable=too-many-ancestors
    def get_queryset(self, *args, **kwargs):
        cluster = Cluster.objects.filter(pk=self.kwargs.get("cluster_pk")).first()
        if not cluster:
            return Action.objects.none()

        return self.queryset.filter(prototype=cluster.prototype)

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


class ServiceActionViewSet(BaseActionViewSet):  # pylint: disable=too-many-ancestors
    def get_queryset(self, *args, **kwargs):
        err_msg, _ = self._check_objects_existence(view_kwargs=self.kwargs)
        if err_msg is not None:
            return Action.objects.none()

        return self.queryset.filter(prototype=ClusterObject.objects.get(pk=self.kwargs["service_pk"]).prototype)

    def list(self, request: Request, *args, **kwargs) -> Response:
        err_msg, return_code = self._check_objects_existence(view_kwargs=kwargs)
        if err_msg is not None:
            return Response(data=err_msg, status=return_code)

        allowed_actions = filter_actions_by_user_perm(
            user=request.user,
            obj=ClusterObject.objects.get(pk=kwargs["service_pk"]),
            actions=self.filter_queryset(queryset=self.get_queryset()),
        )
        serializer = self.get_serializer_class()(instance=allowed_actions, many=True, context={"request": request})

        return Response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        err_msg, return_code = self._check_objects_existence(view_kwargs=kwargs)
        if err_msg is not None:
            return Response(data=err_msg, status=return_code)

        return super().retrieve(request, *args, **kwargs)

    @action(methods=["post"], detail=True, url_path="run")
    def run(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        err_msg, return_code = self._check_objects_existence(view_kwargs=kwargs)
        if err_msg is not None:
            return Response(data=err_msg, status=return_code)

        service = get_object_for_user(
            user=request.user, perms=VIEW_SERVICE_PERM, klass=ClusterObject, pk=kwargs["service_pk"]
        )
        service_action = get_object_for_user(user=request.user, perms=VIEW_ACTION_PERM, klass=Action, pk=kwargs["pk"])
        if not check_run_perms(user=request.user, action=service_action, obj=service):
            return Response(data="Run action forbidden", status=HTTP_403_FORBIDDEN)

        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        start_task(
            action=service_action,
            obj=service,
            conf=serializer.validated_data["config"],
            attr=serializer.validated_data["attr"],
            hostcomponent=serializer.validated_data["host_component_map"],
            hosts=[],
            verbose=serializer.validated_data["is_verbose"],
        )

        return Response()

    @staticmethod
    def _check_objects_existence(view_kwargs: dict) -> tuple[str | None, int | None]:
        if not Cluster.objects.filter(pk=view_kwargs.get("cluster_pk")).first():
            return f'Cluster with pk "{view_kwargs.get("cluster_pk")}" not found', HTTP_404_NOT_FOUND

        if not ClusterObject.objects.filter(pk=view_kwargs.get("service_pk")).first():
            return f'Service with pk "{view_kwargs.get("service_pk")}" not found', HTTP_404_NOT_FOUND

        return None, None
