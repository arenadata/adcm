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

"""ViewSet and Serializers for Role"""

from django.contrib.auth.models import Group
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework import serializers, status
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.mixins import (
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
)

from rbac.models import Role
from rbac.viewsets import ModelPermViewSet, GenericPermViewSet
from .user.serializers import PermissionSerializer


class GroupRoleSerializer(serializers.ModelSerializer):
    """Serializer for group's roles"""

    id = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())
    url = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = (
            'id',
            'name',
            'url',
        )
        read_only_fields = ('name',)

    def get_url(self, obj):
        """get role URL rbac/group/1/role/1/"""
        kwargs = {'id': self.context['group'].id, 'role_id': obj.id}
        return reverse('rbac:group-role-detail', kwargs=kwargs, request=self.context['request'])

    def create(self, validated_data):
        """Add role to group"""
        group = self.context.get('group')
        role = validated_data['id']
        role.add_group(group)
        return role


class GroupSerializer(FlexFieldsSerializerMixin, serializers.HyperlinkedModelSerializer):
    """Group serializer"""

    permissions = PermissionSerializer(many=True, read_only=True)
    add_role = serializers.HyperlinkedIdentityField(
        view_name='rbac:group-role-list', lookup_field='id'
    )

    class Meta:
        model = Group
        fields = (
            'id',
            'name',
            'permissions',
            'add_role',
            'url',
        )
        extra_kwargs = {
            'url': {'view_name': 'rbac:group-detail', 'lookup_field': 'id'},
        }


# pylint: disable=too-many-ancestors
class GroupViewSet(ModelPermViewSet):
    """Group View Set"""

    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    lookup_field = 'id'
    filterset_fields = ['id', 'name']
    ordering_fields = ['id', 'name']

    def get_serializer_context(self):
        """Add group to context"""
        context = super().get_serializer_context()
        group_id = self.kwargs.get('id')
        if group_id is not None:
            group = Group.objects.get(id=group_id)
            context.update({'group': group})
        return context


# pylint: disable=too-many-ancestors
class GroupRoleViewSet(
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    GenericPermViewSet,
):
    """Group role view set"""

    queryset = Role.objects.all()
    serializer_class = GroupRoleSerializer
    lookup_url_kwarg = 'role_id'

    def destroy(self, request, *args, **kwargs):
        """Remove role from group"""
        group = Group.objects.get(id=self.kwargs.get('id'))
        role = self.get_object()
        role.remove_group(group)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # def get_queryset(self):
    #     """Filter user's roles"""
    #     return self.queryset.filter(group__id=self.kwargs.get('id'))

    def get_serializer_context(self):
        """Add group to context"""
        context = super().get_serializer_context()
        group_id = self.kwargs.get('id')
        if group_id is not None:
            group = Group.objects.get(id=group_id)
            context.update({'group': group})
        return context
