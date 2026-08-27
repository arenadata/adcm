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

from collections.abc import Collection

from adcm.permissions import (
    VIEW_CLUSTER_PERM,
    VIEW_HC_PERM,
    VIEW_HOST_PERM,
    VIEW_IMPORT_PERM,
    VIEW_SERVICE_PERM,
    ChangeMMPermissions,
    IsAuthenticatedAudit,
    check_custom_perm,
    get_object_for_user,
)
from audit.alt.api import audit_create, audit_delete, audit_update, audit_view
from audit.alt.hooks import (
    adjust_denied_on_404_result,
    extract_current_from_response,
    extract_from_object,
    extract_previous_from_object,
    only_on_success,
)
from cm.errors import AdcmEx
from cm.legacy.api import delete_cluster, remove_host_from_cluster
from cm.legacy.services.bundle import retrieve_bundle_restrictions
from cm.legacy.services.cluster import (
    ClusterDB,
    perform_host_to_cluster_map,
)
from cm.legacy.services.mapping import set_host_component_mapping
from cm.models import (
    AnsibleConfig,
    Bundle,
    Cluster,
    Component,
    ConcernType,
    Host,
    HostComponent,
    MaintenanceMode,
    ObjectType,
    Prototype,
    Service,
)
from cm.transition.status import StatusScenarios
from core.cluster import ClusterService
from core.concern.repo import ConcernRepoI
from core.legacy.bundle.operations import build_requires_dependencies_map
from core.legacy.cluster.operations import find_host_candidates_for_cluster
from core.legacy.cluster.types import HostComponentEntry
from core.types import (
    ADCMCoreType,
    ClusterID,
    ComponentNameKey,
    Descriptor,
    MaintenanceModeOfObjects,
    MaintenanceModeState,
    ServiceNameKey,
)
from dishka import FromDishka
from django.contrib.contenttypes.models import ContentType
from django.db.models import Case, CharField, Q, QuerySet, Value, When
from django.db.transaction import atomic
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from guardian.shortcuts import get_objects_for_user
from rbac.scenarios import RBACScenarios
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
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
from use_cases.cluster.maintenance_mode import SetMaintenanceMode
from use_cases.transition.cluster.create import CreateCluster

from api_v2.api_schema import DefaultParams, exclude_params, responses
from api_v2.cluster.depend_on import prepare_depend_on_hierarchy, retrieve_serialized_depend_on_hierarchy
from api_v2.cluster.filters import (
    ClusterFilter,
    ClusterMappingComponentFilter,
    ClusterMappingHostFilter,
    ClusterServiceCandidateAndPrototypeFilter,
    ClusterStatusesHostFilter,
    ClusterStatusesServiceFilter,
)
from api_v2.cluster.permissions import ClusterPermissions, HostsClusterPermissions
from api_v2.cluster.serializers import (
    AnsibleConfigRetrieveSerializer,
    AnsibleConfigUpdateSerializer,
    ClusterCreateSerializer,
    ClusterHostStatusSerializer,
    ClusterSerializer,
    ClusterUpdateSerializer,
    ComponentMappingSerializer,
    MappingSerializer,
    RelatedHostsStatusesSerializer,
    RelatedServicesStatusesSerializer,
    ServicePrototypeSerializer,
    SetMappingSerializer,
)
from api_v2.generic.action.api_schema import document_action_viewset
from api_v2.generic.action.audit import audit_action_viewset
from api_v2.generic.action.process.api_schema import (
    document_action_process_step_viewset,
    document_action_process_viewset,
)
from api_v2.generic.action.process.audit import audit_action_process_viewset
from api_v2.generic.action.process.views import ActionProcessViewSet, ProcessStepViewSet
from api_v2.generic.action.views import ActionViewSet
from api_v2.generic.action_host_group.api_schema import (
    document_action_host_group_actions_viewset,
    document_action_host_group_hosts_viewset,
    document_action_host_group_viewset,
)
from api_v2.generic.action_host_group.audit import audit_action_host_group_viewset
from api_v2.generic.action_host_group.views import (
    ActionHostGroupActionsViewSet,
    ActionHostGroupHostsViewSet,
    ActionHostGroupViewSet,
)
from api_v2.generic.config.api_schema import document_config_viewset
from api_v2.generic.config.audit import audit_config_viewset
from api_v2.generic.config.utils import ConfigSchemaMixin, extend_config_schema
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
from api_v2.generic.upgrade.api_schema import document_upgrade_viewset
from api_v2.generic.upgrade.audit import audit_upgrade_viewset
from api_v2.generic.upgrade.views import UpgradeViewSet
from api_v2.host.filters import ClusterHostFilter
from api_v2.host.serializers import (
    HostAddSerializer,
    HostChangeMaintenanceModeSerializer,
    HostMappingSerializer,
    HostSerializer,
    HostShortSerializer,
    ManyHostAddSerializer,
)
from api_v2.utils.audit import (
    cluster_from_lookup,
    cluster_from_response,
    host_from_lookup,
    nested_host_does_exist,
    parent_cluster_from_lookup,
    parent_host_from_lookup,
    retrieve_cluster_ansible_config_from_object,
    retrieve_cluster_ansible_config_from_response,
    set_add_hosts_name,
    set_removed_host_name,
    update_cluster_name,
)
from api_v2.utils.di import inject
from api_v2.views import ADCMGenericViewSet, ClusterHostOperationHandleExceptionMixin, ObjectWithStatusViewMixin


