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


from api_v2.cluster.filters import (
    ClusterFilter,
    ClusterHostFilter,
    ClusterServiceFilter,
)
from api_v2.cluster.permissions import ClusterPermissions
from api_v2.cluster.serializers import (
    ClusterCreateSerializer,
    ClusterSerializer,
    ClusterUpdateSerializer,
    MappingSerializer,
    RelatedHostsStatusesSerializer,
    RelatedServicesStatusesSerializer,
    ServicePrototypeSerializer,
)
from api_v2.component.serializers import ComponentMappingSerializer
from api_v2.config.utils import ConfigSchemaMixin
from api_v2.host.serializers import HostMappingSerializer
from api_v2.views import CamelCaseModelViewSet
from audit.utils import audit
from cm.api import (
    add_cluster,
    delete_cluster,
    retrieve_host_component_objects,
    set_host_component,
)
from cm.errors import AdcmEx
from cm.issue import update_hierarchy_issues
from cm.models import (
    Cluster,
    ClusterObject,
    Host,
    HostComponent,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from guardian.mixins import PermissionListMixin
from guardian.shortcuts import get_objects_for_user
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_403_FORBIDDEN,
)

from adcm.permissions import (
    VIEW_CLUSTER_PERM,
    VIEW_HC_PERM,
    VIEW_HOST_PERM,
    VIEW_SERVICE_PERM,
    get_object_for_user,
)


class ClusterViewSet(
    PermissionListMixin,
    ConfigSchemaMixin,
    CamelCaseModelViewSet,
):  # pylint:disable=too-many-ancestors
    queryset = (
        Cluster.objects.prefetch_related("prototype", "concerns")
        .prefetch_related("clusterobject_set__prototype")
        .order_by("name")
    )
    permission_required = [VIEW_CLUSTER_PERM]
    filterset_class = ClusterFilter
    permission_classes = [ClusterPermissions]

    def get_serializer_class(self):  # pylint: disable=too-many-return-statements
        match self.action:
            case "create":
                return ClusterCreateSerializer
            case "update" | "partial_update":
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

    @audit
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid = serializer.validated_data

        cluster = add_cluster(
            prototype=Prototype.objects.get(pk=valid["prototype_id"], type=ObjectType.CLUSTER),
            name=valid["name"],
            description=valid["description"],
        )

        return Response(data=ClusterSerializer(cluster).data, status=HTTP_201_CREATED)

    @audit
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data

        if valid_data.get("name") and valid_data.get("name") != instance.name and instance.state != "created":
            raise AdcmEx(code="CLUSTER_CONFLICT", msg="Name change is available only in the 'created' state")

        instance.name = valid_data.get("name", instance.name)
        instance.description = valid_data.get("description", instance.description)
        instance.save(update_fields=["name", "description"])
        update_hierarchy_issues(obj=instance)

        return Response(status=HTTP_200_OK, data=ClusterSerializer(instance).data)

    @audit
    def destroy(self, request, *args, **kwargs):
        cluster = self.get_object()
        delete_cluster(cluster=cluster)

        return Response(status=HTTP_204_NO_CONTENT)

    @action(methods=["get"], detail=True, url_path="service-prototypes")
    def service_prototypes(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        cluster = self.get_object()
        prototypes = Prototype.objects.filter(type=ObjectType.SERVICE, bundle=cluster.prototype.bundle).order_by(
            "display_name"
        )
        serializer = self.get_serializer_class()(instance=prototypes, many=True)

        return Response(data=serializer.data)

    @action(methods=["get"], detail=True, url_path="service-candidates")
    def service_candidates(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
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
        queryset=ClusterObject.objects.order_by("prototype__display_name"),
        permission_required=[VIEW_SERVICE_PERM],
        filterset_class=ClusterServiceFilter,
    )
    def services_statuses(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        cluster = get_object_for_user(user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["pk"])
        queryset = self.filter_queryset(queryset=self.get_queryset().filter(cluster=cluster))

        return self.get_paginated_response(
            data=RelatedServicesStatusesSerializer(instance=self.paginate_queryset(queryset=queryset), many=True).data
        )

    @action(
        methods=["get"],
        detail=True,
        url_path="statuses/hosts",
        queryset=Host.objects.order_by("fqdn"),
        permission_required=[VIEW_HOST_PERM],
        filterset_class=ClusterHostFilter,
    )
    def hosts_statuses(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        cluster = get_object_for_user(user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["pk"])
        queryset = self.filter_queryset(queryset=self.get_queryset().filter(cluster=cluster))

        return self.get_paginated_response(
            data=RelatedHostsStatusesSerializer(instance=self.paginate_queryset(queryset=queryset), many=True).data
        )

    @audit
    @action(
        methods=["get", "post"],
        detail=True,
        pagination_class=None,
        filter_backends=[],
    )
    def mapping(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        cluster = self.get_object()

        if request.method == "GET":
            queryset = get_objects_for_user(user=request.user, perms=VIEW_HC_PERM, klass=HostComponent).filter(
                cluster=cluster
            )

            if not queryset.exists() and request.user.has_perm("cm.view_host_components_of_cluster", cluster):
                queryset = HostComponent.objects.filter(cluster=cluster)

            return Response(status=HTTP_200_OK, data=self.get_serializer(instance=queryset, many=True).data)

        if not request.user.has_perm("cm.edit_host_components_of_cluster", cluster):
            return Response(status=HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        host_component_objects = retrieve_host_component_objects(cluster=cluster, plain_hc=serializer.validated_data)
        new_host_component = set_host_component(cluster=cluster, host_component_objects=host_component_objects)

        return Response(data=self.get_serializer(instance=new_host_component, many=True).data, status=HTTP_201_CREATED)

    @action(methods=["get"], detail=True, url_path="mapping/hosts", url_name="mapping-hosts")
    def mapping_hosts(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        cluster = self.get_object()
        serializer = self.get_serializer(instance=Host.objects.filter(cluster=cluster), many=True)

        return Response(status=HTTP_200_OK, data=serializer.data)

    @action(methods=["get"], detail=True, url_path="mapping/components", url_name="mapping-components")
    def mapping_components(self, request: Request, *args, **kwargs):  # pylint: disable=unused-argument
        cluster = self.get_object()
        serializer = self.get_serializer(
            instance=ServiceComponent.objects.filter(cluster=cluster).order_by("pk"), many=True
        )

        return Response(status=HTTP_200_OK, data=serializer.data)
