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


from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import FilterSet, CharFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework import viewsets
from rest_framework.mixins import (
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
)
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from api.views import ViewInterfaceGenericViewSet
from cm.models import GroupConfig, Host, ObjectConfig, ConfigLog
from . import serializers


def has_config_perm(user, action_type, obj):
    model = type(obj).__name__.lower()
    if user.has_perm(f'cm.{action_type}_configlog'):
        return True
    if user.has_perm(f'cm.{action_type}_config_of_{model}', obj):
        return True
    return False


def check_config_perm(self, action_type, obj):
    if not has_config_perm(self.request.user, action_type, obj):
        self.permission_denied(
            self.request,
            message='You do not have permission to perform this action',
            code=status.HTTP_403_FORBIDDEN,
        )


class GroupConfigFilterSet(FilterSet):
    object_type = CharFilter(
        field_name='object_type', label='object_type', method='filter_object_type'
    )

    def filter_object_type(self, queryset, name, value):
        value = serializers.revert_model_name(value)
        object_type = ContentType.objects.get(app_label='cm', model=value)
        return queryset.filter(**{name: object_type})

    class Meta:
        model = GroupConfig
        fields = ('object_id', 'object_type')


class GroupConfigHostViewSet(
    NestedViewSetMixin,
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    viewsets.GenericViewSet,
):  # pylint: disable=too-many-ancestors
    queryset = Host.objects.all()
    serializer_class = serializers.GroupConfigHostSerializer
    permission_classes = (IsAuthenticated,)
    check_config_perm = check_config_perm
    lookup_url_kwarg = 'host_id'

    def destroy(self, request, *args, **kwargs):
        group_config = GroupConfig.obj.get(id=self.kwargs.get('parent_lookup_group_config'))
        self.check_config_perm('change', group_config.object)
        host = self.get_object()
        group_config.hosts.remove(host)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        group_config_id = self.kwargs.get('parent_lookup_group_config')
        if group_config_id is not None:
            group_config = GroupConfig.obj.get(id=group_config_id)
            self.check_config_perm('view', group_config.object)
            context.update({'group_config': group_config})
        return context


class GroupConfigHostCandidateViewSet(
    NestedViewSetMixin, viewsets.ReadOnlyModelViewSet
):  # pylint: disable=too-many-ancestors
    serializer_class = serializers.GroupConfigHostCandidateSerializer
    permission_classes = (IsAuthenticated,)
    check_config_perm = check_config_perm
    lookup_url_kwarg = 'host_id'

    def get_queryset(self):
        group_config_id = self.kwargs.get('parent_lookup_group_config')
        if group_config_id is None:
            return None
        group_config = GroupConfig.obj.get(id=group_config_id)
        return group_config.host_candidate()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        group_config_id = self.kwargs.get('parent_lookup_group_config')
        if group_config_id is not None:
            group_config = GroupConfig.obj.get(id=group_config_id)
            self.check_config_perm('view', group_config.object)
            context.update({'group_config': group_config})
        return context


class GroupConfigConfigViewSet(NestedViewSetMixin, RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = ObjectConfig.objects.all()
    serializer_class = serializers.GroupConfigConfigSerializer
    permission_classes = (IsAuthenticated,)
    check_config_perm = check_config_perm

    def get_serializer_context(self):
        context = super().get_serializer_context()
        group_config_id = self.kwargs.get('parent_lookup_group_config')
        if group_config_id is not None:
            group_config = GroupConfig.obj.get(id=group_config_id)
            self.check_config_perm('view', group_config.object)
            context.update({'group_config': group_config})
            context.update({'obj_ref__group_config': group_config})
        obj_ref_id = self.kwargs.get('pk')
        if obj_ref_id is not None:
            obj_ref = ObjectConfig.obj.get(id=obj_ref_id)
            context.update({'obj_ref': obj_ref})
        return context


class GroupConfigConfigLogViewSet(
    NestedViewSetMixin,
    RetrieveModelMixin,
    ListModelMixin,
    CreateModelMixin,
    ViewInterfaceGenericViewSet,
):  # pylint: disable=too-many-ancestors
    serializer_class = serializers.GroupConfigConfigLogSerializer
    ui_serializer_class = serializers.UIGroupConfigConfigLogSerializer
    permission_classes = (IsAuthenticated,)
    check_config_perm = check_config_perm
    filterset_fields = ('id',)
    ordering_fields = ('id',)

    def get_queryset(self):
        kwargs = {
            'obj_ref__group_config': self.kwargs.get('parent_lookup_obj_ref__group_config'),
            'obj_ref': self.kwargs.get('parent_lookup_obj_ref'),
        }
        return ConfigLog.objects.filter(**kwargs).order_by('-id')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        group_config_id = self.kwargs.get('parent_lookup_obj_ref__group_config')
        if group_config_id is not None:
            group_config = GroupConfig.obj.get(id=group_config_id)
            self.check_config_perm('view', group_config.object)
            context.update({'obj_ref__group_config': group_config})
        obj_ref_id = self.kwargs.get('parent_lookup_obj_ref')
        if obj_ref_id is not None:
            obj_ref = ObjectConfig.obj.get(id=obj_ref_id)
            context.update({'obj_ref': obj_ref})
        return context


class GroupConfigViewSet(
    NestedViewSetMixin, viewsets.ModelViewSet
):  # pylint: disable=too-many-ancestors
    queryset = GroupConfig.objects.all()
    serializer_class = serializers.GroupConfigSerializer
    filterset_class = GroupConfigFilterSet
    permission_classes = (IsAuthenticated,)
    check_config_perm = check_config_perm

    def perform_create(self, serializer):
        model = serializer.validated_data['object_type'].model_class()
        obj = model.obj.get(id=serializer.validated_data['object_id'])
        self.check_config_perm('change', obj)
        serializer.save()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.kwargs:
            group_config = self.get_object()
            self.check_config_perm('view', group_config.object)
            context.update({'group_config': group_config})
        return context
