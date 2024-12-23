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
from audit.alt.api import audit_create, audit_delete, audit_update
from audit.alt.hooks import (
    extract_current_from_response,
    extract_from_object,
    extract_previous_from_object,
    only_on_success,
)
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
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
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
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.api_schema import DefaultParams, ErrorSerializer
from api_v2.rbac.user.filters import UserFilterSet
from api_v2.rbac.user.permissions import UserPermissions
from api_v2.rbac.user.serializers import (
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from api_v2.utils.audit import (
    retrieve_user_password_groups,
    set_username_for_block_actions,
    update_user_name,
    user_from_lookup,
    user_from_response,
)
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    list=extend_schema(
        operation_id="getUsers",
        description="Get a list of ADCM users with information on them.",
        summary="GET users",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(name="username", description="Case insensitive and partial filter by user name."),
            OpenApiParameter(name="status", description="User status.", enum=("active", "blocked")),
            OpenApiParameter(name="type", description="User type.", enum=("local", "ldap")),
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                enum=("username", "-username"),
                default="username",
            ),
        ],
        responses={
            HTTP_200_OK: UserSerializer(many=True),
            HTTP_403_FORBIDDEN: ErrorSerializer,
        },
    ),
    create=extend_schema(
        operation_id="postUsers",
        description="Create a new ADCM user.",
        summary="POST users",
        responses={
            HTTP_201_CREATED: UserSerializer(many=False),
            **{err_code: ErrorSerializer for err_code in (HTTP_403_FORBIDDEN, HTTP_409_CONFLICT, HTTP_400_BAD_REQUEST)},
        },
    ),
    retrieve=extend_schema(
        operation_id="getUser",
        description="Get detailed information about a specific user.",
        summary="GET user",
        responses={
            HTTP_200_OK: UserSerializer(many=False),
            **{err_code: ErrorSerializer for err_code in (HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN)},
        },
    ),
    partial_update=extend_schema(
        operation_id="patchUser",
        description="Change information for a specific user.",
        summary="PATCH user",
        responses={
            HTTP_200_OK: UserSerializer,
            **{
                err_code: ErrorSerializer
                for err_code in (HTTP_403_FORBIDDEN, HTTP_409_CONFLICT, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND)
            },
        },
    ),
    block=extend_schema(
        operation_id="postUsersBlock",
        description="Block users in the ADCM (manual block).",
        summary="POST user block",
        responses={
            HTTP_200_OK: OpenApiResponse(),
            **{err_code: ErrorSerializer for err_code in (HTTP_409_CONFLICT, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)},
        },
    ),
    unblock=extend_schema(
        operation_id="postUsersUnblock",
        description="Unblock the user in the ADCM",
        summary="POST user unblock",
        responses={
            HTTP_200_OK: OpenApiResponse(),
            **{err_code: ErrorSerializer for err_code in (HTTP_409_CONFLICT, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)},
        },
    ),
    destroy=extend_schema(
        operation_id="deleteUser",
        description="Delete user from ADCM",
        summary="DELETE user",
        responses={
            HTTP_204_NO_CONTENT: None,
            **{err_code: ErrorSerializer for err_code in (HTTP_409_CONFLICT, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)},
        },
    ),
)
class UserViewSet(
    PermissionListMixin,
    ListModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    CreateModelMixin,
    ADCMGenericViewSet,
):
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

    def get_serializer_class(
        self,
    ) -> type[UserSerializer] | type[UserUpdateSerializer] | type[UserCreateSerializer] | None:
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer

        elif self.action == "create":
            return UserCreateSerializer

        elif self.action in ("block", "unblock"):
            return None

        return UserSerializer

    @audit_create(name="User created", object_=user_from_response)
    def create(self, request: Request, *_, **__) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.is_superuser and serializer.validated_data["is_superuser"]:
            raise AdcmEx(
                code="USER_CREATE_ERROR",
                http_code=HTTP_403_FORBIDDEN,
                msg="You can't create user with ADCM Administrator's rights.",
            )

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

    @(
        audit_update(name="User updated", object_=user_from_lookup)
        .attach_hooks(on_collect=only_on_success(update_user_name))
        .track_changes(
            before=(
                extract_previous_from_object(User, "first_name", "last_name", "email", "password", "is_superuser"),
                extract_from_object(func=retrieve_user_password_groups, section="previous"),
            ),
            after=(
                extract_current_from_response(
                    "first_name",
                    "last_name",
                    "email",
                    is_superuser="is_super_user",
                ),
                extract_from_object(func=retrieve_user_password_groups, section="current"),
            ),
        )
    )
    def partial_update(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        user_id = int(kwargs["pk"])
        new_password = validated_data.get("password", None)

        try:
            if request.user.is_superuser:
                if request.user.pk == user_id and validated_data.get("is_superuser") is False:
                    raise AdcmEx(
                        code="USER_UPDATE_ERROR",
                        http_code=HTTP_409_CONFLICT,
                        msg="You can't withdraw ADCM Administrator's rights from yourself.",
                    )

                perform_user_update_as_superuser(
                    user_id=user_id,
                    update_data=UserUpdateDTO(**validated_data),
                    new_password=new_password,
                    new_user_groups=set(validated_data["groups"]) if "groups" in validated_data else None,
                )
            else:
                if new_password is not None and not request.user.is_superuser:
                    raise AdcmEx(
                        code="USER_UPDATE_ERROR", http_code=HTTP_403_FORBIDDEN, msg="You can't change user's password."
                    )

                if "is_superuser" in validated_data:
                    raise AdcmEx(
                        code="USER_UPDATE_ERROR",
                        http_code=HTTP_403_FORBIDDEN,
                        msg=f"You can't {'grant' if validated_data['is_superuser'] else 'withdraw'} "
                        "ADCM Administrator's rights.",
                    )

                perform_regular_user_update(user_id=user_id, update_data=UserUpdateDTO(**validated_data))
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

    @audit_update(name="{username} user blocked", object_=user_from_lookup).attach_hooks(
        pre_call=set_username_for_block_actions
    )
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

    @audit_update(name="{username} user unblocked", object_=user_from_lookup).attach_hooks(
        pre_call=set_username_for_block_actions
    )
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

    @audit_delete(name="User deleted", object_=user_from_lookup, removed_on_success=True)
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        user = self.get_object()
        if user.built_in:
            raise AdcmEx(code="USER_DELETE_ERROR")

        return super().destroy(*args, request=request, **kwargs)
