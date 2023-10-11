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

from api_v2.component.filters import ComponentFilter
from api_v2.component.serializers import (
    ComponentMaintenanceModeSerializer,
    ComponentSerializer,
    ComponentStatusSerializer,
)
from api_v2.config.utils import ConfigSchemaMixin
from api_v2.views import CamelCaseReadOnlyModelViewSet
from cm.api import update_mm_objects
from cm.models import Cluster, ClusterObject, ServiceComponent
from django_filters.rest_framework.backends import DjangoFilterBackend
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from adcm.permissions import (
    CHANGE_MM_PERM,
    VIEW_CLUSTER_PERM,
    VIEW_COMPONENT_PERM,
    VIEW_SERVICE_PERM,
    DjangoModelPermissionsAudit,
    check_custom_perm,
    get_object_for_user,
)
from adcm.utils import get_maintenance_mode_response


class ComponentViewSet(
    PermissionListMixin, ConfigSchemaMixin, CamelCaseReadOnlyModelViewSet
):  # pylint: disable=too-many-ancestors
    queryset = ServiceComponent.objects.select_related("cluster", "service").order_by("pk")
    serializer_class = ComponentSerializer
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_COMPONENT_PERM]
    filterset_class = ComponentFilter
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self, *args, **kwargs):
        cluster = get_object_for_user(
            user=self.request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, pk=self.kwargs["cluster_pk"]
        )
        service = get_object_for_user(
            user=self.request.user, perms=VIEW_SERVICE_PERM, klass=ClusterObject, pk=self.kwargs["service_pk"]
        )

        return super().get_queryset(*args, **kwargs).filter(cluster=cluster, service=service)

    def get_serializer_class(self):
        match self.action:
            case "maintenance_mode":
                return ComponentMaintenanceModeSerializer

        return self.serializer_class

    @update_mm_objects
    @action(methods=["post"], detail=True, url_path="maintenance-mode")
    def maintenance_mode(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        component = get_object_for_user(
            user=request.user, perms=VIEW_COMPONENT_PERM, klass=ServiceComponent, pk=kwargs["pk"]
        )
        check_custom_perm(
            user=request.user, action_type=CHANGE_MM_PERM, model=component.__class__.__name__.lower(), obj=component
        )

        serializer = self.get_serializer_class()(instance=component, data=request.data)
        serializer.is_valid(raise_exception=True)

        response: Response = get_maintenance_mode_response(obj=self.get_object(), serializer=serializer)
        if response.status_code == HTTP_200_OK:
            response.data = serializer.data

        return response

    @action(methods=["get"], detail=True, url_path="statuses")
    def statuses(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        component = get_object_for_user(
            user=request.user, perms=VIEW_COMPONENT_PERM, klass=ServiceComponent, id=kwargs["pk"]
        )

        return Response(data=ComponentStatusSerializer(instance=component).data)
