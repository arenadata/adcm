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

from api.api_views import PageView, check_obj, DetailViewRO
from cm.models import ServiceComponent, ClusterObject, Cluster
from . import serializers


class ComponentListView(PageView):
    queryset = ServiceComponent.objects.all()
    serializer_class = serializers.ComponentSerializer
    serializer_class_ui = serializers.ComponentUISerializer
    filterset_fields = ('cluster_id', )
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
