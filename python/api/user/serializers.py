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

from django.db import IntegrityError, transaction
from django.contrib.auth.models import User, Group
from rest_framework import serializers
from rest_framework.authtoken.models import Token

import cm
from cm.errors import AdcmEx
from cm.models import UserProfile, Role
from api.api_views import check_obj, hlink
from api.serializers import UrlField


class PermSerializer(serializers.Serializer):
    name = serializers.CharField()
    codename = serializers.CharField()
    app_label = serializers.SerializerMethodField()
    model = serializers.SerializerMethodField()

    def get_app_label(self, obj):
        return obj.content_type.app_label

    def get_model(self, obj):
        return obj.content_type.model


class RoleSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    url = hlink('role-details', 'id', 'role_id')


class RoleDetailSerializer(RoleSerializer):
    permissions = PermSerializer(many=True, read_only=True)


class GroupSerializer(serializers.Serializer):
    name = serializers.CharField()
    url = hlink('group-details', 'name', 'name')
    change_role = hlink('change-group-role', 'name', 'name')

    @transaction.atomic
    def create(self, validated_data):
        try:
            return Group.objects.create(name=validated_data.get('name'))
        except IntegrityError:
            raise AdcmEx("GROUP_CONFLICT", 'group already exists') from None


class GroupDetailSerializer(GroupSerializer):
    permissions = PermSerializer(many=True, read_only=True)
    role = RoleSerializer(many=True, source='role_set')


class UserSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    url = hlink('user-details', 'username', 'username')
    change_group = hlink('add-user-group', 'username', 'username')
    change_password = hlink('user-passwd', 'username', 'username')
    change_role = hlink('change-user-role', 'username', 'username')
    is_superuser = serializers.BooleanField(required=False)

    @transaction.atomic
    def create(self, validated_data):
        try:
            user = User.objects.create_user(
                validated_data.get('username'),
                password=validated_data.get('password'),
                is_superuser=validated_data.get('is_superuser', True),
            )
            UserProfile.objects.create(login=validated_data.get('username'))
            return user
        except IntegrityError:
            raise AdcmEx("USER_CONFLICT", 'user already exists') from None


class UserDetailSerializer(UserSerializer):
    user_permissions = PermSerializer(many=True)
    groups = GroupSerializer(many=True)
    role = RoleSerializer(many=True, source='role_set')


class AddUser2GroupSerializer(serializers.Serializer):
    name = serializers.CharField()

    def update(self, user, validated_data):  # pylint: disable=arguments-differ
        group = check_obj(Group, {'name': validated_data.get('name')}, 'GROUP_NOT_FOUND')
        group.user_set.add(user)
        return group


class AddUserRoleSerializer(serializers.Serializer):
    role_id = serializers.IntegerField()
    name = serializers.CharField(read_only=True)

    def update(self, user, validated_data):  # pylint: disable=arguments-differ
        role = check_obj(Role, {'id': validated_data.get('role_id')}, 'ROLE_NOT_FOUND')
        return cm.api.add_user_role(user, role)


class AddGroupRoleSerializer(serializers.Serializer):
    role_id = serializers.IntegerField()
    name = serializers.CharField(read_only=True)

    def update(self, group, validated_data):  # pylint: disable=arguments-differ
        role = check_obj(Role, {'id': validated_data.get('role_id')}, 'ROLE_NOT_FOUND')
        return cm.api.add_group_role(group, role)


class UserPasswdSerializer(serializers.Serializer):
    token = serializers.CharField(read_only=True, source='key')
    password = serializers.CharField(write_only=True)

    @transaction.atomic
    def update(self, user, validated_data):  # pylint: disable=arguments-differ
        user.set_password(validated_data.get('password'))
        user.save()
        token = Token.obj.get(user=user)
        token.delete()
        token.key = token.generate_key()
        token.user = user
        token.save()
        return token


class ProfileDetailSerializer(serializers.Serializer):
    class MyUrlField(UrlField):
        def get_kwargs(self, obj):
            return {'username': obj.login}

    username = serializers.CharField(read_only=True, source='login')
    change_password = MyUrlField(read_only=True, view_name='profile-passwd')
    profile = serializers.JSONField()

    def validate_profile(self, raw):
        if isinstance(raw, str):
            raise AdcmEx('JSON_ERROR', 'profile should not be just one string')
        return raw

    def update(self, instance, validated_data):
        instance.profile = validated_data.get('profile', instance.profile)
        try:
            instance.save()
        except IntegrityError:
            raise AdcmEx("USER_CONFLICT") from None
        return instance


class ProfileSerializer(ProfileDetailSerializer):
    username = serializers.CharField(source='login')
    url = hlink('profile-details', 'login', 'username')

    def create(self, validated_data):
        check_obj(User, {'username': validated_data.get('login')}, 'USER_NOT_FOUND')
        try:
            return UserProfile.objects.create(**validated_data)
        except IntegrityError:
            raise AdcmEx("USER_CONFLICT") from None
