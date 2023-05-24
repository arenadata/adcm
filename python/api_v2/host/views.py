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

from api_v2.host.serializers import HostChangeMaintenanceModeSerializer, HostSerializer
from cm.api import add_host_to_cluster
from cm.models import Cluster, Host, MaintenanceMode
from guardian.mixins import PermissionListMixin
from guardian.shortcuts import get_objects_for_user
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
from rest_framework.viewsets import ModelViewSet

from adcm.permissions import (
    VIEW_CLUSTER_PERM,
    VIEW_HOST_PERM,
    DjangoModelPermissionsAudit,
)
from adcm.utils import get_maintenance_mode_response


class HostViewSet(PermissionListMixin, ModelViewSet):  # pylint:disable=too-many-ancestors
    queryset = Host.objects.all()
    serializer_class = HostSerializer
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_HOST_PERM]
    filterset_fields = ["provider__name", "state", "fqdn"]
    ordering_fields = ["fqdn"]

    def get_serializer_class(self):
        if self.action == "maintenance_mode":
            return HostChangeMaintenanceModeSerializer

        return self.serializer_class

    def create(self, request, *args, **kwargs):
        host = Host.objects.filter(pk=request.data[0]["host_id"]).first()
        if not host:
            return Response(data=f'Host with pk "{request.data[0]["host_id"]}" not found', status=HTTP_404_NOT_FOUND)

        cluster_queryset = get_objects_for_user(user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster)
        cluster = cluster_queryset.get(pk=kwargs["cluster_pk"])
        if not cluster:
            return Response(data=f'Cluster with pk "{kwargs["cluster_pk"]}" not found', status=HTTP_404_NOT_FOUND)

        if not request.user.has_perm(perm="cm.map_host_to_cluster", obj=cluster):
            return Response(
                data="Current user has no permission to map host to cluster",
                status=HTTP_403_FORBIDDEN,
            )

        add_host_to_cluster(cluster=cluster, host=host)

        return Response(status=HTTP_201_CREATED)

    @action(methods=["post"], detail=True)
    def maintenance_mode(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        host = Host.objects.filter(pk=kwargs["pk"]).first()
        if not host:
            return Response(data=f'Host with pk "{kwargs["pk"]}" not found', status=HTTP_404_NOT_FOUND)

        if not request.user.has_perm(perm="cm.change_maintenance_mode_host", obj=host):
            return Response(
                data="Current user has no permission to change host maintenance_mode",
                status=HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(instance=host, data=request.data)
        serializer.is_valid(raise_exception=True)
        if (
            serializer.validated_data.get("maintenance_mode") == MaintenanceMode.ON
            and not host.is_maintenance_mode_available
        ):
            return Response(data="MAINTENANCE_MODE_NOT_AVAILABLE", status=HTTP_409_CONFLICT)

        response: Response = get_maintenance_mode_response(obj=host, serializer=serializer)
        if response.status_code == HTTP_200_OK:
            response.data = serializer.data

        return response
