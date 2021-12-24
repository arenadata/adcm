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

"""Role object candidates view set"""

from rest_framework import serializers, mixins
from rest_framework.response import Response
from rest_framework.decorators import action

from rbac import models
from rbac.viewsets import GenericPermViewSet


class RoleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    parametrized_by_type = serializers.JSONField()
    object_candidate_url = serializers.HyperlinkedIdentityField(
        view_name='rbac-ui:role-object-candidate'
    )


class RoleViewSet(mixins.ListModelMixin, GenericPermViewSet):
    queryset = models.Role.objects.filter(type=models.RoleTypes.role).all()
    serializer_class = RoleSerializer

    @action(methods=['get'], detail=True)
    def object_candidate(self, request, **kwargs):
        role = self.get_object()
        data = {
            'cluster': [role.pk],
            'service': [],
            'provider': [],
            'host': [],
        }
        return Response(data)
