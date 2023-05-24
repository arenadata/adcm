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

from api_v2.service.filters import ServiceFilter
from api_v2.service.serializers import (
    ServiceCreateSerializer,
    ServiceMaintenanceModeSerializer,
    ServiceRetrieveSerializer,
)
from cm.api import add_service_to_cluster, update_mm_objects
from cm.models import Cluster, ClusterObject
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework.viewsets import ModelViewSet

from adcm.permissions import (
    ADD_SERVICE_PERM,
    CHANGE_MM_PERM,
    VIEW_CLUSTER_PERM,
    VIEW_SERVICE_PERM,
    DjangoModelPermissionsAudit,
    check_custom_perm,
    get_object_for_user,
)
from adcm.utils import get_maintenance_mode_response


class ServiceViewSet(PermissionListMixin, ModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = ClusterObject.objects.all()
    serializer_class = ServiceRetrieveSerializer
    filterset_class = ServiceFilter
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_SERVICE_PERM]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self, *args, **kwargs):
        cluster = Cluster.objects.filter(pk=self.kwargs.get("cluster_pk")).first()
        if not cluster:
            return ClusterObject.objects.none()

        return self.queryset.filter(cluster=cluster)

    def get_serializer_class(self):
        match self.action:
            case "create":
                return ServiceCreateSerializer
            case "maintenance_mode":
                return ServiceMaintenanceModeSerializer

        return self.serializer_class

    def create(self, request: Request, *args, **kwargs):
        cluster = get_object_for_user(
            user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, pk=kwargs["cluster_pk"]
        )
        check_custom_perm(user=request.user, action_type=ADD_SERVICE_PERM, model=Cluster.__name__.lower(), obj=cluster)

        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        add_service_to_cluster(
            cluster=Cluster.objects.get(pk=kwargs["cluster_pk"]), proto=serializer.validated_data["prototype"]
        )

        return Response(status=HTTP_201_CREATED)

    @update_mm_objects
    @action(methods=["post"], detail=True, url_path="maintenance-mode")
    def maintenance_mode(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        service = get_object_for_user(user=request.user, perms=VIEW_SERVICE_PERM, klass=ClusterObject, pk=kwargs["pk"])
        check_custom_perm(
            user=request.user, action_type=CHANGE_MM_PERM, model=service.__class__.__name__.lower(), obj=service
        )

        serializer = self.get_serializer_class()(instance=service, data=request.data)
        serializer.is_valid(raise_exception=True)

        response: Response = get_maintenance_mode_response(obj=self.get_object(), serializer=serializer)
        if response.status_code == HTTP_200_OK:
            response.data = serializer.data

        return response
