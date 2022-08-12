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
from audit.utils import audit
from cm.models import Cluster, ClusterObject, Host, HostProvider, ServiceComponent
from guardian.mixins import PermissionListMixin
from rbac.models import Group, Policy, Role, RoleTypes, User
from rbac.services.policy import policy_create, policy_update
from rbac.utils import BaseRelatedSerializer
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework.exceptions import ValidationError

# from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.serializers import (
    BooleanField,
    HyperlinkedIdentityField,
    JSONField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    RegexField,
)
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_405_METHOD_NOT_ALLOWED,
)
from rest_framework.viewsets import ModelViewSet

from adcm.permissions import DjangoModelPermissionsAudit


class ObjectField(JSONField):
    @staticmethod
    def schema_validate(value):
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
        except jsonschema.ValidationError as e:
            raise ValidationError('the field does not match the scheme') from e

        return value

    def to_internal_value(self, data):
        self.schema_validate(data)
        dictionary = {
            'cluster': Cluster,
            'service': ClusterObject,
            'component': ServiceComponent,
            'provider': HostProvider,
            'host': Host,
        }

        objects = []
        for obj in data:
            objects.append(dictionary[obj['type']].obj.get(id=obj['id']))

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
    id = PrimaryKeyRelatedField(queryset=Role.objects.all())
    url = HyperlinkedIdentityField(view_name='rbac:role-detail')


class PolicyUserSerializer(BaseRelatedSerializer):
    id = PrimaryKeyRelatedField(queryset=User.objects.all())
    url = HyperlinkedIdentityField(view_name='rbac:user-detail')


class PolicyGroupSerializer(BaseRelatedSerializer):
    id = PrimaryKeyRelatedField(queryset=Group.objects.all())
    url = HyperlinkedIdentityField(view_name='rbac:group-detail')


class PolicySerializer(FlexFieldsSerializerMixin, ModelSerializer):
    url = HyperlinkedIdentityField(view_name='rbac:policy-detail')
    name = RegexField(r'^[^\n]*$', max_length=160)
    object = ObjectField(required=True)
    built_in = BooleanField(read_only=True)
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

    @staticmethod
    def validate_role(role):
        if role.type != RoleTypes.role:
            raise ValidationError(f'Role with type "{role.type}" could not be used in policy')
        return role


class PolicyViewSet(PermissionListMixin, ModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer
    permission_classes = (DjangoModelPermissionsAudit,)
    permission_required = ['rbac.view_policy']
    filterset_fields = ('id', 'name', 'built_in', 'role', 'user', 'group')
    ordering_fields = ('id', 'name', 'built_in', 'role')

    @audit
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            policy = policy_create(**serializer.validated_data)

            return Response(data=self.get_serializer(policy).data, status=HTTP_201_CREATED)
        else:
            return Response(data=serializer.errors, status=HTTP_400_BAD_REQUEST)

    @audit
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        policy = self.get_object()

        if policy.built_in:
            return Response(status=HTTP_405_METHOD_NOT_ALLOWED)

        serializer = self.get_serializer(policy, data=request.data, partial=partial)
        if serializer.is_valid(raise_exception=True):

            policy = policy_update(policy, **serializer.validated_data)

            return Response(data=self.get_serializer(policy).data)
        else:
            return Response(data=serializer.errors, status=HTTP_400_BAD_REQUEST)

    @audit
    def destroy(self, request, *args, **kwargs):
        policy = self.get_object()
        if policy.built_in:
            return Response(status=HTTP_405_METHOD_NOT_ALLOWED)
        return super().destroy(request, *args, **kwargs)
