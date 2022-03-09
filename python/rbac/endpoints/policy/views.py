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

import jsonschema
from guardian.mixins import PermissionListMixin
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.validators import ValidationError
from rest_framework.viewsets import ModelViewSet

from cm.models import Cluster, ClusterObject, ServiceComponent, HostProvider, Host
from rbac.models import Policy, User, Group, Role, RoleTypes
from rbac.services.policy import policy_create, policy_update
from rbac.utils import BaseRelatedSerializer


class ObjectField(serializers.JSONField):
    def schema_validate(self, value):
        schema = {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'number'},
                    'type': {
                        'type': 'string',
                        'pattern': '^(cluster|service|component|provider|host)$',
                    },
                    'name': {
                        'type': 'string',
                    },
                },
                'additionalProperties': True,
                'required': ['id', 'type'],
            },
        }
        try:
            jsonschema.validate(value, schema)
        except jsonschema.ValidationError:
            raise ValidationError('the field does not match the scheme') from None

    dictionary = {
        'cluster': Cluster,
        'service': ClusterObject,
        'component': ServiceComponent,
        'provider': HostProvider,
        'host': Host,
    }

    def to_internal_value(self, data):
        self.schema_validate(data)
        objects = []
        for obj in data:
            objects.append(self.dictionary[obj['type']].obj.get(id=obj['id']))
        return objects

    def to_representation(self, value):
        data = []
        for obj in value.all():
            data.append(
                {
                    'id': obj.object_id,
                    'type': obj.object.prototype.type,
                    'name': obj.object.display_name,
                }
            )
        return super().to_representation(data)


class PolicyRoleSerializer(BaseRelatedSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())
    url = serializers.HyperlinkedIdentityField(view_name='rbac:role-detail')


class PolicyUserSerializer(BaseRelatedSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    url = serializers.HyperlinkedIdentityField(view_name='rbac:user-detail')


class PolicyGroupSerializer(BaseRelatedSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all())
    url = serializers.HyperlinkedIdentityField(view_name='rbac:group-detail')


class PolicySerializer(FlexFieldsSerializerMixin, serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='rbac:policy-detail')
    name = serializers.RegexField(r'^[^\n]*$', max_length=160)
    object = ObjectField(required=True)
    built_in = serializers.BooleanField(read_only=True)
    role = PolicyRoleSerializer()
    user = PolicyUserSerializer(many=True, required=False)
    group = PolicyGroupSerializer(many=True, required=False)

    class Meta:
        model = Policy
        fields = (
            'id',
            'name',
            'description',
            'object',
            'built_in',
            'role',
            'user',
            'group',
            'url',
        )
        expandable_fields = {
            'user': ('rbac.endpoints.user.views.UserSerializer', {'many': True}),
            'group': ('rbac.endpoints.group.views.GroupSerializer', {'many': True}),
            'role': 'rbac.endpoints.role.views.RoleSerializer',
        }

    def validate_role(self, role):
        if role.type != RoleTypes.role:
            raise serializers.ValidationError(
                f'Role with type "{role.type}" could not be used in policy'
            )
        return role


class PolicyViewSet(PermissionListMixin, ModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer
    permission_classes = (DjangoModelPermissions,)
    permission_required = ['rbac.view_policy']
    filterset_fields = ('id', 'name', 'built_in', 'role', 'user', 'group')
    ordering_fields = ('id', 'name', 'built_in', 'role')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            policy = policy_create(**serializer.validated_data)

            return Response(data=self.get_serializer(policy).data, status=status.HTTP_201_CREATED)
        else:
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        policy = self.get_object()

        if policy.built_in:
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

        serializer = self.get_serializer(policy, data=request.data, partial=partial)
        if serializer.is_valid(raise_exception=True):

            policy = policy_update(policy, **serializer.validated_data)

            return Response(data=self.get_serializer(policy).data)
        else:
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        policy = self.get_object()
        if policy.built_in:
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return super().destroy(request, *args, **kwargs)
