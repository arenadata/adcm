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

from rest_framework import viewsets

from rbac.models import Role

from .serializers import RoleSerializer


# pylint: disable=too-many-ancestors
class RoleViewSet(viewsets.ModelViewSet):
    """Role View Set"""

    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    lookup_field = 'id'
    filterset_fields = ['id', 'name']
    ordering_fields = ['id', 'name']
