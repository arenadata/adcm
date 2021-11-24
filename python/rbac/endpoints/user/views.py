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
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework import serializers

from rbac import log
from rbac.services import user as user_services
from rbac.viewsets import ModelPermViewSet


class PasswordField(serializers.CharField):
    def to_representation(self, value):
        return user_services.PASSWORD_MASK


class GroupSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='rbac:group-detail', lookup_field='id')

    class Meta:
        model = Group

    def update(self, instance, validated_data):
        ...

    def create(self, validated_data):
        ...


class ExpandedGroupSerializer(GroupSerializer):
    name = serializers.CharField()


class UserSerializer(FlexFieldsSerializerMixin, serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField()
    first_name = serializers.CharField(allow_blank=True, default='')
    last_name = serializers.CharField(allow_blank=True, default='')
    email = serializers.EmailField(allow_blank=True, required=False)
    is_superuser = serializers.BooleanField(default=False)
    password = PasswordField(trim_whitespace=False)
    url = serializers.HyperlinkedIdentityField(view_name='rbac:user-detail')
    profile = serializers.JSONField(source='userprofile.profile', required=False)
    groups = GroupSerializer(many=True, required=False)

    class Meta:
        model = User
        expandable_fields = {'groups': (ExpandedGroupSerializer, {'many': True})}

    def update(self, instance, validated_data):
        log.info(validated_data)
        if 'userprofile' in validated_data:
            validated_data['profile'] = validated_data.pop('userprofile')['profile']
        return user_services.update(instance, partial=self.partial, **validated_data)

    def create(self, validated_data):
        log.info(validated_data)
        if 'userprofile' in validated_data:
            validated_data['profile'] = validated_data.pop('userprofile')['profile']
        return user_services.create(**validated_data)


class UserViewSet(ModelPermViewSet):
    """User view set"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    filterset_fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_superuser']
    ordering_fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_superuser']


# class SelfChangePasswordPerm(DjangoModelPerm):
#     """
#     User self change password permissions class.
#     Use codename self_change_password to check permissions
#     """
#
#     def __init__(self, *args, **kwargs):
#         """Replace PUT permissions from "change" to "self_change_password"""
#         super().__init__(*args, **kwargs)
#         self.perms_map['PUT'] = ['%(app_label)s.self_change_password_%(model_name)s']
#
#     def has_object_permission(self, request, view, obj):
#         """Check that user change his/her own password"""
#         # if request.user != obj:
#         #     return False
#         return True
