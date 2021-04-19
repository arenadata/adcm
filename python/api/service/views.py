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

from rest_framework import status
from rest_framework.response import Response

from api.api_views import (
    PageView, create, check_obj, DetailViewRO, ListView, DetailViewDelete
)
from api.stack_serial import ImportSerializer
from api.cluster_serial import BindSerializer

from cm.api import delete_service, get_import, unbind
from cm.models import Cluster, ClusterObject, Prototype, ClusterBind
from . import serializers


def check_service(kwargs):
    service = check_obj(ClusterObject, kwargs['service_id'])
    if 'cluster_id' in kwargs:
        check_obj(Cluster, kwargs['cluster_id'])
    return service


class ServiceListView(PageView):
    queryset = ClusterObject.objects.all()
    serializer_class = serializers.ServiceSerializer
    serializer_class_ui = serializers.ServiceUISerializer
    serializer_class_cluster = serializers.ClusterServiceSerializer
    filterset_fields = ('cluster_id', )
    ordering_fields = ('state', 'prototype__display_name', 'prototype__version_order')

    def get(self, request, *args, **kwargs):
        """
        List all services
        """
        queryset = self.get_queryset()
        if 'cluster_id' in kwargs:
            cluster = check_obj(Cluster, kwargs['cluster_id'])
            queryset = self.get_queryset().filter(cluster=cluster)
        return self.get_page(self.filter_queryset(queryset), request)

    def post(self, request, *args, **kwargs):
        """
        Add service to cluster
        """
        serializer_class = self.serializer_class
        if 'cluster_id' in kwargs:
            serializer_class = self.serializer_class_cluster
        serializer = serializer_class(data=request.data, context={
            'request': request, 'cluster_id': kwargs.get('cluster_id', None)}
        )
        return create(serializer)


class ServiceDetailView(DetailViewRO):
    queryset = ClusterObject.objects.all()
    serializer_class = serializers.ServiceDetailSerializer
    serializer_class_ui = serializers.ServiceUISerializer

    def get(self, request, *args, **kwargs):
        """
        Show service
        """
        service = check_service(kwargs)
        serial_class = self.select_serializer(request)
        serializer = serial_class(service, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        """
        Remove service from cluster
        """
        service = check_service(kwargs)
        delete_service(service)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ServiceImportView(ListView):
    queryset = Prototype.objects.all()
    serializer_class = ImportSerializer
    post_serializer_class = serializers.ImportPostSerializer

    def get(self, request, *args, **kwargs):
        """
        List all imports available for specified service
        """
        service = check_service(kwargs)
        cluster = service.cluster
        return Response(get_import(cluster, service))

    def post(self, request, **kwargs):
        service = check_service(kwargs)
        cluster = service.cluster
        serializer = self.post_serializer_class(
            data=request.data,
            context={'request': request, 'cluster': cluster, 'service': service})
        if serializer.is_valid():
            return Response(
                serializer.create(serializer.validated_data), status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServiceBindView(ListView):
    queryset = ClusterBind.objects.all()
    serializer_class = serializers.ServiceBindSerializer

    def get_serializer_class(self):
        if self.request and self.request.method == 'POST':
            return serializers.ServiceBindPostSerializer
        else:
            return serializers.ServiceBindSerializer

    def get(self, request, *args, **kwargs):
        """
        List all binds of service
        """
        service = check_service(kwargs)
        binds = self.get_queryset().filter(service=service)
        serializer = self.get_serializer_class()(binds, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, **kwargs):
        """
        Bind two services
        """
        service = check_service(kwargs)
        cluster = service.cluster
        serializer = self.get_serializer_class()(data=request.data, context={'request': request})
        return create(serializer, cluster=cluster, service=service)


class ServiceBindDetailView(DetailViewDelete):
    queryset = ClusterBind.objects.all()
    serializer_class = BindSerializer

    def get_obj(self, kwargs, bind_id):
        service = check_service(kwargs)
        cluster = service.cluster
        return check_obj(ClusterBind, {'cluster': cluster, 'id': bind_id})

    def get(self, request, *args, **kwargs):
        """
        Show specified bind of service
        """
        bind = self.get_obj(kwargs, kwargs['bind_id'])
        serializer = self.serializer_class(bind, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        """
        Unbind specified bind of service
        """
        bind = self.get_obj(kwargs, kwargs['bind_id'])
        unbind(bind)
        return Response(status=status.HTTP_204_NO_CONTENT)
