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

from django.contrib.auth.models import User, Group
from rest_framework import status
from rest_framework import viewsets
from rest_framework.mixins import (
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
)
from rest_framework.response import Response

from .serializers import UserSerializer, UserGroupSerializer


# pylint: disable=too-many-ancestors
class UserViewSet(viewsets.ModelViewSet):
    """User View Set"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'id'
    filterset_fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_superuser']
    ordering_fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_superuser']


class UserGroupViewSet(
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    viewsets.GenericViewSet,
):  # pylint: disable=too-many-ancestors
    queryset = Group.objects.all()
    serializer_class = UserGroupSerializer
    lookup_url_kwarg = 'group_id'

    def destroy(self, request, *args, **kwargs):
        user = User.objects.get(id=self.kwargs.get('id'))
        group = self.get_object()
        user.groups.remove(group)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        return self.queryset.filter(user__id=self.kwargs.get('id'))

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user_id = self.kwargs.get('id')
        if user_id is not None:
            user = User.objects.get(id=user_id)
            context.update({'user': user})
        return context
