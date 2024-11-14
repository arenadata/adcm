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
    CHANGE_MM_PERM,
    VIEW_CLUSTER_PERM,
    VIEW_COMPONENT_PERM,
    VIEW_HOST_PERM,
    VIEW_SERVICE_PERM,
    ChangeMMPermissions,
    DjangoModelPermissionsAudit,
    check_custom_perm,
    get_object_for_user,
)
from audit.alt.api import audit_update
from audit.alt.hooks import adjust_denied_on_404_result, extract_current_from_response, extract_previous_from_object
from cm.errors import AdcmEx
from cm.models import Cluster, Component, Host, Service
from cm.services.maintenance_mode import get_maintenance_mode_response
from cm.services.status.notify import update_mm_objects
from django.db.models import F
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.api_schema import DefaultParams, ErrorSerializer
from api_v2.component.filters import ComponentFilter
from api_v2.component.serializers import (
    ComponentMaintenanceModeSerializer,
    ComponentSerializer,
    ComponentStatusSerializer,
    HostComponentSerializer,
)
from api_v2.generic.action.api_schema import document_action_viewset
from api_v2.generic.action.audit import audit_action_viewset
from api_v2.generic.action.views import ActionViewSet
from api_v2.generic.action_host_group.api_schema import (
    document_action_host_group_actions_viewset,
    document_action_host_group_hosts_viewset,
    document_action_host_group_viewset,
)
from api_v2.generic.action_host_group.views import (
    ActionHostGroupActionsViewSet,
    ActionHostGroupHostsViewSet,
    ActionHostGroupViewSet,
)
from api_v2.generic.config.api_schema import document_config_viewset
from api_v2.generic.config.audit import audit_config_viewset
from api_v2.generic.config.utils import ConfigSchemaMixin
from api_v2.generic.config.views import ConfigLogViewSet
from api_v2.generic.config_host_group.api_schema import (
    document_config_host_group_viewset,
    document_host_config_host_group_viewset,
)
from api_v2.generic.config_host_group.audit import (
    audit_config_config_host_group_viewset,
    audit_config_host_group_viewset,
    audit_host_config_host_group_viewset,
)
from api_v2.generic.config_host_group.views import CHGViewSet, HostCHGViewSet
from api_v2.utils.audit import (
    component_from_lookup,
    component_with_parents_specified_in_path_exists,
    parent_component_from_lookup,
)
from api_v2.views import (
    ADCMGenericViewSet,
    ADCMReadOnlyModelViewSet,
    ObjectWithStatusViewMixin,
)


