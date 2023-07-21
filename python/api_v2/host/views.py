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

from api_v2.host.serializers import (
    ClusterHostCreateSerializer,
    ClusterHostSerializer,
    HostChangeMaintenanceModeSerializer,
    HostCreateSerializer,
    HostSerializer,
    HostUpdateSerializer,
)
from api_v2.host.utils import (
    add_new_host_and_map_it,
    maintenance_mode,
    map_list_of_hosts,
)
from cm.api import add_host_to_cluster, delete_host, remove_host_from_cluster
from cm.errors import AdcmEx
from cm.issue import update_hierarchy_issues, update_issue_after_deleting
from cm.models import Cluster, Host
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
from rest_framework.viewsets import ModelViewSet

from adcm.permissions import (
    VIEW_CLUSTER_PERM,
    VIEW_HOST_PERM,
    DjangoModelPermissionsAudit,
    check_custom_perm,
    get_object_for_user,
)


# pylint:disable-next=too-many-ancestors
class HostViewSet(PermissionListMixin, ModelViewSet):
    queryset = Host.objects.prefetch_related("provider", "concerns").all()
    serializer_class = HostSerializer
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_HOST_PERM]
    filterset_fields = ["provider__name", "state", "fqdn"]
    ordering_fields = ["fqdn"]

    def get_serializer_class(self):
        if self.action == "create":
            return HostCreateSerializer
        elif self.action in ("update", "partial_update"):
            return HostUpdateSerializer
        elif self.action == "maintenance_mode":
            return HostChangeMaintenanceModeSerializer

        return self.serializer_class

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid = serializer.validated_data

        host = add_new_host_and_map_it(
            provider=valid.get("provider"), fqdn=valid.get("fqdn"), cluster=valid.get("cluster")
        )

        return Response(data=HostSerializer(host).data, status=HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        host = self.get_object()
        check_custom_perm(request.user, "remove", "host", host)
        delete_host(host=host)
        return Response(status=HTTP_204_NO_CONTENT)

    def _host_update(self, request, *args, partial=False, **kwargs):  # pylint: disable=unused-argument
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid = serializer.validated_data

        host = self.get_object()
        check_custom_perm(request.user, "change", "host", host)

        if not partial and not all((valid.get("fqdn"), valid.get("cluster"))):
            raise AdcmEx(code="HOST_UPDATE_ERROR", msg="Not all values presented in full update")

        if valid.get("fqdn") and valid.get("fqdn") != host.fqdn and (host.cluster or host.state != "created"):
            raise AdcmEx(code="HOST_UPDATE_ERROR")

        if valid.get("fqdn"):
            host.fqdn = valid["fqdn"]

        if valid.get("cluster"):
            check_custom_perm(request.user, "map_host_to", "cluster", valid["cluster"])
            add_host_to_cluster(cluster=valid["cluster"], host=host)
        elif valid.get("cluster") is None and host.cluster:
            check_custom_perm(request.user, "unmap_host_from", "cluster", valid["cluster"])
            remove_host_from_cluster(host=host)
        elif valid.get("cluster") is None:
            host.save()
            update_hierarchy_issues(host.cluster)
            update_hierarchy_issues(host.provider)
            update_issue_after_deleting()

        return Response(status=HTTP_200_OK, data=HostSerializer(host).data)

    def partial_update(self, request, *args, **kwargs):
        return self._host_update(request, *args, partial=True, **kwargs)

    def update(self, request, *args, **kwargs):
        return self._host_update(request, *args, **kwargs)

    @action(methods=["post"], detail=True, url_path="maintenance-mode")
    def maintenance_mode(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        return maintenance_mode(request=request, **kwargs)


class HostClusterViewSet(PermissionListMixin, ModelViewSet):  # pylint:disable=too-many-ancestors
    serializer_class = ClusterHostSerializer
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_HOST_PERM]
    filterset_fields = ["provider__name", "state", "fqdn"]
    ordering_fields = ["fqdn"]

    def get_serializer_class(self):
        if self.action == "maintenance_mode":
            return HostChangeMaintenanceModeSerializer
        elif self.action == "create":
            return ClusterHostCreateSerializer

        return self.serializer_class

    def get_queryset(self, *args, **kwargs):  # pylint: disable=unused-argument
        return Host.objects.filter(cluster=self.kwargs["cluster_pk"])

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cluster = get_object_for_user(
            user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["cluster_pk"]
        )
        if not cluster:
            return Response(data=f'Cluster with pk "{kwargs["cluster_pk"]}" not found', status=HTTP_404_NOT_FOUND)

        check_custom_perm(request.user, "map_host_to", "cluster", cluster)

        map_list_of_hosts(hosts=serializer.validated_data["hosts"], cluster=cluster)

        return Response(
            data=ClusterHostSerializer(
                instance=Host.objects.prefetch_related("hostcomponent_set").filter(cluster=cluster),
                many=True,
            ).data,
            status=HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        host = self.get_object()
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_pk"])
        if host.cluster != cluster:
            msg = f"Host #{host.id} doesn't belong to cluster #{cluster.id}"

            raise AdcmEx("FOREIGN_HOST", msg)
        check_custom_perm(request.user, "unmap_host_from", "cluster", cluster)
        remove_host_from_cluster(host=host)
        return Response(status=HTTP_204_NO_CONTENT)

    @action(methods=["post"], detail=True, url_path="maintenance-mode")
    def maintenance_mode(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        return maintenance_mode(request=request, **kwargs)
