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

from collections import defaultdict

from adcm.permissions import VIEW_ROLE_PERMISSION
from audit.alt.api import audit_create, audit_delete, audit_update
from audit.alt.hooks import (
    extract_current_from_response,
    extract_from_object,
    extract_previous_from_object,
    only_on_success,
)
from cm.errors import AdcmEx
from cm.models import Cluster, Host, ProductCategory, Provider, Service
from django.db.models import Prefetch
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from guardian.mixins import PermissionListMixin
from rbac.models import ObjectType as RBACObjectType
from rbac.models import Role, RoleTypes
from rbac.services.role import role_create, role_update
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin, RetrieveModelMixin
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
from api_v2.rbac.role.filters import RoleFilter
from api_v2.rbac.role.permissions import RolePermissions
from api_v2.rbac.role.serializers import (
    RoleCategoriesSerializer,
    RoleCreateSerializer,
    RoleObjectCandidatesSerializer,
    RoleSerializer,
    RoleUpdateSerializer,
)
from api_v2.utils.audit import retrieve_role_children, role_from_lookup, role_from_response, update_role_name
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    list=extend_schema(
        operation_id="getRoles",
        description="Get information about user roles in ADCM.",
        summary="GET roles",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(
                name="categories",
                description="List of categories in the role.",
            ),
            OpenApiParameter(
                name="type",
                description="Type of the role.",
                enum=("business", "role"),
            ),
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                enum=("displayName", "-displayName"),
                default="displayName",
            ),
        ],
        responses={
            HTTP_200_OK: RoleSerializer(many=True),
            HTTP_403_FORBIDDEN: ErrorSerializer,
        },
    ),
    create=extend_schema(
        operation_id="postRoles",
        description="Create a new user role in ADCM.",
        summary="POST roles",
        responses={
            HTTP_201_CREATED: RoleSerializer(many=False),
            **{err_code: ErrorSerializer for err_code in (HTTP_403_FORBIDDEN, HTTP_409_CONFLICT, HTTP_400_BAD_REQUEST)},
        },
    ),
    retrieve=extend_schema(
        operation_id="getRole",
        description="Get information about a specific ADCM user role.",
        summary="GET role",
        responses={
            HTTP_200_OK: RoleSerializer(many=False),
            **{err_code: ErrorSerializer for err_code in (HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN)},
        },
    ),
    partial_update=extend_schema(
        operation_id="patchRole",
        description="Change information about the ADCM user role.",
        summary="PATCH role",
        responses={
            HTTP_200_OK: RoleCreateSerializer,
            **{
                err_code: ErrorSerializer
                for err_code in (HTTP_403_FORBIDDEN, HTTP_409_CONFLICT, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND)
            },
        },
    ),
    destroy=extend_schema(
        operation_id="deleteRole",
        description="Delete a specific ADCM user role.",
        summary="DELETE role",
        responses={
            HTTP_204_NO_CONTENT: None,
            **{err_code: ErrorSerializer for err_code in (HTTP_409_CONFLICT, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)},
        },
    ),
    object_candidates=extend_schema(
        operation_id="getCandidateobject",
        description="Get information about objects which are might be chosen in policy for concrete role.",
        summary="GET Candidate",
        responses={
            HTTP_200_OK: RoleObjectCandidatesSerializer,
            HTTP_403_FORBIDDEN: ErrorSerializer,
        },
    ),
    categories=extend_schema(
        operation_id="getCategories",
        description="Get information about objects which are might be chosen in policy for concrete role.",
        summary="GET Candidate",
        responses={
            HTTP_200_OK: RoleCategoriesSerializer,
            HTTP_403_FORBIDDEN: ErrorSerializer,
        },
    ),
)
class RoleViewSet(
    PermissionListMixin,
    ListModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    CreateModelMixin,
    ADCMGenericViewSet,
):
    queryset = (
        Role.objects.prefetch_related(
            Prefetch(lookup="child", queryset=Role.objects.exclude(type=RoleTypes.HIDDEN)), "category", "policy_set"
        )
        .exclude(type=RoleTypes.HIDDEN)
        .order_by("display_name")
    )
    permission_classes = (RolePermissions,)
    permission_required = [VIEW_ROLE_PERMISSION]
    filterset_class = RoleFilter

    def get_serializer_class(self):
        if self.action == "create":
            return RoleCreateSerializer

        elif self.action == "partial_update":
            return RoleUpdateSerializer
        elif self.action == "categories":
            return RoleCategoriesSerializer
        elif self.action == "object_candidates":
            return RoleObjectCandidatesSerializer

        return RoleSerializer

    @audit_create(name="Role created", object_=role_from_response)
    def create(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = role_create(**serializer.validated_data)

        return Response(data=RoleSerializer(instance=role).data, status=HTTP_201_CREATED)

    @(
        audit_update(name="Role updated", object_=role_from_lookup)
        .attach_hooks(on_collect=only_on_success(update_role_name))
        .track_changes(
            before=(
                extract_previous_from_object(Role, "name", "display_name", "description"),
                extract_from_object(func=retrieve_role_children, section="previous"),
            ),
            after=(
                extract_current_from_response("name", "display_name", "description"),
                extract_from_object(func=retrieve_role_children, section="current"),
            ),
        )
    )
    def partial_update(self, request, *args, **kwargs):  # noqa: ARG002
        instance = self.get_object()

        if instance.built_in:
            raise AdcmEx(code="ROLE_UPDATE_ERROR", msg=f"Can't modify role {instance.name} as it is auto created")

        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        role = role_update(role=instance, partial=True, **serializer.validated_data)

        return Response(data=RoleSerializer(instance=role).data, status=HTTP_200_OK)

    @audit_delete(name="Role deleted", object_=role_from_lookup, removed_on_success=True)
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.built_in:
            raise AdcmEx(code="ROLE_DELETE_ERROR", msg="It is forbidden to remove the built-in role.")

        if instance.policy_set.exists():
            raise AdcmEx(code="ROLE_DELETE_ERROR", msg="Can't remove role that is used in policy.")

        return super().destroy(request, *args, **kwargs)

    @action(methods=["get"], detail=False, pagination_class=None)
    def categories(self, request, *args, **kwargs):  # noqa: ARG001, ARG002
        serializer = self.get_serializer(data=sorted(ProductCategory.objects.values_list("value", flat=True)))
        serializer.is_valid(raise_exception=True)
        return Response(data=serializer.data, status=HTTP_200_OK)

    @action(methods=["get"], detail=True, url_path="object-candidates", url_name="object-candidates")
    def object_candidates(self, request, *args, **kwargs):  # noqa: ARG001, ARG002
        role = self.get_object()
        if role.type != RoleTypes.ROLE:
            return Response({"cluster": [], "provider": [], "service": [], "host": []})

        clusters = []
        providers = []
        services = []
        hosts = []

        if RBACObjectType.CLUSTER.value in role.parametrized_by_type:
            for cluster in Cluster.objects.all():
                clusters.append(
                    {
                        "name": cluster.display_name,
                        "id": cluster.id,
                    },
                )

        if RBACObjectType.PROVIDER.value in role.parametrized_by_type:
            for provider in Provider.objects.all():
                providers.append(
                    {
                        "name": provider.display_name,
                        "id": provider.id,
                    },
                )

        if RBACObjectType.HOST.value in role.parametrized_by_type:
            for host in Host.objects.all():
                hosts.append(
                    {
                        "name": host.display_name,
                        "id": host.id,
                    },
                )

        if (
            RBACObjectType.SERVICE.value in role.parametrized_by_type
            or RBACObjectType.COMPONENT.value in role.parametrized_by_type
        ):
            _services = defaultdict(list)
            for service in Service.objects.all():
                _services[service].append(
                    {
                        "name": service.cluster.name,
                        "id": service.id,
                    },
                )
            for service, clusters_info in _services.items():
                services.append(
                    {
                        "name": service.name,
                        "display_name": service.display_name,
                        "clusters": sorted(clusters_info, key=lambda x: x["name"]),
                    },
                )

        serializer = self.get_serializer(
            data={
                "cluster": sorted(clusters, key=lambda x: x["name"]),
                "provider": sorted(providers, key=lambda x: x["name"]),
                "service": sorted(services, key=lambda x: x["name"]),
                "host": sorted(hosts, key=lambda x: x["name"]),
            }
        )
        serializer.is_valid(raise_exception=True)

        return Response(data=serializer.data, status=HTTP_200_OK)
