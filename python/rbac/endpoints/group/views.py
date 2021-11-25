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

"""Group view sets"""

from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework import serializers

from rbac import models, log
from rbac.services import group as group_services
from rbac.viewsets import ModelPermViewSet


class UserSerializer(serializers.Serializer):
    """Simple User serializer"""

    id = serializers.IntegerField()
    url = serializers.HyperlinkedIdentityField(view_name='rbac:user-detail', lookup_field='pk')

    class Meta:
        model = models.User


class ExpandedUserSerializer(UserSerializer):
    """Expanded User serializer"""

    username = serializers.CharField()
    first_name = serializers.CharField(allow_blank=True, default='')
    last_name = serializers.CharField(allow_blank=True, default='')
    email = serializers.EmailField(allow_blank=True, required=False)
    is_superuser = serializers.BooleanField(default=False)


class GroupSerializer(FlexFieldsSerializerMixin, serializers.Serializer):
    """Group serializer"""

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True, default='')
    user = UserSerializer(source='user_set', many=True, required=False)
    url = serializers.HyperlinkedIdentityField(view_name='rbac:group-detail')

    class Meta:
        model = models.Group
        expandable_fields = {'user': (ExpandedUserSerializer, {'many': True, 'source': 'user_set'})}

    def update(self, instance, validated_data):
        log.debug(validated_data)
        if 'user_set' in validated_data:
            validated_data['user'] = validated_data.pop('user_set')
        log.debug(validated_data)
        return group_services.update(instance, partial=self.partial, **validated_data)

    def create(self, validated_data):
        log.debug(validated_data)
        if 'user_set' in validated_data:
            validated_data['user'] = validated_data.pop('user_set')
        return group_services.create(**validated_data)


class GroupViewSet(ModelPermViewSet):  # pylint: disable=too-many-ancestors
    """Group view set"""

    queryset = models.Group.objects.all()
    serializer_class = GroupSerializer
    filterset_fields = ['id', 'name']
    ordering_fields = ['id', 'name']
