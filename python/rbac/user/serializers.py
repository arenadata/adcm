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

from django.db import models
from django.db.transaction import atomic
from django.contrib.auth.models import User, Group

from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.utils import model_meta


class PasswordField(serializers.CharField):
    """Password serializer field"""

    def to_representation(self, value):
        return '******'


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = (
            'id',
            'name',
        )


class UserSerializer(FlexFieldsSerializerMixin, serializers.HyperlinkedModelSerializer):
    """User serializer"""

    password = PasswordField()
    groups = serializers.SerializerMethodField()
    add_group = serializers.HyperlinkedIdentityField(
        view_name='rbac-user-group-list', lookup_field= 'id'
    )

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'password',
            'first_name',
            'last_name',
            'email',
            'is_superuser',
            'groups',
            'url',
            'add_group'
        )
        extra_kwargs = {
            #'url': {'view_name': 'rbac_user:user-detail', 'lookup_field': 'id'},
            'url': {'view_name': 'rbac-user-detail', 'lookup_field': 'id'},
            'is_superuser': {'required': False},
            'profile': {'required': False},
        }

    def get_groups(self, obj):
        groups = obj.groups.all()
        return GroupSerializer(groups, many=True, context=self.context).data

    def create(self, validated_data):
        extra_fields = {}

        def set_extra(name):
            if name in validated_data:
                extra_fields[name] = validated_data[name]

        for name in ('first_name', 'last_name', 'profile'):
            set_extra(name)

        return User.objects.create_user(
            validated_data.get('username'),
            password=validated_data.get('password'),
            is_superuser=validated_data.get('is_superuser', True),
            email=validated_data.get('email', None),
            **extra_fields,
        )

    @atomic
    def update(self, instance, validated_data):
        """Update user, use in PUT and PATCH methods"""
        if 'password' in validated_data:
            password = validated_data.pop('password')
            instance.set_password(password)
            instance.save()
            token, _ = Token.objects.get_or_create(user=instance)
            token.delete()
            token.key = token.generate_key()
            token.user = instance
            token.save()

        return super().update(instance, validated_data)

    def get_fields(self):
        """Get fields for serialization, remove `huge` fields"""
        fields = super().get_fields()
        action = getattr(self.context.get('view'), 'action', '')
        if action == 'list':
            model_field_info = model_meta.get_field_info(User)
            for name, field in model_field_info.fields.items():
                if name in fields:
                    if isinstance(field, (models.JSONField, models.TextField)):
                        del fields[name]
        return fields


class UserGroupSerializer(serializers.ModelSerializer):
    """Serializer for user's groups"""

    id = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all())

    class Meta:
        model = Group
        fields = (
            'id',
            'name',
            #'url',
        )
        read_only_fields = ('name',)

    def create(self, validated_data):
        user = self.context.get('user')
        group = validated_data['id']
        user.groups.add(group)
        return group