@extend_schema_view(
    statuses=extend_schema(
        operation_id="getHostComponentStatusesOfComponent",
        summary="GET host-component statuses of component on hoosts",
        description="Get information about component on hosts statuses.",
        responses={HTTP_200_OK: ComponentStatusSerializer, HTTP_404_NOT_FOUND: ErrorSerializer},
    ),
    retrieve=extend_schema(
        operation_id="getComponent",
        description="Get information about a specific component.",
        summary="GET components",
        responses={HTTP_200_OK: ComponentSerializer, HTTP_404_NOT_FOUND: ErrorSerializer},
    ),
    list=extend_schema(
        operation_id="getComponents",
        description="Get a list of all components of a particular service with information on them.",
        summary="GET components",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            DefaultParams.ordering_by("id"),
            OpenApiParameter(
                name="id",
                location=OpenApiParameter.QUERY,
                description="Component id.",
                type=int,
            ),
            OpenApiParameter(
                name="state",
                location=OpenApiParameter.QUERY,
                description="Case insensitive and partial filter by state.",
                type=str,
            ),
            OpenApiParameter(
                name="name",
                location=OpenApiParameter.QUERY,
                description="Case insensitive and partial filter by name.",
                type=str,
            ),
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                type=str,
                enum=(
                    "id",
                    "-id",
                    "name",
                    "-name",
                    "state",
                    "-state",
                    "displayName",
                    "-displayName",
                ),
                default="id",
            ),
        ],
        responses={HTTP_200_OK: ComponentSerializer(many=True), HTTP_404_NOT_FOUND: ErrorSerializer},
    ),
    maintenance_mode=extend_schema(
        operation_id="postComponentMaintenanceMode",
        description="Turn on/off maintenance mode on the component.",
        summary="POST component maintenance-mode",
        responses={
            HTTP_200_OK: ComponentMaintenanceModeSerializer,
            **{
                err_code: ErrorSerializer
                for err_code in (HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
            },
        },
    ),
)
class ComponentViewSet(PermissionListMixin, ConfigSchemaMixin, ObjectWithStatusViewMixin, ADCMReadOnlyModelViewSet):
    queryset = Component.objects.select_related("cluster", "service").order_by("pk")
    permission_classes = [DjangoModelPermissions]
    permission_required = [VIEW_COMPONENT_PERM]
    filterset_class = ComponentFilter
    retrieve_status_map_actions = ("statuses", "list")

    audit_model_hint = Component

    def get_queryset(self, *args, **kwargs):
        cluster = get_object_for_user(
            user=self.request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, pk=self.kwargs["cluster_pk"]
        )
        service = get_object_for_user(
            user=self.request.user, perms=VIEW_SERVICE_PERM, klass=Service, pk=self.kwargs["service_pk"]
        )

        return super().get_queryset(*args, **kwargs).filter(cluster=cluster, service=service)

    def get_serializer_class(self):
        match self.action:
            case "maintenance_mode":
                return ComponentMaintenanceModeSerializer

        return ComponentSerializer

    @(
        audit_update(name="Component updated", object_=component_from_lookup)
        .attach_hooks(on_collect=adjust_denied_on_404_result(component_with_parents_specified_in_path_exists))
        .track_changes(
            before=extract_previous_from_object(model=Component, maintenance_mode=F("_maintenance_mode")),
            after=extract_current_from_response("maintenance_mode"),
        )
    )
    @update_mm_objects
    @action(methods=["post"], detail=True, url_path="maintenance-mode", permission_classes=[ChangeMMPermissions])
    def maintenance_mode(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        component: Component = get_object_for_user(
            user=request.user, perms=VIEW_COMPONENT_PERM, klass=Component, pk=kwargs["pk"]
        )

        if not component.is_maintenance_mode_available:
            raise AdcmEx(code="MAINTENANCE_MODE_NOT_AVAILABLE", msg="Component does not support maintenance mode")

        check_custom_perm(
            user=request.user, action_type=CHANGE_MM_PERM, model=component.__class__.__name__.lower(), obj=component
        )

        serializer = self.get_serializer_class()(instance=component, data=request.data)
        serializer.is_valid(raise_exception=True)

        response: Response = get_maintenance_mode_response(obj=self.get_object(), serializer=serializer)
        if response.status_code == HTTP_200_OK:
            response.data = serializer.data

        return response

    @action(methods=["get"], detail=True, url_path="statuses")
    def statuses(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        component = get_object_for_user(user=request.user, perms=VIEW_COMPONENT_PERM, klass=Component, id=kwargs["pk"])

        return Response(data=ComponentStatusSerializer(instance=component, context=self.get_serializer_context()).data)


@extend_schema_view(
    list=extend_schema(
        operation_id="getHostComponents",
        summary="GET host components",
        description="Get a list of host components.",
        parameters=[
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                type=str,
                enum=(
                    "id",
                    "-id",
                    "name",
                    "-name",
                    "state",
                    "-state",
                    "displayName",
                    "-displayName",
                ),
                default="id",
            ),
        ],
    )
)
class HostComponentViewSet(PermissionListMixin, ListModelMixin, ObjectWithStatusViewMixin, ADCMGenericViewSet):
    queryset = Component.objects.select_related("cluster", "service").order_by("prototype__name")
    serializer_class = HostComponentSerializer
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_COMPONENT_PERM]
    filterset_class = ComponentFilter

    def get_queryset(self, *args, **kwargs):
        cluster = get_object_for_user(
            user=self.request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, pk=self.kwargs["cluster_pk"]
        )
        host = get_object_for_user(user=self.request.user, perms=VIEW_HOST_PERM, klass=Host, pk=self.kwargs["host_pk"])

        return (
            super()
            .get_queryset(*args, **kwargs)
            .filter(cluster=cluster, id__in=host.hostcomponent_set.all().values_list("component_id", flat=True))
        )


@document_config_host_group_viewset(object_type="component")
@audit_config_host_group_viewset(retrieve_owner=parent_component_from_lookup)
class ComponentCHGViewSet(CHGViewSet):
    ...


@document_host_config_host_group_viewset(object_type="component")
@audit_host_config_host_group_viewset(retrieve_owner=parent_component_from_lookup)
class ComponentHostCHGViewSet(HostCHGViewSet):
    ...


@document_config_viewset(object_type="component config group", operation_id_variant="ComponentConfigGroup")
@audit_config_config_host_group_viewset(retrieve_owner=parent_component_from_lookup)
class ComponentConfigCHGViewSet(ConfigLogViewSet):
    ...


@document_action_viewset(object_type="component")
@audit_action_viewset(retrieve_owner=parent_component_from_lookup)
class ComponentActionViewSet(ActionViewSet):
    ...


@document_action_host_group_viewset(object_type="component")
class ComponentActionHostGroupViewSet(ActionHostGroupViewSet):
    ...


@document_action_host_group_hosts_viewset(object_type="component")
class ComponentActionHostGroupHostsViewSet(ActionHostGroupHostsViewSet):
    ...


@document_action_host_group_actions_viewset(object_type="component")
class ComponentActionHostGroupActionsViewSet(ActionHostGroupActionsViewSet):
    ...


@document_config_viewset(object_type="component")
@audit_config_viewset(type_in_name="Component", retrieve_owner=parent_component_from_lookup)
class ComponentConfigViewSet(ConfigLogViewSet):
    ...
