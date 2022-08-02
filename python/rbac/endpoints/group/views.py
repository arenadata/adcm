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

from adwp_base.errors import AdwpEx
from audit.utils import audit
from django_filters.rest_framework import CharFilter, DjangoFilterBackend, FilterSet
from guardian.mixins import PermissionListMixin
from rbac import models
from rbac.services import group as group_services
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.serializers import (
    BooleanField,
    CharField,
    HyperlinkedIdentityField,
    IntegerField,
    ModelSerializer,
    RegexField,
    Serializer,
)
from rest_framework.status import HTTP_405_METHOD_NOT_ALLOWED
from rest_framework.viewsets import ModelViewSet

from adcm.serializers import EmptySerializer


class UserSerializer(EmptySerializer):
    """Simple User serializer"""

    id = IntegerField()
    url = HyperlinkedIdentityField(view_name='rbac:user-detail')


class UserGroupSerializer(EmptySerializer):
    """Simple Group serializer"""

    id = IntegerField()
    url = HyperlinkedIdentityField(view_name='rbac:group-detail')


class ExpandedUserSerializer(FlexFieldsSerializerMixin, ModelSerializer):
    """Expanded User serializer"""

    group = UserGroupSerializer(many=True, source='groups')
    url = HyperlinkedIdentityField(view_name='rbac:user-detail')

    class Meta:
        model = models.User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'is_superuser',
            'group',
            'url',
        )
        expandable_fields = {
            'group': (
                'rbac.endpoints.group.views.GroupSerializer',
                {'many': True, 'source': 'groups'},
            )
        }


class GroupSerializer(FlexFieldsSerializerMixin, Serializer):
    """
    Group serializer
    Group model inherits 'user_set' property from parent class, which refers to 'auth.User',
    so it has not our custom properties in expanded fields
    """

    id = IntegerField(read_only=True)
    name = RegexField(r'^[^\n]+$', max_length=150, source='name_to_display')
    description = CharField(max_length=255, allow_blank=True, required=False, default='')
    user = UserSerializer(many=True, required=False, source='user_set')
    url = HyperlinkedIdentityField(view_name='rbac:group-detail')
    built_in = BooleanField(read_only=True)
    type = CharField(read_only=True)

    class Meta:
        expandable_fields = {'user': (ExpandedUserSerializer, {'many': True, 'source': 'user_set'})}

    def update(self, instance, validated_data):
        return group_services.update(instance, partial=self.partial, **validated_data)

    def create(self, validated_data):
        return group_services.create(**validated_data)


class GroupFilterSet(FilterSet):
    name = CharFilter(field_name='display_name', label='name')

    class Meta:
        model = models.Group
        fields = ('id', 'type')


class GroupOrderingFilter(OrderingFilter):
    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)

        if not ordering:
            return queryset

        fix_ordering = []

        for field in ordering:
            if field == '-name':
                fix_ordering.append('-display_name')
                continue
            if field == 'name':
                fix_ordering.append('display_name')
                continue
            fix_ordering.append(field)
        return queryset.order_by(*fix_ordering)


class GroupViewSet(PermissionListMixin, ModelViewSet):  # pylint: disable=too-many-ancestors
    """Group view set"""

    queryset = models.Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = (DjangoModelPermissions,)
    permission_required = ['rbac.view_group']
    filter_backends = (DjangoFilterBackend, GroupOrderingFilter)
    filterset_class = GroupFilterSet
    ordering_fields = ('id', 'name')
    search_fields = ('name', 'description', 'display_name')

    @audit
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @audit
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.built_in:
            raise AdwpEx(
                'GROUP_DELETE_ERROR',
                msg='Built-in group could not be deleted',
                http_code=HTTP_405_METHOD_NOT_ALLOWED,
            )
        return super().destroy(request, args, kwargs)
