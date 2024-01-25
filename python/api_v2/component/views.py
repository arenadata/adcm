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
    CHANGE_MM_PERM,
    VIEW_CLUSTER_PERM,
    VIEW_COMPONENT_PERM,
    VIEW_HOST_PERM,
    VIEW_SERVICE_PERM,
    ChangeMMPermissions,
    DjangoModelPermissionsAudit,
    check_custom_perm,
    get_object_for_user,
)
from adcm.utils import get_maintenance_mode_response
from audit.utils import audit
from cm.models import Cluster, ClusterObject, Host, ServiceComponent
from cm.services.status.notify import update_mm_objects
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from api_v2.component.filters import ComponentFilter
from api_v2.component.serializers import (
    ComponentMaintenanceModeSerializer,
    ComponentSerializer,
    ComponentStatusSerializer,
    HostComponentSerializer,
)
from api_v2.config.utils import ConfigSchemaMixin
from api_v2.views import (
    CamelCaseGenericViewSet,
    CamelCaseReadOnlyModelViewSet,
    ObjectWithStatusViewMixin,
)


class ComponentViewSet(
    PermissionListMixin, ConfigSchemaMixin, CamelCaseReadOnlyModelViewSet, ObjectWithStatusViewMixin
):
    queryset = ServiceComponent.objects.select_related("cluster", "service").order_by("pk")
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_COMPONENT_PERM]
    filterset_class = ComponentFilter
    retrieve_status_map_actions = ("statuses", "list")

    audit_model_hint = ServiceComponent

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

        return ComponentSerializer

    @audit
    @update_mm_objects
    @action(methods=["post"], detail=True, url_path="maintenance-mode", permission_classes=[ChangeMMPermissions])
    def maintenance_mode(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
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
    def statuses(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        component = get_object_for_user(
            user=request.user, perms=VIEW_COMPONENT_PERM, klass=ServiceComponent, id=kwargs["pk"]
        )

        return Response(data=ComponentStatusSerializer(instance=component, context=self.get_serializer_context()).data)


class HostComponentViewSet(PermissionListMixin, ListModelMixin, CamelCaseGenericViewSet, ObjectWithStatusViewMixin):
    queryset = ServiceComponent.objects.select_related("cluster", "service").order_by("prototype__name")
    serializer_class = HostComponentSerializer
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_COMPONENT_PERM]
    filterset_class = ComponentFilter

    def get_queryset(self, *args, **kwargs):
        cluster = get_object_for_user(
            user=self.request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, pk=self.kwargs["cluster_pk"]
        )
        host = get_object_for_user(user=self.request.user, perms=VIEW_HOST_PERM, klass=Host, pk=self.kwargs["host_pk"])

        return (
            super()
            .get_queryset(*args, **kwargs)
            .filter(cluster=cluster, id__in=host.hostcomponent_set.all().values_list("component_id", flat=True))
        )
