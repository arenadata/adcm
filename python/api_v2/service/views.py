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
    ADD_SERVICE_PERM,
    CHANGE_MM_PERM,
    VIEW_CLUSTER_PERM,
    VIEW_IMPORT_PERM,
    VIEW_SERVICE_PERM,
    ChangeMMPermissions,
    check_custom_perm,
    get_object_for_user,
)
from audit.alt.api import audit_update, audit_view
from audit.alt.hooks import (
    adjust_denied_on_404_result,
    extract_current_from_response,
    extract_previous_from_object,
)
from cm.errors import AdcmEx
from cm.models import Cluster, Service
from cm.services.maintenance_mode import get_maintenance_mode_response
from cm.services.service import delete_service_from_api
from cm.services.status.notify import update_mm_objects
from django.db.models import F
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
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
from api_v2.generic.imports.serializers import ImportPostSerializer, ImportSerializer
from api_v2.generic.imports.views import ImportViewSet
from api_v2.service.filters import ServiceFilter
from api_v2.service.permissions import ServicePermissions
from api_v2.service.serializers import (
    ServiceCreateSerializer,
    ServiceMaintenanceModeSerializer,
    ServiceRetrieveSerializer,
    ServiceStatusSerializer,
)
from api_v2.service.utils import (
    bulk_add_services_to_cluster,
    validate_service_prototypes,
)
from api_v2.utils.audit import (
    parent_cluster_from_lookup,
    parent_service_from_lookup,
    service_does_exist,
    service_from_lookup,
    service_with_parents_specified_in_path_exists,
    set_service_name_from_object,
    set_service_names_from_request,
)
from api_v2.views import ADCMGenericViewSet, ObjectWithStatusViewMixin


