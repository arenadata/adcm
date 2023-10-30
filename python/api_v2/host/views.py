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
from api_v2.config.utils import ConfigSchemaMixin
from api_v2.host.filters import HostClusterFilter, HostFilter
from api_v2.host.serializers import (
    ClusterHostStatusSerializer,
    HostChangeMaintenanceModeSerializer,
    HostCreateRelatedSerializer,
    HostCreateSerializer,
    HostGroupConfigSerializer,
    HostSerializer,
    HostUpdateSerializer,
)
from api_v2.host.utils import add_new_host_and_map_it, maintenance_mode
from api_v2.views import CamelCaseModelViewSet, CamelCaseReadOnlyModelViewSet
from audit.utils import audit
from cm.api import add_host_to_cluster, delete_host, remove_host_from_cluster
from cm.errors import AdcmEx
from cm.models import Cluster, GroupConfig, Host, HostProvider
from django_filters.rest_framework.backends import DjangoFilterBackend
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
)

from adcm.permissions import (
    VIEW_CLUSTER_PERM,
    VIEW_HOST_PERM,
    VIEW_PROVIDER_PERM,
    DjangoModelPermissionsAudit,
    ModelObjectPermissionsByActionMixin,
    check_custom_perm,
    get_object_for_user,
)


# pylint:disable-next=too-many-ancestors
class HostViewSet(ModelObjectPermissionsByActionMixin, PermissionListMixin, ConfigSchemaMixin, CamelCaseModelViewSet):
    queryset = (
        Host.objects.select_related("provider", "cluster")
        .prefetch_related("concerns", "hostcomponent_set")
        .order_by("fqdn")
    )
    permission_required = [VIEW_HOST_PERM]
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

    @audit
    def create(self, request, *args, **kwargs):
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

        host = add_new_host_and_map_it(
            provider=request_hostprovider, fqdn=serializer.validated_data["fqdn"], cluster=request_cluster
        )

        return Response(data=HostSerializer(instance=host).data, status=HTTP_201_CREATED)

    @audit
    def destroy(self, request, *args, **kwargs):
        host = self.get_object()
        check_custom_perm(request.user, "remove", "host", host)
        delete_host(host=host)
        return Response(status=HTTP_204_NO_CONTENT)

    @audit
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)

        instance = self.get_object()
        check_custom_perm(request.user, "change", "host", instance)

        serializer = self.get_serializer(instance=instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        valid = serializer.validated_data

        if (
            valid.get("fqdn")
            and valid.get("fqdn") != instance.fqdn
            and (instance.cluster or instance.state != "created")
        ):
            raise AdcmEx(code="HOST_UPDATE_ERROR")

        serializer.save()

        return Response(status=HTTP_200_OK, data=HostSerializer(instance=instance).data)

    @audit
    @action(methods=["post"], detail=True, url_path="maintenance-mode")
    def maintenance_mode(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        return maintenance_mode(request=request, **kwargs)


class HostClusterViewSet(  # pylint:disable=too-many-ancestors
    ModelObjectPermissionsByActionMixin, PermissionListMixin, CamelCaseReadOnlyModelViewSet
):
    object_actions = ["destroy"]
    permission_required = [VIEW_HOST_PERM]
    filterset_class = HostClusterFilter
    audit_model_hint = Host

    def get_serializer_class(self):
        if self.action == "maintenance_mode":
            return HostChangeMaintenanceModeSerializer
        elif self.action == "create":
            return HostCreateRelatedSerializer

        return HostSerializer

    def get_queryset(self, *args, **kwargs):
        cluster = get_object_for_user(
            user=self.request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=self.kwargs["cluster_pk"]
        )

        return Host.objects.filter(cluster=cluster).select_related("cluster").prefetch_related("hostcomponent_set")

    @audit
    def create(self, request, *args, **kwargs):  # pylint:disable=unused-argument
        cluster = get_object_for_user(
            user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["cluster_pk"]
        )

        if not cluster:
            return Response(data=f'Cluster with pk "{kwargs["cluster_pk"]}" not found', status=HTTP_404_NOT_FOUND)

        check_custom_perm(request.user, "map_host_to", "cluster", cluster)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        host = add_host_to_cluster(cluster=cluster, host=serializer.validated_data["host_id"])

        return Response(status=HTTP_201_CREATED, data=HostSerializer(instance=host).data)

    @audit
    def destroy(self, request, *args, **kwargs):  # pylint:disable=unused-argument
        host = self.get_object()
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_pk"])
        if host.cluster != cluster:
            raise AdcmEx(code="FOREIGN_HOST", msg=f"Host #{host.id} doesn't belong to cluster #{cluster.id}")

        check_custom_perm(request.user, "unmap_host_from", "cluster", cluster)
        remove_host_from_cluster(host=host)
        return Response(status=HTTP_204_NO_CONTENT)

    @audit
    @action(methods=["post"], detail=True, url_path="maintenance-mode")
    def maintenance_mode(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        return maintenance_mode(request=request, **kwargs)

    @action(methods=["get"], detail=True, url_path="statuses")
    def statuses(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        host = self.get_object()
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_pk"])
        if host.cluster != cluster:
            raise AdcmEx(code="FOREIGN_HOST", msg=f"Host #{host.id} doesn't belong to cluster #{cluster.id}")

        return Response(data=ClusterHostStatusSerializer(instance=host).data)


class HostGroupConfigViewSet(PermissionListMixin, CamelCaseReadOnlyModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = (
        Host.objects.select_related("provider", "cluster")
        .prefetch_related("concerns", "hostcomponent_set")
        .order_by("fqdn")
    )
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_HOST_PERM]
    filterset_class = HostClusterFilter
    filter_backends = (DjangoFilterBackend,)
    pagination_class = None

    def get_serializer_class(self) -> type[HostGroupConfigSerializer | HostCreateRelatedSerializer]:
        if self.action == "create":
            return HostCreateRelatedSerializer

        return HostGroupConfigSerializer

    def get_queryset(self, *args, **kwargs):
        return self.queryset.filter(group_config__id=self.kwargs["group_config_pk"])

    def create(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        group_config = GroupConfig.objects.filter(id=self.kwargs["group_config_pk"]).first()

        if not group_config:
            raise AdcmEx(code="HOST_GROUP_CONFIG_NOT_FOUND")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        host = serializer.validated_data["host_id"]
        group_config.check_host_candidate(host_ids=[host.pk])
        group_config.hosts.add(host)

        return Response(status=HTTP_201_CREATED, data=HostGroupConfigSerializer(instance=host).data)

    def destroy(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        group_config = GroupConfig.objects.filter(id=self.kwargs["group_config_pk"]).first()

        if not group_config:
            raise AdcmEx(code="HOST_GROUP_CONFIG_NOT_FOUND")

        host = self.get_object()
        group_config.hosts.remove(host)
        return Response(status=HTTP_204_NO_CONTENT)
