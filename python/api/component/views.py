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

from adcm.permissions import check_custom_perm, get_object_for_user
from audit.utils import audit
from cm.models import Cluster, Component, HostComponent, Service
from cm.services.maintenance_mode import get_maintenance_mode_response
from cm.services.status.notify import update_mm_objects
from cm.status_api import make_ui_component_status
from guardian.mixins import PermissionListMixin
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from api.base_view import DetailView, GenericUIView, PaginatedView
from api.component.serializers import (
    ComponentChangeMaintenanceModeSerializer,
    ComponentDetailSerializer,
    ComponentDetailUISerializer,
    ComponentSerializer,
    ComponentStatusSerializer,
    ComponentUISerializer,
)
from api.rbac.viewsets import DjangoOnlyObjectPermissions


def get_component_queryset(queryset, user, kwargs):
    if "cluster_id" in kwargs:
        cluster = get_object_for_user(user, "cm.view_cluster", Cluster, id=kwargs["cluster_id"])
        service = get_object_for_user(
            user,
            "cm.view_service",
            Service,
            cluster=cluster,
            id=kwargs["service_id"],
        )
        queryset = queryset.filter(cluster=cluster, service=service)
    elif "service_id" in kwargs:
        service = get_object_for_user(user, "cm.view_service", Service, id=kwargs["service_id"])
        queryset = queryset.filter(service=service)

    return queryset


class ComponentListView(PermissionListMixin, PaginatedView):
    queryset = Component.objects.all()
    serializer_class = ComponentSerializer
    serializer_class_ui = ComponentUISerializer
    filterset_fields = ("cluster_id", "service_id")
    ordering_fields = ("state", "prototype__display_name", "prototype__version_order")
    permission_required = ["cm.view_component"]
    ordering = ["id"]

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)

        return get_component_queryset(queryset, self.request.user, self.kwargs)


class ComponentDetailView(PermissionListMixin, DetailView):
    queryset = Component.objects.all()
    serializer_class = ComponentDetailSerializer
    serializer_class_ui = ComponentDetailUISerializer
    permission_classes = (DjangoOnlyObjectPermissions,)
    permission_required = ["cm.view_component"]
    lookup_url_kwarg = "component_id"
    error_code = Component.__error_code__
    ordering = ["id"]

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)

        return get_component_queryset(queryset, self.request.user, self.kwargs)


class ComponentMaintenanceModeView(GenericUIView):
    queryset = Component.objects.all()
    permission_classes = (DjangoOnlyObjectPermissions,)
    serializer_class = ComponentChangeMaintenanceModeSerializer
    lookup_field = "id"
    lookup_url_kwarg = "component_id"
    ordering = ["id"]

    @update_mm_objects
    @audit
    def post(self, request: Request, **kwargs) -> Response:
        component = get_object_for_user(
            request.user,
            "cm.view_component",
            Component,
            id=kwargs["component_id"],
        )
        check_custom_perm(request.user, "change_maintenance_mode", component._meta.model_name, component)
        serializer = self.get_serializer(instance=component, data=request.data)
        serializer.is_valid(raise_exception=True)

        response: Response = get_maintenance_mode_response(obj=component, serializer=serializer)
        if response.status_code == HTTP_200_OK:
            response.data = serializer.data

        return response


class StatusList(GenericUIView):
    queryset = HostComponent.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ComponentStatusSerializer
    ordering = ["id"]

    def get(self, request, *args, **kwargs):  # noqa: ARG001, ARG002
        queryset = get_component_queryset(Component.objects.order_by("id"), request.user, kwargs)
        component = get_object_for_user(request.user, "cm.view_component", queryset, id=kwargs["component_id"])
        if self._is_for_ui():
            host_components = self.get_queryset().filter(component=component)

            return Response(make_ui_component_status(component, host_components))

        return Response(self.get_serializer(component).data)
