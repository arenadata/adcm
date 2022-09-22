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

from guardian.mixins import PermissionListMixin
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST

from api.base_view import DetailView, GenericUIView, PaginatedView
from api.cluster.serializers import BindSerializer
from api.service.serializers import (
    ClusterServiceSerializer,
    ImportPostSerializer,
    ServiceBindPostSerializer,
    ServiceBindSerializer,
    ServiceDetailSerializer,
    ServiceSerializer,
    ServiceUISerializer,
    StatusSerializer,
)
from api.stack.serializers import ImportSerializer
from api.utils import check_custom_perm, check_obj, create, get_object_for_user
from audit.utils import audit
from cm.api import delete_service, get_import, unbind
from cm.errors import raise_adcm_ex
from cm.models import Cluster, ClusterBind, ClusterObject, HostComponent, Prototype
from cm.status_api import make_ui_service_status
from rbac.viewsets import DjangoOnlyObjectPermissions


def check_service(user, kwargs):
    service = get_object_for_user(
        user, 'cm.view_clusterobject', ClusterObject, id=kwargs['service_id']
    )
    if 'cluster_id' in kwargs:
        get_object_for_user(user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id'])
    return service


class ServiceListView(PermissionListMixin, PaginatedView):
    queryset = ClusterObject.objects.all()
    permission_required = ['cm.view_clusterobject']
    serializer_class = ServiceSerializer
    serializer_class_ui = ServiceUISerializer
    serializer_class_cluster = ClusterServiceSerializer
    filterset_fields = ('cluster_id',)
    ordering_fields = ('state', 'prototype__display_name', 'prototype__version_order')

    def get(self, request, *args, **kwargs):
        """
        List all services
        """
        queryset = self.get_queryset()
        if 'cluster_id' in kwargs:
            cluster = get_object_for_user(
                request.user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id']
            )
            queryset = queryset.filter(cluster=cluster).select_related("config")
        return self.get_page(self.filter_queryset(queryset), request)

    @audit
    def post(self, request, *args, **kwargs):
        """
        Add service to cluster
        """
        serializer_class = self.serializer_class
        if 'cluster_id' in kwargs:
            serializer_class = self.serializer_class_cluster
            cluster = get_object_for_user(
                request.user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id']
            )
        else:
            cluster = get_object_for_user(
                request.user, 'cm.view_cluster', Cluster, id=request.data['cluster_id']
            )
        check_custom_perm(request.user, 'add_service_to', 'cluster', cluster)
        serializer = serializer_class(
            data=request.data,
            context={'request': request, 'cluster_id': kwargs.get('cluster_id', None)},
        )
        return create(serializer)


class ServiceDetailView(PermissionListMixin, DetailView):
    queryset = ClusterObject.objects.all()
    serializer_class = ServiceDetailSerializer
    serializer_class_ui = ServiceUISerializer
    permission_classes = (DjangoOnlyObjectPermissions,)
    lookup_url_kwarg = 'service_id'
    permission_required = ['cm.view_clusterobject']
    error_code = ClusterObject.__error_code__

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if 'cluster_id' in self.kwargs:
            cluster = get_object_for_user(
                self.request.user, 'cm.view_cluster', Cluster, id=self.kwargs['cluster_id']
            )
            queryset = queryset.filter(cluster=cluster)
        return queryset

    @audit
    def delete(self, request, *args, **kwargs):
        """
        Remove service from cluster
        """
        instance = self.get_object()
        if instance.state != "created":
            raise_adcm_ex("SERVICE_DELETE_ERROR")
        delete_service(instance)

        return Response(status=HTTP_204_NO_CONTENT)


class ServiceImportView(GenericUIView):
    queryset = Prototype.objects.all()
    serializer_class = ImportSerializer
    serializer_class_post = ImportPostSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """
        List all imports available for specified service
        """
        service = check_service(request.user, kwargs)
        check_custom_perm(
            request.user, 'view_import_of', 'clusterobject', service, 'view_clusterbind'
        )
        cluster = service.cluster
        return Response(get_import(cluster, service))

    @audit
    def post(self, request, **kwargs):
        service = check_service(request.user, kwargs)
        check_custom_perm(request.user, 'change_import_of', 'clusterobject', service)
        cluster = service.cluster
        serializer = self.get_serializer(
            data=request.data, context={'request': request, 'cluster': cluster, 'service': service}
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
        """
        List all binds of service
        """
        service = check_service(request.user, kwargs)
        check_custom_perm(
            request.user, 'view_import_of', 'clusterobject', service, 'view_clusterbind'
        )
        binds = self.get_queryset().filter(service=service)
        serializer = self.get_serializer(binds, many=True)
        return Response(serializer.data)

    @audit
    def post(self, request, **kwargs):
        """
        Bind two services
        """
        service = check_service(request.user, kwargs)
        check_custom_perm(request.user, 'change_import_of', 'clusterobject', service)
        cluster = service.cluster
        serializer = self.get_serializer(data=request.data)
        return create(serializer, cluster=cluster, service=service)


class ServiceBindDetailView(GenericUIView):
    queryset = ClusterBind.objects.all()
    serializer_class = BindSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_obj(self, kwargs, bind_id):
        service = check_service(self.request.user, kwargs)
        cluster = service.cluster
        return service, check_obj(ClusterBind, {'cluster': cluster, 'id': bind_id})

    def get(self, request, *args, **kwargs):
        """
        Show specified bind of service
        """
        service, bind = self.get_obj(kwargs, kwargs['bind_id'])
        check_custom_perm(
            request.user, 'view_import_of', 'clusterobject', service, 'view_clusterbind'
        )
        serializer = self.get_serializer(bind)
        return Response(serializer.data)

    @audit
    def delete(self, request, *args, **kwargs):
        """
        Unbind specified bind of service
        """
        service, bind = self.get_obj(kwargs, kwargs['bind_id'])
        check_custom_perm(request.user, 'change_import_of', 'clusterobject', service)
        unbind(bind)
        return Response(status=HTTP_204_NO_CONTENT)


class StatusList(GenericUIView):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = HostComponent.objects.all()
    serializer_class = StatusSerializer

    def get(self, request, *args, **kwargs):
        """
        Show all hosts and components in a specified cluster
        """
        service = check_service(request.user, kwargs)
        if self._is_for_ui():
            host_components = self.get_queryset().filter(service=service)
            return Response(make_ui_service_status(service, host_components))
        else:
            serializer = self.get_serializer(service)
            return Response(serializer.data)
