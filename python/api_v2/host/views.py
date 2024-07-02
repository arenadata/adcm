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


from adcm.permissions import (
    VIEW_CLUSTER_PERM,
    VIEW_HOST_PERM,
    VIEW_PROVIDER_PERM,
    ChangeMMPermissions,
    check_custom_perm,
    get_object_for_user,
)
from audit.alt.api import audit_create, audit_delete, audit_update
from audit.alt.hooks import extract_current_from_response, extract_previous_from_object, only_on_success
from cm.api import delete_host
from cm.errors import AdcmEx
from cm.models import Cluster, ConcernType, Host, HostProvider
from django.db.transaction import atomic
from django_filters.rest_framework.backends import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
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
from api_v2.generic.action.api_schema import document_action_viewset
from api_v2.generic.action.audit import audit_action_viewset
from api_v2.generic.action.views import ActionViewSet
from api_v2.generic.config.api_schema import document_config_viewset
from api_v2.generic.config.audit import audit_config_viewset
from api_v2.generic.config.utils import ConfigSchemaMixin
from api_v2.generic.config.views import ConfigLogViewSet
from api_v2.host.filters import HostFilter
from api_v2.host.permissions import (
    HostsPermissions,
)
from api_v2.host.serializers import (
    HostChangeMaintenanceModeSerializer,
    HostCreateSerializer,
    HostSerializer,
    HostUpdateSerializer,
)
from api_v2.host.utils import create_host, maintenance_mode, process_config_issues_policies_hc
from api_v2.utils.audit import host_from_lookup, host_from_response, parent_host_from_lookup, update_host_name
from api_v2.views import ADCMGenericViewSet, ObjectWithStatusViewMixin


@extend_schema_view(
    list=extend_schema(
        operation_id="getHosts",
        description="Get a list of all hosts.",
        summary="GET hosts",
        parameters=[
            OpenApiParameter(name="name", description="Case insensitive and partial filter by host name."),
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                type=str,
                enum=("name", "-name", "id", "-id"),
                default="name",
            ),
        ],
        responses={
            HTTP_200_OK: HostSerializer(many=True),
        },
    ),
    create=extend_schema(
        operation_id="postHosts",
        description="Create a new hosts.",
        summary="POST hosts",
        responses={
            HTTP_201_CREATED: HostSerializer,
            **{err_code: ErrorSerializer for err_code in (HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_409_CONFLICT)},
        },
    ),
    retrieve=extend_schema(
        operation_id="getHost",
        description="Get information about a specific host.",
        summary="GET host",
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Host id.",
            ),
        ],
        responses={
            HTTP_200_OK: HostSerializer,
            HTTP_404_NOT_FOUND: ErrorSerializer,
        },
    ),
    destroy=extend_schema(
        operation_id="deleteHost",
        description="Delete host from ADCM.",
        summary="DELETE host",
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Host id.",
            ),
        ],
        responses={
            HTTP_204_NO_CONTENT: None,
            **{err_code: ErrorSerializer for err_code in (HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)},
        },
    ),
    partial_update=extend_schema(
        operation_id="patchHost",
        description="Change host Information.",
        summary="PATCH host",
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Host id.",
            ),
        ],
        responses={
            HTTP_200_OK: HostSerializer,
            **{
                err_code: ErrorSerializer
                for err_code in (HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
            },
        },
    ),
    maintenance_mode=extend_schema(
        operation_id="postHostMaintenanceMode",
        description="Turn on/off maintenance mode on the host.",
        summary="POST host maintenance-mode",
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="Host id.",
            ),
        ],
        responses={
            HTTP_200_OK: HostChangeMaintenanceModeSerializer,
            **{
                err_code: ErrorSerializer
                for err_code in (HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
            },
        },
    ),
)
class HostViewSet(
    PermissionListMixin,
    ConfigSchemaMixin,
    ObjectWithStatusViewMixin,
    RetrieveModelMixin,
    ListModelMixin,
    ADCMGenericViewSet,
):
    queryset = (
        Host.objects.select_related("provider", "cluster", "cluster__prototype", "prototype")
        .prefetch_related("concerns", "hostcomponent_set__component__prototype")
        .order_by("fqdn")
    )
    permission_required = [VIEW_HOST_PERM]
    permission_classes = [HostsPermissions]
    filterset_class = HostFilter
    filter_backends = (DjangoFilterBackend,)

    def get_serializer_class(self):
        if self.action == "create":
            return HostCreateSerializer
        elif self.action in ("update", "partial_update"):
            return HostUpdateSerializer
        elif self.action == "maintenance_mode":
            return HostChangeMaintenanceModeSerializer

        return HostSerializer

    @audit_create(name="Host created", object_=host_from_response)
    def create(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request_hostprovider = get_object_for_user(
            user=request.user,
            perms=VIEW_PROVIDER_PERM,
            klass=HostProvider,
            id=serializer.validated_data["hostprovider_id"],
        )

        request_cluster = None
        if serializer.validated_data.get("cluster_id"):
            request_cluster = get_object_for_user(
                user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=serializer.validated_data["cluster_id"]
            )

        with atomic():
            host = create_host(
                provider=request_hostprovider, fqdn=serializer.validated_data["fqdn"], cluster=request_cluster
            )
            process_config_issues_policies_hc(host=host)

        return Response(
            data=HostSerializer(instance=host, context=self.get_serializer_context()).data, status=HTTP_201_CREATED
        )

    @audit_delete(name="Host deleted", object_=host_from_lookup, removed_on_success=True)
    def destroy(self, request, *args, **kwargs):  # noqa: ARG002
        host = self.get_object()
        check_custom_perm(request.user, "remove", "host", host)
        delete_host(host=host)
        return Response(status=HTTP_204_NO_CONTENT)

    @(
        audit_update(name="Host updated", object_=host_from_lookup)
        .attach_hooks(on_collect=only_on_success(update_host_name))
        .track_changes(
            before=extract_previous_from_object(Host, "fqdn", "description"),
            after=extract_current_from_response("fqdn", "description", fqdn="name"),
        )
    )
    def partial_update(self, request, *args, **kwargs):  # noqa: ARG002
        instance = self.get_object()
        check_custom_perm(request.user, "change", "host", instance)

        serializer = self.get_serializer(instance=instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        valid = serializer.validated_data

        if valid.get("fqdn") and instance.concerns.filter(type=ConcernType.LOCK).exists():
            raise AdcmEx(code="HOST_CONFLICT", msg="Name change is available only if no locking concern exists")

        if (
            valid.get("fqdn")
            and valid.get("fqdn") != instance.fqdn
            and (instance.cluster or instance.state != "created")
        ):
            raise AdcmEx(code="HOST_UPDATE_ERROR")

        serializer.save()

        return Response(
            status=HTTP_200_OK, data=HostSerializer(instance=instance, context=self.get_serializer_context()).data
        )

    @audit_update(name="Host updated", object_=host_from_lookup).track_changes(
        before=extract_previous_from_object(Host, "maintenance_mode"),
        after=extract_current_from_response("maintenance_mode"),
    )
    @action(methods=["post"], detail=True, url_path="maintenance-mode", permission_classes=[ChangeMMPermissions])
    def maintenance_mode(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        return maintenance_mode(request=request, host=self.get_object())


@document_action_viewset(object_type="host")
@audit_action_viewset(retrieve_owner=parent_host_from_lookup)
class HostActionViewSet(ActionViewSet):
    ...


@document_config_viewset(object_type="host")
@audit_config_viewset(type_in_name="Host", retrieve_owner=parent_host_from_lookup)
class HostConfigViewSet(ConfigLogViewSet):
    ...
