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

from rest_framework import permissions
from rest_framework.response import Response

import cm.status_api
from api.utils import check_obj
from api.base_view import GenericUIView, PaginatedView
from cm.models import ServiceComponent, ClusterObject, Cluster, HostComponent
from . import serializers


class ComponentListView(PaginatedView):
    queryset = ServiceComponent.objects.all()
    serializer_class = serializers.ComponentSerializer
    serializer_class_ui = serializers.ComponentUISerializer
    filterset_fields = ('cluster_id', 'service_id')
    ordering_fields = ('state', 'prototype__display_name', 'prototype__version_order')

    def get_queryset(self):
        queryset = super().get_queryset()
        kwargs = self.kwargs
        if 'cluster_id' in kwargs:
            cluster = check_obj(Cluster, kwargs['cluster_id'], 'CLUSTER_NOT_FOUND')
            co = check_obj(
                ClusterObject, {'cluster': cluster, 'id': kwargs['service_id']}, 'SERVICE_NOT_FOUND'
            )
            queryset = queryset.filter(cluster=cluster, service=co)
        elif 'service_id' in kwargs:
            co = check_obj(ClusterObject, {'id': kwargs['service_id']}, 'SERVICE_NOT_FOUND')
            queryset = queryset.filter(service=co)
        return queryset


class ComponentDetailView(GenericUIView):
    queryset = ServiceComponent.objects.all()
    serializer_class = serializers.ComponentDetailSerializer
    serializer_class_ui = serializers.ComponentUISerializer

    def get(self, request, *args, **kwargs):
        """
        Show component
        """
        component = check_obj(
            ServiceComponent, {'id': kwargs['component_id']}, 'COMPONENT_NOT_FOUND'
        )
        serializer = self.get_serializer(component)
        return Response(serializer.data)


class StatusList(GenericUIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.StatusSerializer
    model_name = ServiceComponent
    queryset = HostComponent.objects.all()

    def get(self, request, component_id, cluster_id=None, service_id=None):
        """
        Show all components in a specified host
        """
        component = check_obj(ServiceComponent, component_id)
        if self._is_for_ui():
            host_components = self.get_queryset().filter(component=component)
            return Response(cm.status_api.make_ui_component_status(component, host_components))
        else:
            serializer = self.get_serializer(component)
            return Response(serializer.data)
