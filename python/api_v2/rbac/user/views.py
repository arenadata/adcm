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
from api_v2.rbac.user.filters import UserFilterSet
from api_v2.rbac.user.serializers import (
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from api_v2.rbac.user.utils import unblock_user
from api_v2.views import CamelCaseModelViewSet
from audit.utils import audit
from cm.errors import AdcmEx
from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup
from django.db.models import Prefetch
from django_filters.rest_framework.backends import DjangoFilterBackend
from guardian.mixins import PermissionListMixin
from rbac.models import User
from rbac.services.user import create_user, update_user
from rbac.utils import Empty
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from adcm.permissions import VIEW_USER_PERMISSION, CustomModelPermissionsByMethod


class UserViewSet(PermissionListMixin, CamelCaseModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = (
        User.objects.prefetch_related(Prefetch(lookup="groups", queryset=AuthGroup.objects.select_related("group")))
        .exclude(username__in=settings.ADCM_HIDDEN_USERS)
        .order_by("username")
    )
    filter_backends = (DjangoFilterBackend,)
    filterset_class = UserFilterSet
    permission_required = [VIEW_USER_PERMISSION]
    permission_classes = (CustomModelPermissionsByMethod,)
    method_permissions_map = {
        "patch": [(VIEW_USER_PERMISSION, NotFound)],
        "delete": [(VIEW_USER_PERMISSION, NotFound)],
    }

    def get_serializer_class(self) -> type[UserSerializer] | type[UserUpdateSerializer] | type[UserCreateSerializer]:
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer

        if self.action == "create":
            return UserCreateSerializer

        return UserSerializer

    @audit
    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        groups = [{"id": group.pk} for group in serializer.validated_data.pop("groups", [])]
        user: User = create_user(groups=groups, **serializer.validated_data)

        return Response(data=UserSerializer(instance=user).data, status=HTTP_201_CREATED)

    @audit
    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        instance: User = self.get_object()
        serializer = self.get_serializer(instance=instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        groups = [{"id": group.pk} for group in validated_data.pop("groups")] if "groups" in validated_data else Empty
        user: User = update_user(
            user=serializer.instance,
            context_user=request.user,
            partial=True,
            need_current_password=False,
            groups=groups,
            **validated_data,
        )

        return Response(data=UserSerializer(instance=user).data, status=HTTP_200_OK)

    @audit
    @action(methods=["post"], detail=True)
    def unblock(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        if not request.user.is_superuser:
            raise AdcmEx(code="USER_UNBLOCK_ERROR")

        unblock_user(user=self.get_object())

        return Response(status=HTTP_200_OK)

    @audit
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        user = self.get_object()
        if user.built_in:
            raise AdcmEx(code="USER_DELETE_ERROR")

        return super().destroy(request=request, *args, **kwargs)
