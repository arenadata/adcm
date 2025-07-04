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

from adcm.permissions import VIEW_GROUP_PERMISSION
from audit.alt.api import audit_create, audit_delete, audit_update
from audit.alt.hooks import (
    extract_current_from_response,
    extract_from_object,
    extract_previous_from_object,
    only_on_success,
)
from cm.errors import AdcmEx
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from rbac.models import Group
from rbac.services.group import create as create_group
from rbac.services.group import update as update_group
from rbac.utils import Empty
from rest_framework.mixins import DestroyModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
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

from api_v2.api_schema import DefaultParams, responses
from api_v2.rbac.group.filters import GroupFilter
from api_v2.rbac.group.permissions import GroupPermissions
from api_v2.rbac.group.serializers import (
    GroupCreateSerializer,
    GroupSerializer,
    GroupUpdateSerializer,
)
from api_v2.utils.audit import (
    group_from_lookup,
    group_from_response,
    retrieve_group_name_users,
    update_group_name,
)
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    list=extend_schema(
        operation_id="getGroups",
        description="Get information about ADCM user groups.",
        summary="GET groups",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(
                name="display_name", description="Case insensitive and partial filter by group display name."
            ),
            OpenApiParameter(name="type", description="Group type.", enum=("local", "ldap")),
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                enum=("displayName", "-displayName"),
                default="displayName",
            ),
        ],
        responses=responses(success=GroupSerializer(many=True)),
    ),
    create=extend_schema(
        operation_id="postGroups",
        description="Create a new ADCM user group.",
        summary="POST groups",
        responses=responses(
            success=(HTTP_201_CREATED, GroupSerializer(many=False)),
            errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_409_CONFLICT),
        ),
    ),
    retrieve=extend_schema(
        operation_id="getGroup",
        description="Get information about a specific ADCM user group.",
        summary="GET group",
        responses=responses(success=GroupSerializer(many=False), errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)),
    ),
    partial_update=extend_schema(
        operation_id="patchGroup",
        description="Change user group information.",
        summary="PATCH group",
        responses=responses(
            success=GroupSerializer(many=False),
            errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
        ),
    ),
    destroy=extend_schema(
        operation_id="deleteGroup",
        description="Delete groups from ADCM.",
        summary="DELETE group",
        responses=responses(
            success=(HTTP_204_NO_CONTENT, None), errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
        ),
    ),
)
class GroupViewSet(PermissionListMixin, RetrieveModelMixin, ListModelMixin, DestroyModelMixin, ADCMGenericViewSet):
    queryset = Group.objects.order_by("display_name").prefetch_related("user_set")
    filterset_class = GroupFilter
    permission_classes = (IsAuthenticated, GroupPermissions)
    permission_required = [VIEW_GROUP_PERMISSION]

    def get_serializer_class(self) -> type[GroupSerializer | GroupCreateSerializer | GroupUpdateSerializer]:
        if self.action == "create":
            return GroupCreateSerializer

        elif self.action in ("update", "partial_update"):
            return GroupUpdateSerializer

        return GroupSerializer

    @audit_create(name="Group created", object_=group_from_response)
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

    @(
        audit_update(name="Group updated", object_=group_from_lookup)
        .attach_hooks(on_collect=only_on_success(update_group_name))
        .track_changes(
            before=(
                extract_previous_from_object(Group, "description"),
                extract_from_object(func=retrieve_group_name_users, section="previous"),
            ),
            after=(
                extract_current_from_response("description"),
                extract_from_object(func=retrieve_group_name_users, section="current"),
            ),
        )
    )
    def partial_update(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        users = [{"id": user.pk} for user in validated_data.pop("user_set")] if "user_set" in validated_data else Empty

        group = update_group(
            group=self.get_object(),
            name_to_display=validated_data.get("display_name", Empty),
            description=validated_data.get("description", Empty),
            user_set=users,
            partial=True,
        )

        return Response(data=GroupSerializer(instance=group).data, status=HTTP_200_OK)

    @audit_delete(name="Group deleted", object_=group_from_lookup, removed_on_success=True)
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        instance: Group = self.get_object()

        if instance.built_in:
            raise AdcmEx(code="GROUP_DELETE_ERROR")

        if instance.policy_set.exists():
            raise AdcmEx(code="GROUP_DELETE_ERROR", msg="Group with policy should not be deleted")

        return super().destroy(*args, request=request, **kwargs)
