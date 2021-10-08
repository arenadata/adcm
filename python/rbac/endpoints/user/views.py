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

"""User view sets"""

from django.contrib.auth.models import User, Group
from rest_framework import serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.mixins import (
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    UpdateModelMixin,
)

from rbac.models import Role
from rbac.viewsets import ModelPermViewSet, GenericPermViewSet, DjangoModelPerm
from .serializers import UserSerializer, UserGroupSerializer, UserRoleSerializer


class SelfChangePasswordPerm(DjangoModelPerm):
    """
    User self change password permissions class.
    Use codename self_change_password to check permissions
    """

    def __init__(self, *args, **kwargs):
        """Replace PUT permissions from "change" to "self_change_password"""
        super().__init__(*args, **kwargs)
        self.perms_map['PUT'] = ['%(app_label)s.self_change_password_%(model_name)s']

    def has_object_permission(self, request, view, obj):
        """Check that user change his/her own password"""
        if request.user != obj:
            return False
        return True


class PasswordSerializer(UserSerializer):
    """UserSerializer with only one changable field - password"""

    username = serializers.CharField(read_only=True)


class ChangePassword(GenericAPIView, UpdateModelMixin):
    """User self change password view"""

    queryset = User.objects.all()
    serializer_class = PasswordSerializer
    lookup_field = 'id'
    permission_classes = (SelfChangePasswordPerm,)

    def put(self, request, *args, **kwargs):
        """Update password"""
        return self.update(request, *args, **kwargs)


# pylint: disable=too-many-ancestors
class UserViewSet(ModelPermViewSet):
    """User view set"""

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
    GenericPermViewSet,
):  # pylint: disable=too-many-ancestors
    """User group view set"""

    queryset = Group.objects.all()
    serializer_class = UserGroupSerializer
    lookup_url_kwarg = 'group_id'

    def destroy(self, request, *args, **kwargs):
        """Remove user"""
        user = User.objects.get(id=self.kwargs.get('id'))
        group = self.get_object()
        user.groups.remove(group)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        """Filter user's groups"""
        return self.queryset.filter(user__id=self.kwargs.get('id'))

    def get_serializer_context(self):
        """Add user to context"""
        context = super().get_serializer_context()
        user_id = self.kwargs.get('id')
        if user_id is not None:
            user = User.objects.get(id=user_id)
            context.update({'user': user})
        return context


class UserRoleViewSet(
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    GenericPermViewSet,
):  # pylint: disable=too-many-ancestors
    """User role view set"""

    queryset = Role.objects.all()
    serializer_class = UserRoleSerializer
    lookup_url_kwarg = 'role_id'

    def destroy(self, request, *args, **kwargs):
        """Remove role from user"""
        user = User.objects.get(id=self.kwargs.get('id'))
        role = self.get_object()
        role.remove_user(user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        """Filter user's roles"""
        return self.queryset.filter(user__id=self.kwargs.get('id'))

    def get_serializer_context(self):
        """Add user to context"""
        context = super().get_serializer_context()
        user_id = self.kwargs.get('id')
        if user_id is not None:
            user = User.objects.get(id=user_id)
            context.update({'user': user})
        return context
