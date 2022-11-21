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

from django.conf import settings
from guardian.mixins import PermissionListMixin
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST

from api.base_view import DetailView, GenericUIView, PaginatedView
from api.cluster.serializers import BindSerializer
from api.service.serializers import (
    ClusterServiceSerializer,
    ImportPostSerializer,
    ServiceBindPostSerializer,
    ServiceBindSerializer,
    ServiceChangeMaintenanceModeSerializer,
    ServiceDetailSerializer,
    ServiceDetailUISerializer,
    ServiceSerializer,
    ServiceUISerializer,
    StatusSerializer,
)
from api.stack.serializers import ImportSerializer
from api.utils import (
    check_custom_perm,
    check_obj,
    create,
    get_maintenance_mode_response,
    get_object_for_user,
)
from audit.utils import audit
from cm.api import (
    cancel_locking_tasks,
    delete_service,
    get_import,
    unbind,
    update_mm_objects,
)
from cm.errors import raise_adcm_ex
from cm.job import start_task
from cm.models import (
    Action,
    Cluster,
    ClusterBind,
    ClusterObject,
    HostComponent,
    JobStatus,
    Prototype,
    TaskLog,
)
from cm.status_api import make_ui_service_status
from rbac.viewsets import DjangoOnlyObjectPermissions


class ServiceListView(PermissionListMixin, PaginatedView):
    queryset = ClusterObject.objects.all()
    permission_required = ["cm.view_clusterobject"]
    serializer_class = ServiceSerializer
    serializer_class_ui = ServiceUISerializer
    serializer_class_cluster = ClusterServiceSerializer
    filterset_fields = ("cluster_id",)
    ordering_fields = ("state", "prototype__display_name", "prototype__version_order")

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if "cluster_id" in kwargs:
            cluster = get_object_for_user(request.user, "cm.view_cluster", Cluster, id=kwargs["cluster_id"])
            queryset = queryset.filter(cluster=cluster).select_related("config")

        return self.get_page(self.filter_queryset(queryset), request)

    @audit
    def post(self, request, *args, **kwargs):
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
    queryset = ClusterObject.objects.all()
    serializer_class = ServiceDetailSerializer
    serializer_class_ui = ServiceDetailUISerializer
    permission_classes = (DjangoOnlyObjectPermissions,)
    lookup_url_kwarg = "service_id"
    permission_required = ["cm.view_clusterobject"]
    error_code = ClusterObject.__error_code__

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if "cluster_id" in self.kwargs:
            cluster = get_object_for_user(self.request.user, "cm.view_cluster", Cluster, id=self.kwargs["cluster_id"])
            queryset = queryset.filter(cluster=cluster)

        return queryset

    @audit
    def delete(self, request, *args, **kwargs):
        instance: ClusterObject = self.get_object()
        delete_action = Action.objects.filter(
            prototype=instance.prototype, name=settings.ADCM_DELETE_SERVICE_ACTION_NAME
        ).first()

        if not delete_action:
            if instance.state != "created":
                raise_adcm_ex("SERVICE_DELETE_ERROR")

            if HostComponent.objects.filter(cluster=instance.cluster, service=instance).exists():
                raise_adcm_ex("SERVICE_CONFLICT", f"Service #{instance.id} has component(s) on host(s)")

        if ClusterBind.objects.filter(source_service=instance).exists():
            raise_adcm_ex("SERVICE_CONFLICT", f"Service #{instance.id} has exports(s)")

        if instance.has_another_service_requires:
            raise_adcm_ex("SERVICE_CONFLICT", f"Service #{instance.id} has another service requires host components")

        if instance.prototype.required:
            raise_adcm_ex("SERVICE_CONFLICT", f"Service #{instance.id} is required")

        if ClusterBind.objects.filter(service=instance).exists():
            raise_adcm_ex("SERVICE_CONFLICT", f"Service #{instance.id} has bind")

        if TaskLog.objects.filter(action=delete_action, status=JobStatus.RUNNING).exists():
            raise_adcm_ex("SERVICE_DELETE_ERROR", "Service is deleting now")

        if delete_action:
            start_task(
                action=delete_action,
                obj=instance,
                conf={},
                attr={},
                hc=[],
                hosts=[],
                verbose=False,
            )
        else:
            cancel_locking_tasks(obj=instance, obj_deletion=True)
            delete_service(service=instance)

        return Response(status=HTTP_204_NO_CONTENT)


