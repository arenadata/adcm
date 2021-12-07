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

from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response

from rbac.models import Role
from rbac.services.role import role_create, role_update
from rbac.utils import BaseRelatedSerializer


class RoleChildSerializer(BaseRelatedSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())
    url = serializers.HyperlinkedIdentityField(view_name='rbac:role-detail')


class RoleSerializer(FlexFieldsSerializerMixin, serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='rbac:role-detail')
    child = RoleChildSerializer(many=True, required=False)

    class Meta:
        model = Role
        fields = (
            'id',
            'name',
            'description',
            'display_name',
            'built_in',
            'type',
            'category',
            'parametrized_by_type',
            'child',
            'url',
        )
        extra_kwargs = {
            'parametrized_by_type': {'required': True},
            'built_in': {'read_only': True},
            'type': {'read_only': True},
        }
        expandable_fields = {'child': ('rbac.endpoints.role.views.RoleSerializer', {'many': True})}


class RoleView(viewsets.ModelViewSet):  # pylint: disable=too-many-ancestors

    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    filterset_fields = (
        'id',
        'name',
        'display_name',
        'built_in',
        'type',
        'child',
    )
    ordering_fields = ('id', 'name', 'display_name', 'built_in', 'type')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):

            role = role_create(**serializer.validated_data)

            return Response(self.get_serializer(role).data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        if instance.built_in:
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

        serializer = self.get_serializer(data=request.data, partial=partial)

        if serializer.is_valid(raise_exception=True):

            role = role_update(instance, **serializer.validated_data)

            return Response(self.get_serializer(role).data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.built_in:
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return super().destroy(request, *args, **kwargs)
