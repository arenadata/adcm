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
from cm.api import get_import, unbind
from cm.models import Cluster, ClusterBind, HostComponent, Prototype, Service
from cm.services.maintenance_mode import get_maintenance_mode_response
from cm.services.service import delete_service_from_api
from cm.services.status.notify import update_mm_objects
from cm.status_api import make_ui_service_status
from guardian.mixins import PermissionListMixin
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST

from api.base_view import DetailView, GenericUIView, PaginatedView
from api.cluster.serializers import BindSerializer
from api.rbac.viewsets import DjangoOnlyObjectPermissions
from api.service.serializers import (
    ClusterServiceSerializer,
    ImportPostSerializer,
    ServiceBindPostSerializer,
    ServiceBindSerializer,
    ServiceChangeMaintenanceModeSerializer,
    ServiceDetailSerializer,
    ServiceDetailUISerializer,
    ServiceSerializer,
    ServiceStatusSerializer,
    ServiceUISerializer,
)
from api.stack.serializers import ImportSerializer
from api.utils import check_obj, create


class ServiceListView(PermissionListMixin, PaginatedView):
    queryset = Service.objects.all()
    permission_required = ["cm.view_service"]
    serializer_class = ServiceSerializer
    serializer_class_ui = ServiceUISerializer
    serializer_class_cluster = ClusterServiceSerializer
    filterset_fields = ("cluster_id",)
    ordering_fields = ("id", "state", "prototype__display_name", "prototype__version_order")
    ordering = ["id"]

    def get(self, request, *_, **kwargs):  # noqa: ARG002
        queryset = self.get_queryset()
        if "cluster_id" in kwargs:
            cluster = get_object_for_user(request.user, "cm.view_cluster", Cluster, id=kwargs["cluster_id"])
            queryset = queryset.filter(cluster=cluster).select_related("config")

        return self.get_page(self.filter_queryset(queryset), request)

    @audit
    def post(self, request, *args, **kwargs):  # noqa: ARG002
        serializer_class = self.serializer_class
        if "cluster_id" in kwargs:
            serializer_class = self.serializer_class_cluster
            cluster = get_object_for_user(request.user, "cm.view_cluster", Cluster, id=kwargs["cluster_id"])
        else:
            cluster = get_object_for_user(request.user, "cm.view_cluster", Cluster, id=request.data["cluster_id"])

        check_custom_perm(request.user, "add_service_to", "cluster", cluster)
        serializer = serializer_class(
            data=request.data,
            context={"request": request, "cluster_id": kwargs.get("cluster_id", None)},
        )

        return create(serializer)


class ServiceDetailView(PermissionListMixin, DetailView):
    queryset = Service.objects.all()
    serializer_class = ServiceDetailSerializer
    serializer_class_ui = ServiceDetailUISerializer
    permission_classes = (DjangoOnlyObjectPermissions,)
    lookup_url_kwarg = "service_id"
    permission_required = ["cm.view_service"]
    error_code = Service.__error_code__
    ordering = ["id"]

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if "cluster_id" in self.kwargs:
            cluster = get_object_for_user(self.request.user, "cm.view_cluster", Cluster, id=self.kwargs["cluster_id"])
            queryset = queryset.filter(cluster=cluster)

        return queryset

    @audit
    def delete(self, request, *args, **kwargs):  # noqa: ARG002
        instance: Service = self.get_object()
        return delete_service_from_api(service=instance)


class ServiceMaintenanceModeView(GenericUIView):
    queryset = Service.objects.all()
    permission_classes = (DjangoOnlyObjectPermissions,)
    serializer_class = ServiceChangeMaintenanceModeSerializer
    lookup_field = "id"
    lookup_url_kwarg = "service_id"
    ordering = ["id"]

    @update_mm_objects
    @audit
    def post(self, request: Request, **kwargs) -> Response:
        service = get_object_for_user(request.user, "cm.view_service", Service, id=kwargs["service_id"])
        check_custom_perm(request.user, "change_maintenance_mode", service.__class__.__name__.lower(), service)
        serializer = self.get_serializer(instance=service, data=request.data)
        serializer.is_valid(raise_exception=True)

        response: Response = get_maintenance_mode_response(obj=service, serializer=serializer)
        if response.status_code == HTTP_200_OK:
            response.data = serializer.data

        return response


