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
from cm.models import Action
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN
from rest_framework.viewsets import GenericViewSet

from adcm.mixins import GetParentObjectMixin
from adcm.permissions import (
    VIEW_ACTION_PERM,
    DjangoModelPermissionsAudit,
    get_object_for_user,
)
from adcm.utils import filter_actions


class ActionViewSet(  # pylint: disable=too-many-ancestors
    PermissionListMixin, GenericViewSet, ListModelMixin, RetrieveModelMixin, GetParentObjectMixin
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

    def get_queryset(self, *args, **kwargs):
        parent_object = self.get_parent_object()
        if parent_object is None:
            raise NotFound("Can't find action's parent object")

        return super().get_queryset(*args, **kwargs).filter(prototype=parent_object.prototype)

    def list(self, request: Request, *args, **kwargs) -> Response:
        parent_object = self.get_parent_object()
        if parent_object is None:
            raise NotFound("Can't find action's parent object")

        allowed_actions = filter_actions(
            obj=parent_object,
            actions=filter_actions_by_user_perm(
                user=request.user,
                obj=parent_object,
                actions=self.filter_queryset(queryset=self.get_queryset()),
            ),
        )
        serializer = self.get_serializer_class()(instance=allowed_actions, many=True, context={"request": request})

        return Response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        parent_object = self.get_parent_object()
        if parent_object is None:
            raise NotFound("Can't find action's parent object")

        # check permissions
        get_object_for_user(user=request.user, perms=VIEW_ACTION_PERM, klass=Action, pk=kwargs["pk"])

        return super().retrieve(request, *args, **kwargs)

    @action(methods=["post"], detail=True, url_path="run")
    def run(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        parent_object = self.get_parent_object()
        if parent_object is None:
            raise NotFound("Can't find action's parent object")

        target_action = get_object_for_user(user=request.user, perms=VIEW_ACTION_PERM, klass=Action, pk=kwargs["pk"])
        if not check_run_perms(user=request.user, action=target_action, obj=parent_object):
            return Response(data="Run action forbidden", status=HTTP_403_FORBIDDEN)

        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        start_task(
            action=target_action,
            obj=parent_object,
            conf=serializer.validated_data["config"],
            attr=serializer.validated_data["attr"],
            hostcomponent=serializer.validated_data["host_component_map"],
            hosts=[],
            verbose=serializer.validated_data["is_verbose"],
        )

        return Response()
