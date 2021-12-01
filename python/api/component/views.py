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

from rest_framework.response import Response

from api.api_views import PageView, check_obj, DetailViewRO, InterfaceView, GenericAPIPermStatusView
from cm.models import ServiceComponent, ClusterObject, Cluster, HostComponent
from . import serializers
import cm.status_api


class ComponentListView(PageView):
    queryset = ServiceComponent.objects.all()
    serializer_class = serializers.ComponentSerializer
    serializer_class_ui = serializers.ComponentUISerializer
    filterset_fields = ('cluster_id', 'service_id')
    ordering_fields = ('state', 'prototype__display_name', 'prototype__version_order')

    def get(self, request, *args, **kwargs):
        """
        List all components
        """
        queryset = self.get_queryset()
        if 'cluster_id' in kwargs:
            cluster = check_obj(Cluster, kwargs['cluster_id'], 'CLUSTER_NOT_FOUND')
            co = check_obj(
                ClusterObject, {'cluster': cluster, 'id': kwargs['service_id']}, 'SERVICE_NOT_FOUND'
            )
            queryset = self.get_queryset().filter(cluster=cluster, service=co)
        elif 'service_id' in kwargs:
            co = check_obj(ClusterObject, {'id': kwargs['service_id']}, 'SERVICE_NOT_FOUND')
            queryset = self.get_queryset().filter(service=co)
        return self.get_page(self.filter_queryset(queryset), request)


class ComponentDetailView(DetailViewRO):
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
        serial_class = self.select_serializer(request)
        serializer = serial_class(component, context={'request': request})
        return Response(serializer.data)


class StatusList(GenericAPIPermStatusView, InterfaceView):
    serializer_class = serializers.StatusSerializer
    model_name = ServiceComponent
    queryset = HostComponent.objects.all()

    def ui_status(self, component, host_components):
        host_list = []
        for hc in host_components:
            host_list.append(
                {
                    'id': hc.host.id,
                    'name': hc.host.fqdn,
                    'status': cm.status_api.get_host_comp_status(hc.host, hc.component),
                }
            )
        return {
            'id': component.id,
            'name': component.display_name,
            'status': cm.status_api.get_component_status(component),
            'hosts': host_list,
        }

    def get(self, request, component_id, cluster_id=None, service_id=None):
        """
        Show all components in a specified host
        """
        component = check_obj(ServiceComponent, component_id)
        hc_queryset = self.get_queryset().filter(component=component)
        if self.for_ui(request):
            return Response(self.ui_status(component, hc_queryset))
        else:
            serializer = self.serializer_class(component, context={'request': request})
            return Response(serializer.data)
