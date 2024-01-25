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

from adcm.permissions import VIEW_GROUP_PERMISSION, CustomModelPermissionsByMethod
from audit.utils import audit
from cm.errors import AdcmEx
from guardian.mixins import PermissionListMixin
from rbac.models import Group
from rbac.services.group import create as create_group
from rbac.services.group import update as update_group
from rbac.utils import Empty
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from api_v2.rbac.group.filters import GroupFilter
from api_v2.rbac.group.serializers import (
    GroupCreateSerializer,
    GroupSerializer,
    GroupUpdateSerializer,
)
from api_v2.views import CamelCaseModelViewSet


class GroupViewSet(PermissionListMixin, CamelCaseModelViewSet):
    queryset = Group.objects.order_by("display_name").prefetch_related("user_set")
    filterset_class = GroupFilter
    permission_classes = (CustomModelPermissionsByMethod,)
    method_permissions_map = {
        "patch": [(VIEW_GROUP_PERMISSION, NotFound)],
        "delete": [(VIEW_GROUP_PERMISSION, NotFound)],
    }
    permission_required = [VIEW_GROUP_PERMISSION]

    def get_serializer_class(self) -> type[GroupSerializer | GroupCreateSerializer | GroupUpdateSerializer]:
        if self.action == "create":
            return GroupCreateSerializer

        elif self.action in ("update", "partial_update"):
            return GroupUpdateSerializer

        return GroupSerializer

    @audit
    def create(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        users = [{"id": user.pk} for user in serializer.validated_data.pop("user_set", [])]
        group = create_group(
            name_to_display=serializer.validated_data["display_name"],
            description=serializer.validated_data.get("description", ""),
            user_set=users,
        )

        return Response(data=GroupSerializer(instance=group).data, status=HTTP_201_CREATED)

    @audit
    def update(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        users = [{"id": user.pk} for user in validated_data.pop("user_set")] if "user_set" in validated_data else Empty

        group = update_group(
            group=self.get_object(),
            name_to_display=validated_data.get("display_name", Empty),
            description=validated_data.get("description", Empty),
            user_set=users,
            partial=kwargs.get("partial", False),
        )

        return Response(data=GroupSerializer(instance=group).data, status=HTTP_200_OK)

    @audit
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        instance: Group = self.get_object()

        if instance.built_in:
            raise AdcmEx(code="GROUP_DELETE_ERROR")

        if instance.policy_set.exists():
            raise AdcmEx(code="GROUP_DELETE_ERROR", msg="Group with policy should not be deleted")

        return super().destroy(*args, request=request, **kwargs)
