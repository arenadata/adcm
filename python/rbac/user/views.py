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
from django.contrib.auth.models import User

from .serializers import UserSerializer


# pylint: disable=too-many-ancestors
class UserViewSet(viewsets.ModelViewSet):
    """User View Set"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'id'
    filterset_fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_superuser']
    ordering_fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_superuser']
