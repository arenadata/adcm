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


from rest_framework.viewsets import ModelViewSet

from cm.models import GroupConfigHost
from .serializers import GroupConfigHostSerializer


class GroupConfigHostViewSet(ModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = GroupConfigHost.objects.all()
    serializer_class = GroupConfigHostSerializer
    filterset_fields = ('group', 'host')
