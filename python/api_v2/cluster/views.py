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
    VIEW_HC_PERM,
    VIEW_HOST_PERM,
    VIEW_SERVICE_PERM,
    check_custom_perm,
    get_object_for_user,
)
from audit.utils import audit
from cm.api import add_cluster, delete_cluster
from cm.errors import AdcmEx
from cm.models import (
    AnsibleConfig,
    Cluster,
    ClusterObject,
    ConcernType,
    Host,
    HostComponent,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from cm.services.cluster import retrieve_clusters_objects_maintenance_mode, retrieve_clusters_topology
from core.cluster.operations import calculate_maintenance_mode_for_cluster_objects
from core.cluster.types import MaintenanceModeOfObjects
from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from guardian.shortcuts import get_objects_for_user
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

from api_v2.api_schema import ErrorSerializer
from api_v2.cluster.filters import (
    ClusterFilter,
    ClusterHostFilter,
    ClusterServiceFilter,
)
from api_v2.cluster.permissions import ClusterPermissions
from api_v2.cluster.serializers import (
    AnsibleConfigRetrieveSerializer,
    AnsibleConfigUpdateSerializer,
    ClusterCreateSerializer,
    ClusterSerializer,
    ClusterUpdateSerializer,
    MappingSerializer,
    RelatedHostsStatusesSerializer,
    RelatedServicesStatusesSerializer,
    ServicePrototypeSerializer,
    SetMappingSerializer,
)
from api_v2.cluster.utils import retrieve_mapping_data, save_mapping
from api_v2.component.serializers import ComponentMappingSerializer
from api_v2.config.utils import ConfigSchemaMixin
from api_v2.host.serializers import HostMappingSerializer
from api_v2.views import ADCMGenericViewSet, ObjectWithStatusViewMixin


@extend_schema_view(
    list=extend_schema(
        summary="GET clusters",
        description="Get a list of ADCM clusters with information on them.",
        operation_id="getClusters",
    ),
    retrieve=extend_schema(
        summary="GET cluster",
        description="Get information about a specific cluster.",
        operation_id="getCluster",
        responses={
            200: ClusterSerializer,
            404: ErrorSerializer,
        },
    ),
    services_statuses=extend_schema(
        operation_id="getClusterServiceStatuses",
        summary="GET cluster service statuses",
        description="Get information about cluster service statuses.",
        responses={200: RelatedServicesStatusesSerializer, 404: ErrorSerializer},
        parameters=[
            OpenApiParameter(
                name="status",
                required=True,
                location=OpenApiParameter.QUERY,
                description="Case insensitive and partial filter by status.",
                type=str,
            ),
            OpenApiParameter(
                name="clusterId",
                required=True,
                location=OpenApiParameter.PATH,
                description="Cluster id.",
                type=int,
            ),
        ],
    ),
    hosts_statuses=extend_schema(
        operation_id="getClusterHostStatuses",
        summary="Get information about cluster host statuses.",
        description="Get information about cluster service statuses.",
        responses={200: RelatedServicesStatusesSerializer, 403: ErrorSerializer, 404: ErrorSerializer},
        parameters=[
            OpenApiParameter(
                name="status",
                required=True,
                location=OpenApiParameter.QUERY,
                description="Case insensitive and partial filter by status.",
                type=str,
            ),
            OpenApiParameter(
                name="clusterId",
                required=True,
                location=OpenApiParameter.PATH,
                description="Cluster id.",
                type=int,
            ),
        ],
    ),
)
class ClusterViewSet(
    PermissionListMixin,
    ConfigSchemaMixin,
    ListModelMixin,
    RetrieveModelMixin,
    ObjectWithStatusViewMixin,
    ADCMGenericViewSet,
):
    queryset = (
        Cluster.objects.prefetch_related("prototype", "concerns")
        .prefetch_related("clusterobject_set__prototype")
        .order_by("name")
    )
    permission_required = [VIEW_CLUSTER_PERM]
    filterset_class = ClusterFilter
    permission_classes = [ClusterPermissions]
    retrieve_status_map_actions = (
        "services_statuses",
        "hosts_statuses",
        "list",
    )

    def get_serializer_class(self):
        match self.action:
            case "create":
                return ClusterCreateSerializer
            case "partial_update":
                return ClusterUpdateSerializer
            case "service_prototypes" | "service_candidates":
                return ServicePrototypeSerializer
            case "mapping":
                return MappingSerializer
            case "mapping_hosts":
                return HostMappingSerializer
            case "mapping_components":
                return ComponentMappingSerializer
            case _:
                return ClusterSerializer

    @extend_schema(
        operation_id="postCluster",
        summary="POST cluster",
        description="Creates of a new ADCM cluster.",
        responses={201: ClusterSerializer, 400: ErrorSerializer, 403: ErrorSerializer, 409: ErrorSerializer},
    )
    @audit
    def create(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid = serializer.validated_data

        prototype = Prototype.objects.filter(pk=valid["prototype_id"], type=ObjectType.CLUSTER).first()

        if not prototype:
            raise AdcmEx(code="PROTOTYPE_NOT_FOUND", http_code=HTTP_409_CONFLICT)

        cluster = add_cluster(prototype=prototype, name=valid["name"], description=valid["description"])

        return Response(
            data=ClusterSerializer(cluster, context=self.get_serializer_context()).data, status=HTTP_201_CREATED
        )

    @extend_schema(
        operation_id="patchCluster",
        summary="PATCH cluster",
        description="Change cluster name.",
        responses={
            200: ClusterSerializer,
            400: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
    )
    @audit
    def partial_update(self, request, *args, **kwargs):  # noqa: ARG002
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data

        if valid_data.get("name") and instance.concerns.filter(type=ConcernType.LOCK).exists():
            raise AdcmEx(code="CLUSTER_CONFLICT", msg="Name change is available only if no locking concern exists")

        if valid_data.get("name") and valid_data.get("name") != instance.name and instance.state != "created":
            raise AdcmEx(code="CLUSTER_CONFLICT", msg="Name change is available only in the 'created' state")

        instance.name = valid_data.get("name", instance.name)
        instance.description = valid_data.get("description", instance.description)
        instance.save(update_fields=["name", "description"])

        return Response(
            status=HTTP_200_OK, data=ClusterSerializer(instance, context=self.get_serializer_context()).data
        )

    @extend_schema(
        operation_id="deleteCluster",
        summary="DELETE cluster",
        description="Delete a specific ADCM cluster.",
        responses={
            204: None,
            403: ErrorSerializer,
            404: ErrorSerializer,
        },
    )
    @audit
    def destroy(self, request, *args, **kwargs):  # noqa: ARG002
        cluster = self.get_object()
        delete_cluster(cluster=cluster)

        return Response(status=HTTP_204_NO_CONTENT)

    @extend_schema(
        operation_id="getServicePrototypes",
        summary="GET service prototypes",
        description="Get service prototypes that is related to this cluster.",
        responses={200: ServicePrototypeSerializer(many=True), 404: ErrorSerializer},
    )
    @action(methods=["get"], detail=True, url_path="service-prototypes", pagination_class=None)
    def service_prototypes(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        cluster = self.get_object()
        prototypes = Prototype.objects.filter(type=ObjectType.SERVICE, bundle=cluster.prototype.bundle).order_by(
            "display_name"
        )
        serializer = self.get_serializer_class()(instance=prototypes, many=True)

        return Response(data=serializer.data)

    @extend_schema(
        operation_id="getServiceCandidates",
        summary="GET service candidates",
        description="Get service prototypes that can be added to this cluster.",
        responses={200: ServicePrototypeSerializer(many=True), 404: ErrorSerializer},
    )
    @action(methods=["get"], detail=True, url_path="service-candidates", pagination_class=None)
    def service_candidates(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        cluster = self.get_object()
        prototypes = (
            Prototype.objects.filter(type=ObjectType.SERVICE, bundle=cluster.prototype.bundle)
            .exclude(id__in=cluster.clusterobject_set.all().values_list("prototype", flat=True))
            .order_by("display_name")
        )
        serializer = self.get_serializer_class()(instance=prototypes, many=True)

        return Response(data=serializer.data)

    @action(
        methods=["get"],
        detail=True,
        url_path="statuses/services",
        queryset=ClusterObject.objects.select_related("prototype").order_by("prototype__display_name"),
        permission_required=[VIEW_SERVICE_PERM],
        filterset_class=ClusterServiceFilter,
    )
    def services_statuses(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        cluster = get_object_for_user(user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["pk"])
        queryset = self.filter_queryset(queryset=self.get_queryset().filter(cluster=cluster))

        return self.get_paginated_response(
            data=RelatedServicesStatusesSerializer(
                instance=self.paginate_queryset(queryset=queryset), many=True, context=self.get_serializer_context()
            ).data
        )

    @action(
        methods=["get"],
        detail=True,
        url_path="statuses/hosts",
        queryset=Host.objects.order_by("fqdn"),
        permission_required=[VIEW_HOST_PERM],
        filterset_class=ClusterHostFilter,
    )
    def hosts_statuses(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        cluster = get_object_for_user(user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["pk"])
        queryset = self.filter_queryset(queryset=self.get_queryset().filter(cluster=cluster))

        return self.get_paginated_response(
            data=RelatedHostsStatusesSerializer(
                instance=self.paginate_queryset(queryset=queryset),
                many=True,
                context=self.get_serializer_context(),
            ).data
        )

    @extend_schema(
        methods=["get"],
        operation_id="getHostComponentMapping",
        summary="GET host component mapping",
        description="Get information about host and component mapping.",
        responses={200: MappingSerializer(many=True), 403: ErrorSerializer, 404: ErrorSerializer},
    )
    @extend_schema(
        methods=["post"],
        operation_id="postHostComponentMapping",
        summary="POST host component mapping",
        description="Save host and component mapping information.",
        request=SetMappingSerializer(many=True),
        responses={
            201: MappingSerializer(many=True),
            400: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
    )
    @audit
    @action(
        methods=["get", "post"],
        detail=True,
        pagination_class=None,
        filter_backends=[],
    )
    def mapping(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        cluster = self.get_object()

        check_custom_perm(
            user=request.user,
            action_type="view_host_components_of",
            model="cluster",
            obj=cluster,
            second_perm="view_hostcomponent",
        )

        if request.method == "GET":
            queryset = get_objects_for_user(user=request.user, perms=VIEW_HC_PERM, klass=HostComponent).filter(
                cluster=cluster
            )

            if not queryset.exists() and request.user.has_perm("cm.view_host_components_of_cluster", cluster):
                queryset = HostComponent.objects.filter(cluster=cluster)

            return Response(status=HTTP_200_OK, data=self.get_serializer(instance=queryset, many=True).data)

        if not request.user.has_perm("cm.edit_host_components_of_cluster", cluster):
            return Response(status=HTTP_403_FORBIDDEN)

        serializer = SetMappingSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        mapping_data = retrieve_mapping_data(cluster=cluster, plain_hc=serializer.validated_data)
        new_mapping = save_mapping(mapping_data=mapping_data)

        return Response(data=self.get_serializer(instance=new_mapping, many=True).data, status=HTTP_201_CREATED)

    @extend_schema(
        operation_id="getMappingHosts",
        summary="GET mapping hosts",
        description="Get a list of hosts to map.",
        responses={200: HostMappingSerializer(many=True), 404: ErrorSerializer},
    )
    @action(
        methods=["get"],
        pagination_class=None,
        filter_backends=[],
        detail=True,
        url_path="mapping/hosts",
        url_name="mapping-hosts",
    )
    def mapping_hosts(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        cluster = self.get_object()
        serializer = self.get_serializer(instance=Host.objects.filter(cluster=cluster).order_by("fqdn"), many=True)

        return Response(status=HTTP_200_OK, data=serializer.data)

    @extend_schema(
        operation_id="getMappingComponents",
        summary="GET mapping components",
        description="Get a list of components to map.",
        responses={200: ComponentMappingSerializer, 404: ErrorSerializer},
    )
    @action(
        methods=["get"],
        detail=True,
        pagination_class=None,
        filter_backends=[],
        url_path="mapping/components",
        url_name="mapping-components",
    )
    def mapping_components(self, request: Request, *args, **kwargs):  # noqa: ARG002
        cluster = self.get_object()

        is_mm_available = Prototype.objects.values_list("allow_maintenance_mode", flat=True).get(
            id=cluster.prototype_id
        )

        objects_mm = (
            calculate_maintenance_mode_for_cluster_objects(
                topology=next(retrieve_clusters_topology(cluster_ids=(cluster.id,))),
                own_maintenance_mode=retrieve_clusters_objects_maintenance_mode(cluster_ids=(cluster.id,)),
            )
            if is_mm_available
            else MaintenanceModeOfObjects(services={}, components={}, hosts={})
        )

        serializer = self.get_serializer(
            instance=(
                ServiceComponent.objects.filter(cluster=cluster)
                .select_related("prototype", "service__prototype")
                .order_by("pk")
            ),
            many=True,
            context={"mm": objects_mm, "is_mm_available": is_mm_available},
        )

        return Response(status=HTTP_200_OK, data=serializer.data)

    @extend_schema(
        methods=["get"],
        operation_id="getClusterAnsibleConfigs",
        summary="GET cluster ansible configuration",
        description="Get information about cluster ansible config.",
        responses={
            HTTP_200_OK: AnsibleConfigRetrieveSerializer,
            HTTP_403_FORBIDDEN: ErrorSerializer,
            HTTP_404_NOT_FOUND: ErrorSerializer,
        },
    )
    @extend_schema(
        methods=["post"],
        operation_id="postClusterAnsibleConfigs",
        summary="POST cluster ansible config",
        description="Create ansible configuration.",
        request=AnsibleConfigUpdateSerializer,
        responses={
            HTTP_201_CREATED: AnsibleConfigRetrieveSerializer,
            HTTP_400_BAD_REQUEST: ErrorSerializer,
            HTTP_403_FORBIDDEN: ErrorSerializer,
            HTTP_404_NOT_FOUND: ErrorSerializer,
            HTTP_409_CONFLICT: ErrorSerializer,
        },
    )
    @audit
    @action(methods=["get", "post"], detail=True, pagination_class=None, filter_backends=[], url_path="ansible-config")
    def ansible_config(self, request: Request, *args, **kwargs):  # noqa: ARG002
        cluster = self.get_object()
        ansible_config = AnsibleConfig.objects.get(
            object_id=cluster.pk, object_type=ContentType.objects.get_for_model(model=cluster)
        )

        if request.method.lower() == "get":
            check_custom_perm(
                user=request.user,
                action_type="view_ansible_config_of",
                model="cluster",
                obj=cluster,
                second_perm="view_ansible_config_of_cluster",
            )

            return Response(status=HTTP_200_OK, data=AnsibleConfigRetrieveSerializer(instance=ansible_config).data)

        check_custom_perm(user=request.user, action_type="change_ansible_config_of", model="cluster", obj=cluster)
        serializer = AnsibleConfigUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ansible_config.value = serializer.validated_data["config"]
        ansible_config.save(update_fields=["value"])

        return Response(status=HTTP_201_CREATED, data=AnsibleConfigRetrieveSerializer(instance=ansible_config).data)

    @extend_schema(
        methods=["get"],
        operation_id="getClusterAnsibleConfigs",
        summary="GET cluster ansible configuration",
        description="Get information about cluster ansible config.",
        responses={
            HTTP_200_OK: dict,
            HTTP_404_NOT_FOUND: ErrorSerializer,
        },
    )
    @action(methods=["get"], detail=True, pagination_class=None, filter_backends=[], url_path="ansible-config-schema")
    def ansible_config_schema(self, request: Request, *args, **kwargs):  # noqa: ARG002
        adcm_meta_part = {
            "isAdvanced": False,
            "isInvisible": False,
            "activation": None,
            "synchronization": None,
            "NoneValue": None,
            "isSecret": False,
            "stringExtra": None,
            "enumExtra": None,
        }
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Ansible configuration",
            "description": "",
            "readOnly": False,
            "adcmMeta": adcm_meta_part,
            "type": "object",
            "properties": {
                "defaults": {
                    "title": "defaults",
                    "type": "object",
                    "description": "",
                    "default": {},
                    "readOnly": False,
                    "adcmMeta": adcm_meta_part,
                    "additionalProperties": False,
                    "properties": {
                        "forks": {
                            "title": "forks",
                            "type": "integer",
                            "description": "",
                            "default": 5,
                            "readOnly": False,
                            "adcmMeta": adcm_meta_part,
                            "minimum": 1,
                        },
                    },
                    "required": [
                        "forks",
                    ],
                },
            },
            "additionalProperties": False,
            "required": [
                "defaults",
            ],
        }

        return Response(status=HTTP_200_OK, data=schema)
