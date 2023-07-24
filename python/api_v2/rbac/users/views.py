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

from api_v2.rbac.users.filters import UserFilterSet, UserOrderingFilter
from api_v2.rbac.users.serializers import (
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from django.utils.timezone import now
from django_filters.rest_framework.backends import DjangoFilterBackend
from guardian.mixins import PermissionListMixin
from rbac.models import User
from rbac.services.user import create_user, update_user
from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework.viewsets import ModelViewSet

from adcm.permissions import VIEW_USER_PERMISSION


class UserViewSet(PermissionListMixin, ModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = User.objects.prefetch_related("groups").all()
    serializer_class = UserSerializer
    filter_backends = (
        DjangoFilterBackend,
        UserOrderingFilter,
    )
    ordering = ("id",)
    filterset_class = UserFilterSet
    permission_classes = (DjangoModelPermissions,)
    permission_required = [VIEW_USER_PERMISSION]
    http_method_names = ["get", "post", "patch"]

    def get_serializer_class(self) -> type[UserSerializer] | type[UserUpdateSerializer] | type[UserCreateSerializer]:
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer

        if self.action == "create":
            return UserCreateSerializer

        return self.serializer_class

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user: User = create_user(**serializer.validated_data)

        return Response(data=UserSerializer(instance=user).data, status=HTTP_201_CREATED)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        instance: User = self.get_object()
        serializer = self.get_serializer(instance=instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        user: User = update_user(
            user=serializer.instance,
            context_user=request.user,
            partial=True,
            need_current_password=not request.user.is_superuser,
            api_v2_behaviour=True,
            **serializer.validated_data,
        )

        return Response(data=UserSerializer(instance=user).data, status=HTTP_200_OK)

    @action(methods=["post"], detail=True)
    def block(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        user = self.get_object()
        user.blocked_at = now()
        user.save(update_fields=["blocked_at"])

        return Response()

    @action(methods=["post"], detail=True)
    def unblock(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        user = self.get_object()
        user.blocked_at = None
        user.save(update_fields=["blocked_at"])

        return Response()

    @action(methods=["post"], detail=True)
    def delete(self, request: Request, *args, **kwargs) -> Response:
        return super().destroy(request=request, *args, **kwargs)