@extend_schema_view(
    retrieve=extend_schema(
        operation_id="getClusterService",
        summary="GET cluster service",
        description="Get information about a specific cluster service.",
        responses=responses(success=ServiceRetrieveSerializer, errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)),
    ),
    list=extend_schema(
        operation_id="getClusterServices",
        summary="GET cluster services",
        description="Get a list of all services of a particular cluster with information on them.",
        parameters=[
            OpenApiParameter(
                name="name",
                description="Case insensitive and partial filter by service name.",
            ),
            OpenApiParameter(
                # It is necessary to specify such fields with underscores, otherwise this field will be duplicated
                # in the scheme. The name in the schema must match the name of the field in the filter class
                name="display_name",
                description="Case insensitive and partial filter by service display name.",
            ),
            OpenApiParameter(
                name="status",
                description="Filter by status",
                enum=("up", "down"),
            ),
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                enum=(
                    "displayName",
                    "-displayName",
                ),
                default="id",
            ),
        ],
        responses=responses(success=ServiceRetrieveSerializer(many=True), errors=HTTP_404_NOT_FOUND),
    ),
    create=extend_schema(
        operation_id="postClusterServices",
        summary="POST cluster services",
        description="Add a new cluster services.",
        responses=responses(
            success=(HTTP_201_CREATED, ServiceRetrieveSerializer),
            errors=(HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN, HTTP_409_CONFLICT),
        ),
    ),
    destroy=extend_schema(
        operation_id="deleteClusterService",
        summary="DELETE cluster service",
        description="Delete a specific cluster service.",
        responses=responses(
            success=(HTTP_204_NO_CONTENT, None),
            errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
        ),
    ),
    maintenance_mode=extend_schema(
        operation_id="postServiceMaintenanceMode",
        summary="POST service maintenance-mode",
        description="Turn on/off maintenance mode on the service.",
        responses=responses(
            success=ServiceMaintenanceModeSerializer,
            errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
        ),
    ),
    statuses=extend_schema(
        operation_id="getComponentStatuses",
        summary="GET component statuses",
        description="Get information about component statuses.",
        responses=responses(success=ServiceStatusSerializer, errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)),
    ),
)
class ServiceViewSet(
    PermissionListMixin,
    ConfigSchemaMixin,
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    ObjectWithStatusViewMixin,
    ADCMGenericViewSet,
):
    queryset = Service.objects.select_related("cluster").order_by("pk")
    filterset_class = ServiceFilter
    permission_required = [VIEW_SERVICE_PERM]
    permission_classes = [ServicePermissions]
    audit_model_hint = Service
    retrieve_status_map_actions = ("list", "statuses")

    def get_queryset(self, *args, **kwargs):
        cluster = get_object_for_user(
            user=self.request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=self.kwargs["cluster_pk"]
        )

        return super().get_queryset(*args, **kwargs).filter(cluster=cluster)

    def get_serializer_class(self):
        match self.action:
            case "create":
                return ServiceCreateSerializer
            case "maintenance_mode":
                return ServiceMaintenanceModeSerializer

        return ServiceRetrieveSerializer

    @audit_update(name="{service_names} service(s) added", object_=parent_cluster_from_lookup).attach_hooks(
        pre_call=set_service_names_from_request
    )
    def create(self, request: Request, *args, **kwargs):  # noqa: ARG002
        cluster = get_object_for_user(
            user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, pk=kwargs["cluster_pk"]
        )
        check_custom_perm(user=request.user, action_type=ADD_SERVICE_PERM, model=Cluster.__name__.lower(), obj=cluster)

        multiple_services = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=multiple_services, context={"cluster": cluster})
        serializer.is_valid(raise_exception=True)

        service_prototypes, error = validate_service_prototypes(
            cluster=cluster, data=serializer.validated_data if multiple_services else [serializer.validated_data]
        )
        if error is not None:
            raise error
        added_services = bulk_add_services_to_cluster(cluster=cluster, prototypes=service_prototypes)

        context = self.get_serializer_context()

        if multiple_services:
            return Response(
                status=HTTP_201_CREATED,
                data=ServiceRetrieveSerializer(instance=added_services, many=True, context=context).data,
            )

        return Response(
            status=HTTP_201_CREATED,
            data=ServiceRetrieveSerializer(instance=added_services[0], context=context).data,
        )

    @audit_update(name="{service_name} service removed", object_=parent_cluster_from_lookup).attach_hooks(
        pre_call=set_service_name_from_object, on_collect=adjust_denied_on_404_result(service_does_exist)
    )
    def destroy(self, request: Request, *args, **kwargs):  # noqa: ARG002
        instance = self.get_object()
        return delete_service_from_api(service=instance)

    @(
        audit_update(name="Service updated", object_=service_from_lookup)
        .attach_hooks(on_collect=adjust_denied_on_404_result(service_with_parents_specified_in_path_exists))
        .track_changes(
            before=extract_previous_from_object(model=Service, maintenance_mode=F("_maintenance_mode")),
            after=extract_current_from_response("maintenance_mode"),
        )
    )
    @update_mm_objects
    @action(methods=["post"], detail=True, url_path="maintenance-mode", permission_classes=[ChangeMMPermissions])
    def maintenance_mode(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        service: Service = get_object_for_user(
            user=request.user, perms=VIEW_SERVICE_PERM, klass=Service, pk=kwargs["pk"]
        )

        if not service.is_maintenance_mode_available:
            raise AdcmEx(code="MAINTENANCE_MODE_NOT_AVAILABLE", msg="Service does not support maintenance mode")

        check_custom_perm(
            user=request.user, action_type=CHANGE_MM_PERM, model=service.__class__.__name__.lower(), obj=service
        )

        serializer = self.get_serializer_class()(instance=service, data=request.data)
        serializer.is_valid(raise_exception=True)

        response: Response = get_maintenance_mode_response(obj=self.get_object(), serializer=serializer)
        if response.status_code == HTTP_200_OK:
            response.data = serializer.data

        return response

    @action(methods=["get"], detail=True, url_path="statuses")
    def statuses(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        service = get_object_for_user(user=request.user, perms=VIEW_SERVICE_PERM, klass=Service, id=kwargs["pk"])

        return Response(data=ServiceStatusSerializer(instance=service, context=self.get_serializer_context()).data)


@extend_schema_view(
    list=extend_schema(
        operation_id="getServiceImports",
        description="Get information about service imports.",
        summary="GET service imports",
        parameters=[DefaultParams.LIMIT, DefaultParams.OFFSET],
        responses=responses(success=ImportSerializer(many=True), errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)),
    ),
    create=extend_schema(
        operation_id="postServiceImports",
        description="Import data.",
        summary="POST service imports",
        responses=responses(
            success=(HTTP_201_CREATED, ImportPostSerializer),
            errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
        ),
    ),
)
@audit_view(create=audit_update(name="Service import updated", object_=parent_service_from_lookup))
class ServiceImportViewSet(ImportViewSet):
    def detect_get_check_kwargs(self) -> tuple[dict, dict]:
        return (
            {"perms": VIEW_SERVICE_PERM, "klass": Service, "id": self.kwargs["service_pk"]},
            {"action_type": VIEW_IMPORT_PERM, "model": Service.__name__.lower()},
        )

    def detect_cluster_service_bind_arguments(self, obj: Cluster | Service) -> tuple[Cluster, Service]:
        return obj.cluster, obj


@document_config_host_group_viewset(object_type="service")
@audit_config_host_group_viewset(retrieve_owner=parent_service_from_lookup)
class ServiceCHGViewSet(CHGViewSet):
    ...


@document_host_config_host_group_viewset(object_type="service")
@audit_host_config_host_group_viewset(retrieve_owner=parent_service_from_lookup)
class ServiceHostCHGViewSet(HostCHGViewSet):
    ...


@document_config_viewset(object_type="service config group", operation_id_variant="ServiceConfigGroup")
@audit_config_config_host_group_viewset(retrieve_owner=parent_service_from_lookup)
class ServiceConfigCHGViewSet(ConfigLogViewSet):
    ...


@document_action_viewset(object_type="service")
@audit_action_viewset(retrieve_owner=parent_service_from_lookup)
class ServiceActionViewSet(ActionViewSet):
    ...


@document_action_host_group_viewset(object_type="service")
class ServiceActionHostGroupViewSet(ActionHostGroupViewSet):
    ...


@document_action_host_group_hosts_viewset(object_type="service")
class ServiceActionHostGroupHostsViewSet(ActionHostGroupHostsViewSet):
    ...


@document_action_host_group_actions_viewset(object_type="service")
class ServiceActionHostGroupActionsViewSet(ActionHostGroupActionsViewSet):
    ...


@document_config_viewset(object_type="service")
@audit_config_viewset(type_in_name="Service", retrieve_owner=parent_service_from_lookup)
class ServiceConfigViewSet(ConfigLogViewSet):
    ...