class ServiceMaintenanceModeView(GenericUIView):
    queryset = ClusterObject.objects.all()
    permission_classes = (DjangoOnlyObjectPermissions,)
    serializer_class = ServiceChangeMaintenanceModeSerializer
    lookup_field = "id"
    lookup_url_kwarg = "service_id"

    @update_mm_objects
    @audit
    def post(self, request: Request, **kwargs) -> Response:
        service = get_object_for_user(request.user, "cm.view_clusterobject", ClusterObject, id=kwargs["service_id"])
        check_custom_perm(request.user, "change_maintenance_mode", service.__class__.__name__.lower(), service)
        serializer = self.get_serializer(instance=service, data=request.data)
        serializer.is_valid(raise_exception=True)

        return get_maintenance_mode_response(obj=service, serializer=serializer)


class ServiceImportView(GenericUIView):
    queryset = Prototype.objects.all()
    serializer_class = ImportSerializer
    serializer_class_post = ImportPostSerializer
    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request, *args, **kwargs):
        service = get_object_for_user(request.user, "cm.view_clusterobject", ClusterObject, id=kwargs["service_id"])
        check_custom_perm(request.user, "view_import_of", "clusterobject", service, "view_clusterbind")
        cluster = service.cluster

        return Response(get_import(cluster, service))

    @audit
    def post(self, request, **kwargs):
        service = get_object_for_user(request.user, "cm.view_clusterobject", ClusterObject, id=kwargs["service_id"])
        check_custom_perm(request.user, "change_import_of", "clusterobject", service)
        cluster = service.cluster
        serializer = self.get_serializer(
            data=request.data, context={"request": request, "cluster": cluster, "service": service}
        )
        if serializer.is_valid():
            return Response(serializer.create(serializer.validated_data), status=HTTP_200_OK)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ServiceBindView(GenericUIView):
    queryset = ClusterBind.objects.all()
    serializer_class = ServiceBindSerializer
    serializer_class_post = ServiceBindPostSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        service = get_object_for_user(request.user, "cm.view_clusterobject", ClusterObject, id=kwargs["service_id"])
        check_custom_perm(request.user, "view_import_of", "clusterobject", service, "view_clusterbind")
        binds = self.get_queryset().filter(service=service)
        serializer = self.get_serializer(binds, many=True)

        return Response(serializer.data)

    @audit
    def post(self, request, **kwargs):
        service = get_object_for_user(request.user, "cm.view_clusterobject", ClusterObject, id=kwargs["service_id"])
        check_custom_perm(request.user, "change_import_of", "clusterobject", service)
        cluster = service.cluster
        serializer = self.get_serializer(data=request.data)

        return create(serializer, cluster=cluster, service=service)


class ServiceBindDetailView(GenericUIView):
    queryset = ClusterBind.objects.all()
    serializer_class = BindSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_obj(self, kwargs, bind_id):
        service = get_object_for_user(
            self.request.user, "cm.view_clusterobject", ClusterObject, id=kwargs["service_id"]
        )
        cluster = service.cluster

        return service, check_obj(ClusterBind, {"cluster": cluster, "id": bind_id})

    def get(self, request, *args, **kwargs):
        service, bind = self.get_obj(kwargs, kwargs["bind_id"])
        check_custom_perm(request.user, "view_import_of", "clusterobject", service, "view_clusterbind")
        serializer = self.get_serializer(bind)

        return Response(serializer.data)

    @audit
    def delete(self, request, *args, **kwargs):
        service, bind = self.get_obj(kwargs, kwargs["bind_id"])
        check_custom_perm(request.user, "change_import_of", "clusterobject", service)
        unbind(bind)

        return Response(status=HTTP_204_NO_CONTENT)


class StatusList(GenericUIView):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = HostComponent.objects.all()
    serializer_class = StatusSerializer

    def get(self, request, *args, **kwargs):
        service = get_object_for_user(request.user, "cm.view_clusterobject", ClusterObject, id=kwargs["service_id"])
        if self._is_for_ui():
            host_components = self.get_queryset().filter(service=service)

            return Response(make_ui_service_status(service, host_components))

        return Response(self.get_serializer(service).data)
