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

from cm.models import GroupConfig, Host
from .serializers import (
    GroupConfigSerializer,
    revert_model_name,
    GroupConfigHostSerializer,
    GroupConfigHostCandidateSerializer,
)


class GroupConfigFilterSet(FilterSet):
    object_type = CharFilter(
        field_name='object_type', label='object_type', method='filter_object_type'
    )

    def filter_object_type(self, queryset, name, value):
        value = revert_model_name(value)
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
    serializer_class = GroupConfigHostSerializer
    lookup_url_kwarg = 'host_id'

    def destroy(self, request, *args, **kwargs):
        group_config = GroupConfig.obj.get(id=self.kwargs.get('parent_lookup_groupconfig'))
        host = self.get_object()
        group_config.hosts.remove(host)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        group_config_id = self.kwargs.get('parent_lookup_groupconfig')
        if group_config_id is not None:
            group_config = GroupConfig.obj.get(id=group_config_id)
            context.update({'groupconfig': group_config})
        return context


class GroupConfigHostCandidateViewSet(NestedViewSetMixin, ListModelMixin, viewsets.GenericViewSet):
    queryset = Host.objects.all()
    serializer_class = GroupConfigHostCandidateSerializer
    lookup_url_kwarg = 'host_id'

    def list(self, request, *args, **kwargs):
        group_config = GroupConfig.obj.get(id=self.kwargs.get('parent_lookup_groupconfig'))
        page = self.paginate_queryset(group_config.host_candidate())
        serializer = self.serializer_class(
            page, many=True, context={'request': request, 'groupconfig': group_config}
        )
        return self.get_paginated_response(serializer.data)


class GroupConfigViewSet(
    NestedViewSetMixin, viewsets.ModelViewSet
):  # pylint: disable=too-many-ancestors
    queryset = GroupConfig.objects.all()
    serializer_class = GroupConfigSerializer
    filterset_class = GroupConfigFilterSet
