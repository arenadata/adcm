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
from cm.api import add_cluster, retrieve_host_component_objects, set_host_component
from cm.errors import AdcmEx
from cm.issue import update_hierarchy_issues
from cm.models import (
    ADCMEntityStatus,
    Cluster,
    ClusterObject,
    Host,
    HostComponent,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from cm.status_api import get_obj_status
from django.db.models import QuerySet
from django_filters.rest_framework.backends import DjangoFilterBackend
from guardian.mixins import PermissionListMixin
from guardian.shortcuts import get_objects_for_user
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
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
    queryset = Cluster.objects.prefetch_related("prototype", "concerns").order_by("name")
    permission_required = [VIEW_CLUSTER_PERM]
    filterset_class = ClusterFilter
    filter_backends = (DjangoFilterBackend,)
    permission_classes = [ClusterPermissions]

    def get_serializer_class(self):  # pylint: disable=too-many-return-statements
        match self.action:
            case "create":
                return ClusterCreateSerializer
            case "update" | "partial_update":
                return ClusterUpdateSerializer
            case "service_prototypes":
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
    def destroy(self, request, *args, **kwargs) -> Response:
        return super().destroy(request=request, *args, **kwargs)

    @audit
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid = serializer.validated_data

        cluster = add_cluster(
            prototype=Prototype.objects.get(pk=valid["prototype_id"], type=ObjectType.CLUSTER),
            name=valid["name"],
            description=valid.get("description", ""),
        )

        return Response(data=ClusterSerializer(cluster).data, status=HTTP_201_CREATED)

    @audit
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

    @action(methods=["get"], detail=True, url_path="service-prototypes")
    def service_prototypes(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        cluster = Cluster.objects.filter(pk=kwargs["pk"]).first()
        if not cluster:
            return Response(data=f'Cluster with pk "{kwargs["pk"]}" not found', status=HTTP_404_NOT_FOUND)

        prototypes = Prototype.objects.filter(type=ObjectType.SERVICE, bundle=cluster.prototype.bundle).order_by(
            "display_name"
        )
        serializer = self.get_serializer_class()(instance=prototypes, many=True)

        return Response(data=serializer.data)

    @action(methods=["get"], detail=True, url_path="statuses/services")
    def services_statuses(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        cluster = get_object_for_user(user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["pk"])
        queryset = get_objects_for_user(user=request.user, perms=VIEW_SERVICE_PERM, klass=ClusterObject).filter(
            cluster=cluster
        )
        queryset = self.filter_queryset(queryset=queryset, request=request)

        return self.get_paginated_response(
            data=RelatedServicesStatusesSerializer(instance=self.paginate_queryset(queryset=queryset), many=True).data
        )

    @action(methods=["get"], detail=True, url_path="statuses/hosts")
    def hosts_statuses(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        cluster = get_object_for_user(user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["pk"])
        queryset = get_objects_for_user(user=request.user, perms=VIEW_HOST_PERM, klass=Host).filter(cluster=cluster)
        queryset = self.filter_queryset(queryset=queryset, request=request)

        return self.get_paginated_response(
            data=RelatedHostsStatusesSerializer(instance=self.paginate_queryset(queryset=queryset), many=True).data
        )

    def filter_queryset(self, queryset: QuerySet, **kwargs) -> QuerySet | list:
        if self.action in {"services_statuses", "hosts_statuses"}:
            return self._filter_by_status(queryset=queryset, **kwargs)

        return super().filter_queryset(queryset=queryset)

    @staticmethod
    def _filter_by_status(request: Request, queryset: QuerySet) -> QuerySet | list:
        status_value = request.query_params.get("status", default=None)
        if status_value is None:
            return queryset

        status_choices = {choice[0] for choice in ADCMEntityStatus.choices}
        if status_value not in status_choices:
            status_choices_repr = ", ".join(status_choices)
            raise AdcmEx(code="BAD_REQUEST", msg=f"Status choices: {status_choices_repr}")

        return [obj for obj in queryset if get_obj_status(obj=obj) == status_value]

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
        serializer = self.get_serializer(instance=ServiceComponent.objects.filter(cluster=cluster), many=True)

        return Response(status=HTTP_200_OK, data=serializer.data)