@extend_schema_view(
    create=extend_schema(
        operation_id="postCluster",
        summary="POST cluster",
        description="Create a new ADCM cluster.",
        responses=responses(
            success=(HTTP_201_CREATED, ClusterSerializer),
            errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_409_CONFLICT),
        ),
    ),
    list=extend_schema(
        summary="GET clusters",
        description="Get a list of ADCM clusters with information on them.",
        operation_id="getClusters",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                enum=(
                    "name",
                    "-name",
                    "prototypeDisplayName",
                    "-prototypeDisplayName",
                    "state",
                    "-state",
                    "prototypeVersion",
                    "-prototypeVersion",
                ),
                default="name",
            ),
            *exclude_params(names=["id"]),
        ],
        responses=responses(success=ClusterSerializer(many=True)),
    ),
    retrieve=extend_schema(
        summary="GET cluster",
        description="Get information about a specific cluster.",
        operation_id="getCluster",
        responses=responses(success=ClusterSerializer, errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)),
    ),
    partial_update=extend_schema(
        operation_id="patchCluster",
        summary="PATCH cluster",
        description="Change cluster name.",
        responses=responses(
            success=ClusterSerializer,
            errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
        ),
    ),
    destroy=extend_schema(
        operation_id="deleteCluster",
        summary="DELETE cluster",
        description="Delete a specific ADCM cluster.",
        responses=responses(success=None, errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)),
    ),
    services_statuses=extend_schema(
        operation_id="getClusterServiceStatuses",
        summary="Get information about cluster service statuses.",
        description="Get information about cluster service statuses.",
        responses=responses(success=RelatedServicesStatusesSerializer(many=True), errors=(HTTP_404_NOT_FOUND,)),
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(
                name="status",
                description="Filter by status",
                enum=("up", "down"),
            ),
            OpenApiParameter(
                name="ordering",
                description="Field to sort by. To sort in descending order, precede the attribute name with a '-'.",
                enum=(
                    "id",
                    "-id",
                ),
                default="id",
            ),
        ],
    ),
    service_prototypes=extend_schema(
        operation_id="getServicePrototypes",
        summary="GET service prototypes",
        description="Get service prototypes that is related to this cluster.",
        responses=responses(success=ServicePrototypeSerializer(many=True)),
    ),
    service_candidates=extend_schema(
        operation_id="getServiceCandidates",
        summary="GET service candidates",
        description="Get service prototypes that can be added to this cluster.",
        responses=responses(success=ServicePrototypeSerializer(many=True)),
    ),
    hosts_statuses=extend_schema(
        operation_id="getClusterHostStatuses",
        summary="Get information about cluster hosts statuses.",
        description="Get information about cluster hosts statuses.",
        responses=responses(success=RelatedHostsStatusesSerializer(many=True), errors=(HTTP_404_NOT_FOUND,)),
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(
                name="status",
                description="Filter by status",
                enum=("up", "down"),
            ),
            OpenApiParameter(
                name="ordering",
                description="Field to sort by. To sort in descending order, precede the attribute name with a '-'.",
                enum=(
                    "id",
                    "-id",
                ),
                default="id",
            ),
        ],
    ),
    mapping_hosts=extend_schema(
        operation_id="getMappingHosts",
        summary="GET mapping hosts",
        description="Get a list of hosts to map.",
        responses=responses(success=HostMappingSerializer(many=True), errors=HTTP_404_NOT_FOUND),
    ),
    mapping_components=extend_schema(
        operation_id="getMappingComponents",
        summary="GET mapping components",
        description="Get a list of components to map.",
        responses=responses(success=ComponentMappingSerializer(many=True), errors=HTTP_404_NOT_FOUND),
    ),
    ansible_config_schema=extend_schema(
        methods=["get"],
        operation_id="getClusterAnsibleConfigsSchema",
        summary="GET cluster ansible configuration schema",
        description="Get information about cluster ansible config schema.",
        examples=DefaultParams.CONFIG_SCHEMA_EXAMPLE,
        responses=responses(success=dict),
    ),
    config_schema=extend_config_schema("cluster"),
    host_candidates=extend_schema(
        methods=["get"],
        operation_id="getClusterHostCandidates",
        description="Get a list of hosts candidates.",
        responses=responses(success=HostShortSerializer(many=True), errors=HTTP_404_NOT_FOUND),
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
        Cluster.objects.prefetch_related("prototype", "prototype__bundle", "concerns")
        .prefetch_related("services__prototype")
        .order_by("name")
    )
    permission_required = [VIEW_CLUSTER_PERM]
    filterset_class = ClusterFilter
    permission_classes = [IsAuthenticated, ClusterPermissions]
    retrieve_status_map_actions = (
        "services_statuses",
        "hosts_statuses",
        "list",
    )

    def get_queryset(self, *args, **kwargs):
        if self.action in ["service_prototypes", "service_candidates"]:
            return Prototype.objects.none()
        return super().get_queryset(*args, **kwargs)

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

    @audit_create(name="Cluster created", object_=cluster_from_response)
    @inject
    def create(self, request, create_cluster: FromDishka[CreateCluster], **_):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid = serializer.validated_data

        prototype = Prototype.objects.filter(pk=valid["prototype_id"], type=ObjectType.CLUSTER).first()

        if not prototype:
            raise AdcmEx(code="PROTOTYPE_NOT_FOUND", http_code=HTTP_409_CONFLICT)

        cluster_id = create_cluster.do(prototype=prototype, name=valid["name"], description=valid["description"])
        cluster = Cluster.objects.get(id=cluster_id)

        return Response(
            data=ClusterSerializer(cluster, context=self.get_serializer_context()).data, status=HTTP_201_CREATED
        )

    @(
        audit_update(name="Cluster updated", object_=cluster_from_lookup)
        .attach_hooks(on_collect=only_on_success(update_cluster_name))
        .track_changes(
            before=extract_previous_from_object(Cluster, "name", "description"),
            after=extract_current_from_response("name", "description"),
        )
    )
    @inject
    def partial_update(
        self,
        request,
        *args,  # noqa: ARG002
        status_scenarios: FromDishka[StatusScenarios],
        concern_repo: FromDishka[ConcernRepoI],
        **kwargs,  # noqa: ARG002
    ):
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data

        added = {}

        with atomic():
            if valid_data.get("name") and instance.concerns.filter(type=ConcernType.LOCK).exists():
                raise AdcmEx(code="CLUSTER_CONFLICT", msg="Name change is available only if no locking concern exists")

            if valid_data.get("name") and valid_data.get("name") != instance.name and instance.state != "created":
                raise AdcmEx(code="CLUSTER_CONFLICT", msg="Name change is available only in the 'created' state")

            previous_name = instance.name

            instance.name = valid_data.get("name", instance.name)
            instance.description = valid_data.get("description", instance.description)
            instance.save(update_fields=["name", "description"])

            if instance.name != previous_name:
                renamed_in_concerns = concern_repo.update_object_name_in_concerns(
                    object_=Descriptor(id=instance.pk, type=ADCMCoreType.CLUSTER),
                    previous_name=previous_name,
                    new_name=instance.name,
                )
                added = concern_repo.get_concerns_distribution(concern_ids=renamed_in_concerns)

        if added:
            # concerns with updated names are sent to UI as new ones, there's no event for their update
            status_scenarios.notify_about_redistributed_concerns_from_maps(added=added, removed={})

        status_scenarios.send_object_update_event(
            instance.pk,
            ADCMCoreType.CLUSTER.value,
            changes={"name": instance.name, "description": instance.description},
        )

        return Response(
            status=HTTP_200_OK, data=ClusterSerializer(instance, context=self.get_serializer_context()).data
        )

    @audit_delete(name="Cluster deleted", object_=cluster_from_lookup, removed_on_success=True)
    @inject
    def destroy(self, request, *args, cluster_service: FromDishka[ClusterService], **kwargs):  # noqa: ARG002
        cluster = self.get_object()
        delete_cluster(cluster=cluster, cluster_service=cluster_service)

        return Response(status=HTTP_204_NO_CONTENT)

    @action(
        methods=["get"],
        detail=True,
        url_path="service-prototypes",
        pagination_class=None,
        filterset_class=ClusterServiceCandidateAndPrototypeFilter,
    )
    def service_prototypes(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        cluster = Cluster.objects.get(pk=kwargs["pk"])
        return self._respond_with_prototypes(cluster_prototype_id=cluster.prototype_id)

    @action(
        methods=["get"],
        detail=True,
        url_path="service-candidates",
        pagination_class=None,
        filterset_class=ClusterServiceCandidateAndPrototypeFilter,
    )
    def service_candidates(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        cluster = Cluster.objects.get(pk=kwargs["pk"])
        exclude_added_service_prototypes = Q(
            id__in=Service.objects.values_list("prototype_id", flat=True).filter(cluster_id=cluster.id)
        )
        return self._respond_with_prototypes(
            cluster_prototype_id=cluster.prototype_id, exclude_clause=exclude_added_service_prototypes
        )

    def _respond_with_prototypes(self, cluster_prototype_id: int, exclude_clause: Q | None = None) -> Response:
        exclude_clause = exclude_clause or Q()
        bundle_id = Prototype.objects.values_list("bundle_id", flat=True).get(id=cluster_prototype_id)

        prototypes = (
            Prototype.objects.filter(type=ObjectType.SERVICE, bundle_id=bundle_id)
            .exclude(exclude_clause)
            .order_by("display_name")
        )

        prototypes = self.filter_queryset(queryset=prototypes)

        context = {"depend_on": {}}

        if any(proto.requires for proto in tuple(prototypes)):
            requires_dependencies = build_requires_dependencies_map(retrieve_bundle_restrictions(bundle_id))
            bundle_hash = Bundle.objects.values_list("hash", flat=True).get(id=bundle_id)
            context["depend_on"] = retrieve_serialized_depend_on_hierarchy(
                hierarchy=prepare_depend_on_hierarchy(
                    dependencies=requires_dependencies,
                    targets=((proto.id, ServiceNameKey(service=proto.name)) for proto in prototypes),
                ),
                bundle_id=bundle_id,
                bundle_hash=bundle_hash,
            )

        serializer = self.get_serializer_class()(instance=prototypes, many=True, context=context)

        return Response(data=serializer.data)

    @action(
        methods=["get"],
        detail=True,
        url_path="statuses/services",
        queryset=Service.objects.select_related("prototype").order_by("prototype__display_name"),
        permission_required=[VIEW_SERVICE_PERM],
        filterset_class=ClusterStatusesServiceFilter,
    )
    @inject
    def services_statuses(
        self,
        request: Request,
        cluster_service: FromDishka[ClusterService],
        *args,  # noqa: ARG002
        **kwargs,
    ) -> Response:
        cluster = get_object_for_user(user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["pk"])
        queryset = self.filter_queryset(
            queryset=self._annotate_services_with_maintenance_mode(
                cluster_id=cluster.pk, qs=self.get_queryset().filter(cluster=cluster), cluster_service=cluster_service
            )
        )

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
        filterset_class=ClusterStatusesHostFilter,
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
        responses=responses(success=MappingSerializer(many=True), errors=HTTP_404_NOT_FOUND),
    )
    @extend_schema(
        methods=["post"],
        operation_id="postHostComponentMapping",
        summary="POST host component mapping",
        description="Save host and component mapping information.",
        request=SetMappingSerializer(many=True),
        responses=responses(
            success=(HTTP_201_CREATED, MappingSerializer(many=True)),
            errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
        ),
    )
    @audit_update(name="Host-Component map updated", object_=cluster_from_lookup)
    @action(
        methods=["get", "post"],
        detail=True,
        pagination_class=None,
        filter_backends=[],
    )
    @inject
    def mapping(self, request: Request, *args, cluster_service: FromDishka[ClusterService], **kwargs) -> Response:  # noqa: ARG002
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

        new_mapping_entries = tuple(HostComponentEntry(**entry) for entry in serializer.validated_data)
        if len(new_mapping_entries) != len(set(new_mapping_entries)):
            checked = set()
            duplicates = set()

            for entry in new_mapping_entries:
                if entry in checked:
                    duplicates.add(entry)
                else:
                    checked.add(entry)

            error_mapping_repr = ", ".join(
                f"component {entry.component_id} - host {entry.host_id}" for entry in sorted(duplicates)
            )
            raise AdcmEx("INVALID_INPUT", msg=f"Mapping entries duplicates found: {error_mapping_repr}.")

        cluster_id = cluster.id
        bundle_id = Prototype.objects.values_list("bundle_id", flat=True).get(id=cluster.prototype_id)

        set_host_component_mapping(
            cluster_id=cluster_id, bundle_id=bundle_id, new_mapping=new_mapping_entries, cluster_service=cluster_service
        )

        return Response(
            data=self.get_serializer(instance=HostComponent.objects.filter(cluster_id=cluster_id), many=True).data,
            status=HTTP_201_CREATED,
        )

    @action(
        methods=["get"],
        pagination_class=None,
        filterset_class=ClusterMappingHostFilter,
        detail=True,
        url_path="mapping/hosts",
        url_name="mapping-hosts",
    )
    def mapping_hosts(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        cluster = get_object_for_user(user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["pk"])
        queryset = self.filter_queryset(queryset=Host.objects.filter(cluster=cluster).order_by("fqdn"))
        serializer = self.get_serializer(instance=queryset, many=True)

        return Response(status=HTTP_200_OK, data=serializer.data)

    @action(
        methods=["get"],
        detail=True,
        pagination_class=None,
        filterset_class=ClusterMappingComponentFilter,
        url_path="mapping/components",
        url_name="mapping-components",
    )
    @inject
    def mapping_components(
        self,
        request: Request,
        *args,  # noqa: ARG002
        cluster_service: FromDishka[ClusterService],
        **kwargs,
    ):
        cluster = get_object_for_user(user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["pk"])
        bundle_id, is_mm_available = Prototype.objects.values_list("bundle_id", "allow_maintenance_mode").get(
            id=cluster.prototype_id
        )

        if is_mm_available:
            objects_mm = cluster_service.calculate_maintenance_mode(
                topology=cluster_service.retrieve_topology(cluster_id=cluster.pk),
                objects_own_mm=cluster_service.retrieve_own_maintenance_mode(cluster_ids=(cluster.pk,)),
            )
        else:
            objects_mm = MaintenanceModeOfObjects(services={}, components={}, hosts={})

        components = self.filter_queryset(
            queryset=Component.objects.filter(cluster=cluster)
            .select_related("prototype", "prototype__parent", "service__prototype")
            .order_by("pk")
        )

        context = {"mm": objects_mm, "is_mm_available": is_mm_available, "depend_on": {}}

        if any(component.prototype.requires for component in components):
            requires_dependencies = build_requires_dependencies_map(retrieve_bundle_restrictions(bundle_id))
            bundle_hash = Bundle.objects.values_list("hash", flat=True).get(id=bundle_id)
            context["depend_on"] = retrieve_serialized_depend_on_hierarchy(
                hierarchy=prepare_depend_on_hierarchy(
                    dependencies=requires_dependencies,
                    targets=(
                        (
                            component.id,
                            ComponentNameKey(
                                service=component.prototype.parent.name, component=component.prototype.name
                            ),
                        )
                        for component in components
                    ),
                ),
                bundle_id=bundle_id,
                bundle_hash=bundle_hash,
            )

        serializer = self.get_serializer(instance=components, many=True, context=context)

        return Response(status=HTTP_200_OK, data=serializer.data)

    @extend_schema(
        methods=["get"],
        operation_id="getClusterAnsibleConfigs",
        summary="GET cluster ansible configuration",
        description="Get information about cluster ansible config.",
        responses=responses(success=AnsibleConfigRetrieveSerializer, errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)),
    )
    @extend_schema(
        methods=["post"],
        operation_id="postClusterAnsibleConfigs",
        summary="POST cluster ansible config",
        description="Create ansible configuration.",
        request=AnsibleConfigUpdateSerializer,
        responses=responses(
            success=(HTTP_201_CREATED, AnsibleConfigRetrieveSerializer),
            errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
        ),
    )
    @audit_update(name="Ansible configuration updated", object_=cluster_from_lookup).track_changes(
        before=extract_from_object(func=retrieve_cluster_ansible_config_from_object, section="previous"),
        after=retrieve_cluster_ansible_config_from_response(),
    )
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

    @action(methods=["get"], detail=True, pagination_class=None, filter_backends=[], url_path="host-candidates")
    def host_candidates(self, request, *_, **kwargs):
        cluster = get_object_for_user(user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["pk"])
        candidates = find_host_candidates_for_cluster(cluster_id=cluster.pk, db=ClusterDB)
        hosts_allowed_for_user_query = get_objects_for_user(user=request.user, perms=VIEW_HOST_PERM, klass=Host)
        candidates_allowed_for_user = hosts_allowed_for_user_query.filter(id__in=(c.id for c in candidates)).order_by(
            "fqdn"
        )
        serializer = HostShortSerializer(instance=candidates_allowed_for_user, many=True)
        return Response(data=serializer.data, status=HTTP_200_OK)

    @staticmethod
    def _annotate_services_with_maintenance_mode(
        cluster_id: ClusterID, qs: QuerySet[Service], cluster_service: ClusterService
    ) -> QuerySet[Service]:
        services_mm = cluster_service.calculate_maintenance_mode(
            topology=cluster_service.retrieve_topology(cluster_id=cluster_id),
            objects_own_mm=cluster_service.retrieve_own_maintenance_mode(cluster_ids=(cluster_id,)),
        ).services

        return qs.annotate(
            calculated_mm=Case(
                *(When(id=service_id, then=Value(mm.state.value)) for service_id, mm in services_mm.items()),
                # default is required for case without services when filter by MM is used (ADCM-8390)
                default=Value(MaintenanceMode.OFF.value),
                output_field=CharField(),
            )
        )


@extend_schema_view(
    list=extend_schema(
        operation_id="getClusterHosts",
        description="Get a list of all cluster hosts.",
        summary="GET cluster hosts",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                enum=(
                    "name",
                    "-name",
                    "state",
                    "-state",
                    "id",
                    "-id",
                    "hostproviderName",
                    "-hostproviderName",
                ),
                default="name",
            ),
        ],
        responses=responses(success=HostSerializer(many=True), errors=(HTTP_404_NOT_FOUND,)),
    ),
    create=extend_schema(
        operation_id="postCusterHosts",
        description="Add a new hosts to cluster.",
        summary="POST cluster hosts",
        request=ManyHostAddSerializer,
        responses=responses(
            success=(HTTP_201_CREATED, DefaultParams.ADD_HOST_TO_CLUSTER_RESPONSE_SCHEMA),
            errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
        ),
    ),
    retrieve=extend_schema(
        operation_id="getClusterHost",
        description="Get information about a specific cluster host.",
        summary="GET cluster host",
        responses=responses(success=HostSerializer, errors=(HTTP_404_NOT_FOUND,)),
    ),
    destroy=extend_schema(
        operation_id="deleteClusterHost",
        description="Unlink host from cluster.",
        summary="DELETE cluster host",
        responses=responses(
            success=(HTTP_204_NO_CONTENT, None),
            errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
        ),
    ),
    maintenance_mode=extend_schema(
        operation_id="postClusterHostMaintenanceMode",
        description="Turn on/off maintenance mode on the cluster host.",
        summary="POST cluster host maintenance-mode",
        responses=responses(
            success=HostChangeMaintenanceModeSerializer,
            errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
        ),
    ),
    statuses=extend_schema(
        operation_id="getHostStatuses",
        description="Get information about cluster host status.",
        summary="GET host status",
        responses=responses(success=ClusterHostStatusSerializer, errors=(HTTP_404_NOT_FOUND,)),
    ),
)
class HostClusterViewSet(
    ClusterHostOperationHandleExceptionMixin,
    PermissionListMixin,
    ObjectWithStatusViewMixin,
    RetrieveModelMixin,
    ListModelMixin,
    ADCMGenericViewSet,
):
    permission_required = [VIEW_HOST_PERM]
    permission_classes = [IsAuthenticated, HostsClusterPermissions]
    # have to define it here for `ObjectWithStatusViewMixin` to be able to determine model related to view
    # don't use it directly, use `get_queryset`
    queryset = (
        Host.objects.select_related("cluster", "cluster__prototype", "provider", "prototype")
        .prefetch_related("concerns", "hostcomponent_set__component__prototype")
        .order_by("fqdn")
    )
    filterset_class = ClusterHostFilter
    audit_model_hint = Host
    retrieve_status_map_actions = ("list", "statuses")

    def get_serializer_class(self):
        if self.action == "maintenance_mode":
            return HostChangeMaintenanceModeSerializer

        if self.action == "create":
            return HostAddSerializer

        return HostSerializer

    def get_queryset(self, *_, **__):
        cluster = get_object_for_user(
            user=self.request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=self.kwargs["cluster_pk"]
        )

        by_cluster_qs = (
            get_objects_for_user(**self.get_get_objects_for_user_kwargs(self.queryset))
            .filter(cluster=cluster)
            .order_by("fqdn")
        )

        if self.action == "statuses":
            return by_cluster_qs.prefetch_related("hostcomponent_set__component__prototype")

        return by_cluster_qs

    @audit_update(name="[{}] host(s) added", object_=parent_cluster_from_lookup).attach_hooks(
        pre_call=set_add_hosts_name
    )
    @inject
    def create(
        self,
        request,
        *_,
        status_scenarios: FromDishka[StatusScenarios],
        rbac_scenarios: FromDishka[RBACScenarios],
        **kwargs,
    ):
        cluster = get_object_for_user(
            user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["cluster_pk"]
        )

        check_custom_perm(request.user, "map_host_to", "cluster", cluster)

        multiple_hosts = isinstance(request.data, list)

        serializer = self.get_serializer(data=request.data, many=multiple_hosts)
        serializer.is_valid(raise_exception=True)

        added_hosts: Collection[int] = perform_host_to_cluster_map(
            cluster_id=cluster.pk,
            hosts=[
                entry["host_id"]
                for entry in (serializer.validated_data if multiple_hosts else [serializer.validated_data])
            ],
            status_service=status_scenarios,
            rbac_scenarios=rbac_scenarios,
        )

        qs_for_added_hosts = self.get_queryset().filter(id__in=added_hosts)
        return Response(
            status=HTTP_201_CREATED,
            data=HostSerializer(
                instance=qs_for_added_hosts if multiple_hosts else qs_for_added_hosts.first(),
                many=multiple_hosts,
                context=self.get_serializer_context(),
            ).data,
        )

    @(
        audit_update(name="Host removed", object_=parent_cluster_from_lookup).attach_hooks(
            pre_call=set_removed_host_name, on_collect=adjust_denied_on_404_result(objects_exist=nested_host_does_exist)
        )
    )
    @inject
    def destroy(
        self,
        request,
        *args,  # noqa: ARG002
        cluster_service: FromDishka[ClusterService],
        rbac_scenarios: FromDishka[RBACScenarios],
        **kwargs,
    ):
        host = self.get_object()
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_pk"])
        check_custom_perm(request.user, "unmap_host_from", "cluster", cluster)
        remove_host_from_cluster(host=host, rbac_scenarios=rbac_scenarios, cluster_service=cluster_service)
        return Response(status=HTTP_204_NO_CONTENT)

    @audit_update(name="Host updated", object_=host_from_lookup).track_changes(
        before=extract_previous_from_object(Host, "maintenance_mode"),
        after=extract_current_from_response("maintenance_mode"),
    )
    @action(
        methods=["post"],
        detail=True,
        url_path="maintenance-mode",
        permission_classes=[IsAuthenticatedAudit, ChangeMMPermissions],
    )
    @inject
    def maintenance_mode(
        self,
        request: Request,
        *args,  # noqa: ARG002
        set_mm: FromDishka[SetMaintenanceMode],
        **kwargs,  # noqa: ARG002
    ) -> Response:
        host = self.get_object()

        check_custom_perm(user=request.user, action_type="change_maintenance_mode", model="host", obj=host)

        serializer = self.get_serializer_class()(instance=host, data=request.data)
        serializer.is_valid(raise_exception=True)

        value = set_mm.do(target=host, value=MaintenanceModeState(serializer.validated_data["maintenance_mode"]))

        return Response(data={"maintenance_mode": value.value})

    @action(methods=["get"], detail=True, url_path="statuses")
    def statuses(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        host = self.get_object()
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_pk"])
        if host.cluster != cluster:
            raise AdcmEx(code="FOREIGN_HOST", msg=f"Host #{host.id} doesn't belong to cluster #{cluster.id}")

        return Response(
            data=ClusterHostStatusSerializer(
                instance=Host.objects.prefetch_related("hostcomponent_set__component__prototype").get(id=host.id),
                context=self.get_serializer_context(),
            ).data
        )


@extend_schema_view(
    list=extend_schema(
        operation_id="getClusterImports",
        description="Get information about cluster imports.",
        summary="GET cluster imports",
        parameters=[DefaultParams.LIMIT, DefaultParams.OFFSET],
        responses=responses(success=ImportSerializer(many=True), errors=HTTP_403_FORBIDDEN),
    ),
    create=extend_schema(
        operation_id="postClusterImports",
        description="Import data.",
        summary="POST cluster imports",
        responses=responses(
            success=(HTTP_201_CREATED, ImportPostSerializer),
            errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
        ),
    ),
)
@audit_view(create=audit_update(name="Cluster import updated", object_=parent_cluster_from_lookup))
class ClusterImportViewSet(ImportViewSet):
    def detect_get_check_kwargs(self) -> tuple[dict, dict]:
        return (
            {"perms": VIEW_CLUSTER_PERM, "klass": Cluster, "id": self.kwargs["cluster_pk"]},
            {"action_type": VIEW_IMPORT_PERM, "model": Cluster.__name__.lower()},
        )

    def detect_cluster_service_bind_arguments(self, obj: Cluster) -> tuple[Cluster, None]:
        return obj, None


@document_config_host_group_viewset(object_type="cluster")
@audit_config_host_group_viewset(retrieve_owner=parent_cluster_from_lookup)
class ClusterCHGViewSet(CHGViewSet):
    ...


@document_host_config_host_group_viewset(object_type="cluster")
@audit_host_config_host_group_viewset(retrieve_owner=parent_cluster_from_lookup)
class ClusterHostCHGViewSet(HostCHGViewSet):
    ...


@document_config_viewset(object_type="cluster config group", operation_id_variant="ClusterConfigGroup")
@audit_config_config_host_group_viewset(retrieve_owner=parent_cluster_from_lookup)
class ClusterConfigCHGViewSet(ConfigLogViewSet):
    ...


@document_action_viewset(object_type="cluster")
@audit_action_viewset(retrieve_owner=parent_cluster_from_lookup)
class ClusterActionViewSet(ActionViewSet):
    ...


@document_action_viewset(object_type="hostInCluster")
@audit_action_viewset(retrieve_owner=parent_host_from_lookup)
class ClusterHostActionViewSet(ActionViewSet):
    ...


@document_action_host_group_viewset(object_type="cluster")
@audit_action_host_group_viewset(parent_cluster_from_lookup)
class ClusterActionHostGroupViewSet(ActionHostGroupViewSet):
    ...


@document_action_host_group_hosts_viewset(object_type="cluster")
class ClusterActionHostGroupHostsViewSet(ActionHostGroupHostsViewSet):
    ...


@document_action_host_group_actions_viewset(object_type="cluster")
class ClusterActionHostGroupActionsViewSet(ActionHostGroupActionsViewSet):
    ...


@document_action_process_viewset(object_type="clusterActionHostGroup", operation_id_variant="ClusterActionHostGroup")
@audit_action_process_viewset(retrieve_owner=parent_cluster_from_lookup)
class ClusterActionHostGroupActionsProcessViewSet(ActionProcessViewSet):
    ...


@document_action_process_step_viewset(
    object_type="clusterActionHostGroup", operation_id_variant="ClusterActionHostGroup"
)
class ClusterActionHostGroupActionsProcessStepViewSet(ProcessStepViewSet):
    ...


@document_config_viewset(object_type="cluster")
@audit_config_viewset(type_in_name="Cluster", retrieve_owner=parent_cluster_from_lookup)
class ClusterConfigViewSet(ConfigLogViewSet):
    ...


@document_upgrade_viewset(object_type="cluster")
@audit_upgrade_viewset(retrieve_owner=parent_cluster_from_lookup)
class ClusterUpgradeViewSet(UpgradeViewSet):
    ...


@audit_action_process_viewset(retrieve_owner=parent_cluster_from_lookup)
@document_action_process_viewset(object_type="cluster")
class ClusterActionProcessViewSet(ActionProcessViewSet):
    ...


@document_action_process_step_viewset(object_type="cluster")
class ClusterActionProcessStepViewSet(ProcessStepViewSet):
    ...


@audit_action_process_viewset(retrieve_owner=parent_host_from_lookup)
@document_action_process_viewset(object_type="clusterHost", operation_id_variant="ClusterHost")
class ClusterHostActionProcessViewSet(ActionProcessViewSet):
    ...


@document_action_process_step_viewset(object_type="clusterHost", operation_id_variant="ClusterHost")
class ClusterHostActionProcessStepViewSet(ProcessStepViewSet):
    ...