class ServiceImportView(GenericUIView):
    queryset = Prototype.objects.all()
    serializer_class = ImportSerializer
    serializer_class_post = ImportPostSerializer
    permission_classes = (permissions.IsAuthenticated,)
    ordering = ["id"]

    @staticmethod
    def get(request, *_, **kwargs):
        service = get_object_for_user(request.user, "cm.view_service", Service, id=kwargs["service_id"])
        check_custom_perm(request.user, "view_import_of", "service", service, "view_clusterbind")
        cluster = service.cluster

        return Response(get_import(cluster, service))

    @audit
    def post(self, request, **kwargs):
        service = get_object_for_user(request.user, "cm.view_service", Service, id=kwargs["service_id"])
        check_custom_perm(request.user, "change_import_of", "service", service)
        cluster = service.cluster
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request, "cluster": cluster, "service": service},
        )
        if serializer.is_valid():
            return Response(serializer.create(serializer.validated_data), status=HTTP_200_OK)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ServiceBindView(GenericUIView):
    queryset = ClusterBind.objects.all()
    serializer_class = ServiceBindSerializer
    serializer_class_post = ServiceBindPostSerializer
    permission_classes = (permissions.IsAuthenticated,)
    ordering = ["id"]

    def get(self, request, *args, **kwargs):  # noqa: ARG002
        service = get_object_for_user(request.user, "cm.view_service", Service, id=kwargs["service_id"])
        check_custom_perm(request.user, "view_import_of", "service", service, "view_clusterbind")
        binds = self.get_queryset().filter(service=service)
        serializer = self.get_serializer(binds, many=True)

        return Response(serializer.data)

    @audit
    def post(self, request, **kwargs):
        service = get_object_for_user(request.user, "cm.view_service", Service, id=kwargs["service_id"])
        check_custom_perm(request.user, "change_import_of", "service", service)
        cluster = service.cluster
        serializer = self.get_serializer(data=request.data)

        return create(serializer, cluster=cluster, service=service)


class ServiceBindDetailView(GenericUIView):
    queryset = ClusterBind.objects.all()
    serializer_class = BindSerializer
    permission_classes = (permissions.IsAuthenticated,)
    ordering = ["id"]

    def get_obj(self, kwargs, bind_id):
        service = get_object_for_user(
            self.request.user,
            "cm.view_service",
            Service,
            id=kwargs["service_id"],
        )
        cluster = service.cluster

        return service, check_obj(ClusterBind, {"cluster": cluster, "id": bind_id})

    def get(self, request, *args, **kwargs):  # noqa: ARG002
        service, bind = self.get_obj(kwargs, kwargs["bind_id"])
        check_custom_perm(request.user, "view_import_of", "service", service, "view_clusterbind")
        serializer = self.get_serializer(bind)

        return Response(serializer.data)

    @audit
    def delete(self, request, *args, **kwargs):  # noqa: ARG002
        service, bind = self.get_obj(kwargs, kwargs["bind_id"])
        check_custom_perm(request.user, "change_import_of", "service", service)
        unbind(bind)

        return Response(status=HTTP_204_NO_CONTENT)


class StatusList(GenericUIView):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = HostComponent.objects.all()
    serializer_class = ServiceStatusSerializer
    ordering = ["id"]

    def get(self, request, *args, **kwargs):  # noqa: ARG002
        service = get_object_for_user(request.user, "cm.view_service", Service, id=kwargs["service_id"])
        if self._is_for_ui():
            host_components = self.get_queryset().filter(service=service)

            return Response(make_ui_service_status(service, host_components))

        return Response(self.get_serializer(service).data)
