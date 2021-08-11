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


from rest_framework.viewsets import ModelViewSet

from cm.models import GroupConfig
from .serializers import GroupConfigSerializer, revert_model_name
from django_filters.rest_framework import FilterSet, CharFilter
from django.contrib.contenttypes.models import ContentType


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


class GroupConfigViewSet(ModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = GroupConfig.objects.all()
    serializer_class = GroupConfigSerializer
    filterset_class = GroupConfigFilterSet
