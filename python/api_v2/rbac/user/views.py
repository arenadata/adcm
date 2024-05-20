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
from typing import Any

from adcm.permissions import VIEW_USER_PERMISSION
from audit.utils import audit
from cm.errors import AdcmEx
from core.errors import NotFoundError
from core.rbac.dto import UserCreateDTO, UserUpdateDTO
from core.rbac.errors import (
    ChangeMembershipError,
    EmailTakenError,
    PasswordError,
    UpdateLDAPUserError,
    UsernameTakenError,
)
from django.conf import settings
from django.contrib.auth.models import Group as AuthGroup
from django.db.models import Prefetch
from django_filters.rest_framework.backends import DjangoFilterBackend
from guardian.mixins import PermissionListMixin
from rbac.models import User
from rbac.services.user import (
    perform_regular_user_update,
    perform_user_creation,
    perform_user_update_as_superuser,
    perform_users_block,
    perform_users_unblock,
)
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_403_FORBIDDEN, HTTP_409_CONFLICT

from api_v2.rbac.user.filters import UserFilterSet
from api_v2.rbac.user.permissions import UserPermissions
from api_v2.rbac.user.serializers import (
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from api_v2.views import CamelCaseModelViewSet


class UserViewSet(PermissionListMixin, CamelCaseModelViewSet):
    queryset = (
        # Filtering by `group__isnull` to filter out possible `auth_group` that hasn't got `rbac_group` linked.
        # Such groups are considered invalid.
        User.objects.prefetch_related(
            Prefetch(lookup="groups", queryset=AuthGroup.objects.select_related("group").filter(group__isnull=False))
        )
        .exclude(username__in=settings.ADCM_HIDDEN_USERS)
        .order_by("username")
    )
    filter_backends = (DjangoFilterBackend,)
    filterset_class = UserFilterSet
    permission_required = [VIEW_USER_PERMISSION]
    permission_classes = (UserPermissions,)

    def get_serializer_class(self) -> type[UserSerializer] | type[UserUpdateSerializer] | type[UserCreateSerializer]:
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer

        if self.action == "create":
            return UserCreateSerializer

        return UserSerializer

    @audit
    def create(self, request: Request, *_, **__) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user_id = perform_user_creation(
                create_data=UserCreateDTO(**serializer.validated_data),
                groups=set(serializer.validated_data.get("groups", ())),
            )
        except UsernameTakenError:
            raise AdcmEx(code="USER_CREATE_ERROR", msg="User with the same username already exist") from None
        except EmailTakenError:
            raise AdcmEx(code="USER_CREATE_ERROR", msg="User with the same email already exist") from None
        except PasswordError as err:
            raise AdcmEx(code="USER_PASSWORD_ERROR", msg=err.message) from None
        except ChangeMembershipError as err:
            raise AdcmEx(code="USER_CREATE_ERROR", http_code=HTTP_409_CONFLICT, msg=err.message) from None

        return Response(data=UserSerializer(instance=self.get_queryset().get(id=user_id)).data, status=HTTP_201_CREATED)

    @audit
    def partial_update(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        user_id = int(kwargs["pk"])
        new_password = validated_data.get("password", None)
        try:
            if request.user.is_superuser:
                perform_user_update_as_superuser(
                    user_id=user_id,
                    update_data=UserUpdateDTO(**validated_data),
                    new_password=new_password,
                    new_user_groups=set(validated_data["groups"]) if "groups" in validated_data else None,
                )
            else:
                perform_regular_user_update(
                    user_id=user_id, update_data=UserUpdateDTO(**validated_data), new_password=new_password
                )
        except EmailTakenError:
            raise AdcmEx(code="USER_CONFLICT", msg="User with the same email already exist") from None
        except PasswordError as err:
            raise AdcmEx(code="USER_PASSWORD_ERROR", msg=err.message) from None
        except ChangeMembershipError as err:
            raise AdcmEx(code="USER_UPDATE_ERROR", http_code=HTTP_409_CONFLICT, msg=err.message) from None
        except UpdateLDAPUserError:
            raise AdcmEx(
                code="USER_UPDATE_ERROR", http_code=HTTP_409_CONFLICT, msg="LDAP user's information can't be changed"
            ) from None
        except NotFoundError as err:
            raise NotFound(err.message) from None

        return Response(data=UserSerializer(instance=self.get_queryset().get(id=user_id)).data, status=HTTP_200_OK)

    @audit
    @action(methods=["post"], detail=True)
    def block(self, request: Request, *_, **kwargs: Any) -> Response:
        # to check existence
        self.get_object()

        if not request.user.is_superuser:
            raise AdcmEx(
                code="USER_BLOCK_ERROR",
                http_code=HTTP_403_FORBIDDEN,
                msg="You do not have permission to perform this action.",
            )

        user_id = int(kwargs["pk"])
        if request.user.pk == user_id:
            raise AdcmEx(code="USER_BLOCK_ERROR", http_code=HTTP_409_CONFLICT, msg="You can't block yourself.")

        try:
            perform_users_block(users=[user_id])
        except UpdateLDAPUserError:
            raise AdcmEx(
                code="USER_BLOCK_ERROR", http_code=HTTP_409_CONFLICT, msg="You can't block LDAP users."
            ) from None

        return Response(status=HTTP_200_OK)

    @audit
    @action(methods=["post"], detail=True)
    def unblock(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        # to check existence
        self.get_object()

        if not request.user.is_superuser:
            raise AdcmEx(
                code="USER_UNBLOCK_ERROR",
                http_code=HTTP_403_FORBIDDEN,
                msg="You do not have permission to perform this action.",
            )

        perform_users_unblock(users=[int(kwargs["pk"])])

        return Response(status=HTTP_200_OK)

    @audit
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        user = self.get_object()
        if user.built_in:
            raise AdcmEx(code="USER_DELETE_ERROR")

        return super().destroy(*args, request=request, **kwargs)
