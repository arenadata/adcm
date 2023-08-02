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


from api_v2.cluster.filters import ClusterFilter
from api_v2.cluster.serializers import (
    ClusterCreateSerializer,
    ClusterSerializer,
    ClusterUpdateSerializer,
    HostComponentListSerializer,
    HostComponentPostSerializer,
    ServicePrototypeSerializer,
)
from api_v2.component.serializers import ComponentMappingSerializer
from api_v2.host.serializers import HostMappingSerializer
from api_v2.views import CamelCaseGenericViewSet, CamelCaseModelViewSet
from cm.api import add_cluster, retrieve_host_component_objects, set_host_component
from cm.issue import update_hierarchy_issues
from cm.models import (
    Cluster,
    Host,
    HostComponent,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from django_filters.rest_framework.backends import DjangoFilterBackend
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND

from adcm.permissions import (
    VIEW_CLUSTER_PERM,
    VIEW_HC_PERM,
    DjangoModelPermissionsAudit,
    check_custom_perm,
    get_object_for_user,
)


class ClusterViewSet(PermissionListMixin, CamelCaseModelViewSet):  # pylint:disable=too-many-ancestors
    queryset = Cluster.objects.prefetch_related("prototype", "concerns").order_by("name")
    serializer_class = ClusterSerializer
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_CLUSTER_PERM]
    filterset_class = ClusterFilter
    filter_backends = (DjangoFilterBackend,)
    http_method_names = ["get", "post", "patch", "delete"]

    def get_serializer_class(self):
        if self.action == "create":
            return ClusterCreateSerializer

        if self.action in ("update", "partial_update"):
            return ClusterUpdateSerializer

        if self.action == "service_prototypes":
            return ServicePrototypeSerializer

        return self.serializer_class

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

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data
        instance = self.get_object()

        if valid_data.get("name") and valid_data.get("name") != instance.name and instance.state != "created":
            raise ValidationError("Name change is available only in the 'created' state")

        instance.name = valid_data.get("name", instance.name)
        instance.save(update_fields=["name"])
        update_hierarchy_issues(obj=instance)

        return Response(status=HTTP_200_OK, data=ClusterSerializer(instance).data)

    @action(methods=["get"], detail=True)
    def service_prototypes(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        cluster = Cluster.objects.filter(pk=kwargs["pk"]).first()
        if not cluster:
            return Response(data=f'Cluster with pk "{kwargs["pk"]}" not found', status=HTTP_404_NOT_FOUND)

        prototypes = Prototype.objects.filter(type=ObjectType.SERVICE, bundle=cluster.prototype.bundle)
        serializer = self.get_serializer_class()(instance=prototypes, many=True)

        return Response(data=serializer.data)


class MappingViewSet(  # pylint:disable=too-many-ancestors
    PermissionListMixin, ListModelMixin, CreateModelMixin, CamelCaseGenericViewSet
):
    queryset = HostComponent.objects.select_related("service", "host", "component", "cluster").order_by(
        "component__prototype__display_name"
    )
    serializer_class = HostComponentListSerializer
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_HC_PERM]
    pagination_class = None
    filter_backends = []

    def get_serializer_class(self):
        if self.action == "create":
            return HostComponentPostSerializer

        return self.serializer_class

    def list(self, request: Request, *args, **kwargs) -> Response:
        cluster = Cluster.objects.filter(pk=kwargs["cluster_pk"]).first()
        if not cluster:
            return Response(data=f'Cluster with pk "{kwargs["cluster_pk"]}" not found', status=HTTP_404_NOT_FOUND)

        self.queryset = self.queryset.filter(cluster_id=cluster.pk)

        return super().list(request, *args, **kwargs)

    def create(self, request: Request, *args, **kwargs) -> Response:
        cluster = get_object_for_user(
            user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["cluster_pk"]
        )
        check_custom_perm(
            user=request.user, action_type="edit_host_components_of", model=Cluster.__name__.lower(), obj=cluster
        )

        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        host_component_objects = retrieve_host_component_objects(cluster=cluster, plain_hc=serializer.validated_data)
        new_host_component = set_host_component(cluster=cluster, host_component_objects=host_component_objects)

        return Response(
            data=self.serializer_class(instance=new_host_component, many=True).data, status=HTTP_201_CREATED
        )

    @action(methods=["get"], detail=False)
    def hosts(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        cluster = Cluster.objects.filter(pk=kwargs["cluster_pk"]).first()
        if not cluster:
            return Response(data=f'Cluster with pk "{kwargs["cluster_pk"]}" not found', status=HTTP_404_NOT_FOUND)

        serializer = HostMappingSerializer(instance=Host.objects.filter(cluster=cluster), many=True)

        return Response(data=serializer.data)

    @action(methods=["get"], detail=False)
    def components(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        cluster = Cluster.objects.filter(pk=kwargs["cluster_pk"]).first()
        if not cluster:
            return Response(data=f'Cluster with pk "{kwargs["cluster_pk"]}" not found', status=HTTP_404_NOT_FOUND)

        serializer = ComponentMappingSerializer(instance=ServiceComponent.objects.filter(cluster=cluster), many=True)

        return Response(data=serializer.data)
