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

from django.db import models
from rest_framework import status
from rest_framework.response import Response

from api.api_views import (
    PageView, create, DetailViewRO, ListView, ActionFilter, GenericAPIPermView, DetailViewDelete
)
from api.serializers import check_obj, filter_actions, TaskRunSerializer
from api.stack_serial import ImportSerializer
from api.cluster_serial import BindSerializer
from cm.api import delete_service, get_import, unbind
from cm.errors import AdcmEx, AdcmApiEx
from cm.models import ClusterObject, Action, TaskLog, ServiceComponent, Prototype, ClusterBind
from . import serializers


class ServiceListView(PageView):
    queryset = ClusterObject.objects.all()
    serializer_class = serializers.ServiceSerializer
    serializer_class_ui = serializers.ServiceUISerializer
    filterset_fields = ('cluster_id', )
    ordering_fields = ('state', 'prototype__display_name', 'prototype__version_order')

    def get(self, request, *args, **kwargs):
        """
        List all services
        """
        return self.get_page(self.filter_queryset(self.get_queryset()), request)

    def post(self, request, *args, **kwargs):
        """
        Add service to cluster
        """
        serializer = self.serializer_class(data=request.data, context={'request': request})
        return create(serializer)


class ServiceDetailView(DetailViewRO):
    queryset = ClusterObject.objects.all()
    serializer_class = serializers.ServiceDetailSerializer
    serializer_class_ui = serializers.ServiceUISerializer

    def get(self, request, *args, **kwargs):
        """
        Show service
        """
        service = check_obj(ClusterObject, {'id': kwargs['service_id']}, 'SERVICE_NOT_FOUND')
        serial_class = self.select_serializer(request)
        serializer = serial_class(service, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        """
        Remove service from cluster
        """
        service = check_obj(ClusterObject, {'id': kwargs['service_id']}, 'SERVICE_NOT_FOUND')
        try:
            delete_service(service)
        except AdcmEx as error:
            raise AdcmApiEx(error.code, error.msg, error.http_code) from error
        return Response(status=status.HTTP_204_NO_CONTENT)


class ServiceActionListView(ListView):
    queryset = Action.objects.filter(prototype__type='service')
    serializer_class = serializers.ServiceActionListSerializer
    serializer_class_ui = serializers.ServiceActionDetailsSerializer
    filterset_class = ActionFilter
    filterset_fields = ('name', 'button', 'button_is_null')

    def get(self, request, *args, **kwargs):
        """
        List all action of a specified service
        """
        service_id = kwargs['service_id']
        service = check_obj(ClusterObject, {'id': service_id}, 'SERVICE_NOT_FOUND')
        actions = filter_actions(
            service, self.filter_queryset(self.get_queryset().filter(prototype=service.prototype)))
        serializer_class = self.select_serializer(request)
        serializer = serializer_class(
            actions, many=True, context={'request': request, 'service_id': service_id})
        return Response(serializer.data)


class ServiceActionView(GenericAPIPermView):
    queryset = Action.objects.filter(prototype__type='service')
    serializer_class = serializers.ServiceActionDetailsSerializer

    def get(self, request, service_id, action_id):
        service = check_obj(ClusterObject, {'id': service_id}, 'SERVICE_NOT_FOUND')
        action = check_obj(
            Action, {'prototype': service.prototype, 'id': action_id}, 'ACTION_NOT_FOUND')
        serializer = self.serializer_class(
            action, context={'request': request, 'service_id': service_id})
        return Response(serializer.data)


class ServiceTask(GenericAPIPermView):
    queryset = TaskLog.objects.all()
    serializer_class = TaskRunSerializer

    def post(self, request, service_id, action_id):
        """
        Run specified action of a specified service
        """
        service = check_obj(ClusterObject, {'id': service_id}, 'SERVICE_NOT_FOUND')
        action = check_obj(
            Action, {'prototype': service.prototype, 'id': action_id}, 'ACTION_NOT_FOUND')
        selector = {'cluster': service.cluster.id, 'service': service.id}
        serializer = self.serializer_class(data=request.data, context={'request': request})
        return create(serializer, action_id=action.id, selector=selector)


class ServiceComponentListView(PageView):
    queryset = ServiceComponent.objects.all()
    serializer_class = serializers.ServiceComponentSerializer
    serializer_class_ui = serializers.ServiceComponentDetailSerializer
    ordering_fields = ('component__display_name', )

    def get(self, request, *args, **kwargs):
        """
        Show components of service
        """
        service = check_obj(ClusterObject, {'id': kwargs['service_id']}, 'SERVICE_NOT_FOUND')
        components = self.filter_queryset(self.get_queryset().filter(service=service))
        return self.get_page(components, request)


class ServiceComponentDetailView(GenericAPIPermView):
    queryset = ServiceComponent.objects.all()
    serializer_class = serializers.ServiceComponentDetailSerializer

    def get(self, request, service_id, component_id):
        """
        Show specified component of service
        """
        service = check_obj(ClusterObject, {'id': service_id}, 'SERVICE_NOT_FOUND')
        service_component = check_obj(
            ServiceComponent, {'id': component_id, 'service': service}, 'COMPONENT_NOT_FOUND')
        serializer = self.serializer_class(service_component, context={'request': request})
        return Response(serializer.data)


class ServiceImportView(ListView):
    queryset = Prototype.objects.all()
    serializer_class = ImportSerializer
    post_serializer_class = serializers.ImportPostSerializer

    def get(self, request, *args, **kwargs):
        """
        List all imports available for specified service
        """

        service = check_obj(ClusterObject, {'id': kwargs['service_id']}, 'SERVICE_NOT_FOUND')
        try:
            cluster = service.cluster
        except models.ObjectDoesNotExist:
            raise AdcmApiEx('CLUSTER_NOT_FOUND') from None

        return Response(get_import(cluster, service))

    def post(self, request, service_id):
        service = check_obj(ClusterObject, {'id': service_id}, 'SERVICE_NOT_FOUND')
        try:
            cluster = service.cluster
        except models.ObjectDoesNotExist:
            raise AdcmApiEx('CLUSTER_NOT_FOUND') from None
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
        service = check_obj(ClusterObject, {'id': kwargs['service_id']}, 'SERVICE_NOT_FOUND')
        binds = self.get_queryset().filter(service=service)
        serializer = self.get_serializer_class()(binds, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, service_id):
        """
        Bind two services
        """
        service = check_obj(ClusterObject, {'id': service_id}, 'SERVICE_NOT_FOUND')
        try:
            cluster = service.cluster
        except models.ObjectDoesNotExist:
            raise AdcmApiEx('CLUSTER_NOT_FOUND') from None
        serializer = self.get_serializer_class()(data=request.data, context={'request': request})
        return create(serializer, cluster=cluster, service=service)


class ServiceBindDetailView(DetailViewDelete):
    queryset = ClusterBind.objects.all()
    serializer_class = BindSerializer

    def get_obj(self, service_id, bind_id):
        service = check_obj(ClusterObject, service_id, 'SERVICE_NOT_FOUND')
        try:
            cluster = service.cluster
        except models.ObjectDoesNotExist:
            AdcmApiEx('CLUSTER_NOT_FOUND')
        return check_obj(ClusterBind, {'cluster': cluster, 'id': bind_id}, 'BIND_NOT_FOUND')

    def get(self, request, *args, **kwargs):
        """
        Show specified bind of service
        """
        bind = self.get_obj(kwargs['service_id'], kwargs['bind_id'])
        serializer = self.serializer_class(bind, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        """
        Unbind specified bind of service
        """
        bind = self.get_obj(kwargs['service_id'], kwargs['bind_id'])
        unbind(bind)
        return Response(status=status.HTTP_204_NO_CONTENT)
