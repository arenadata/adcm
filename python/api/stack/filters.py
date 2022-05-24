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


from django_filters import rest_framework as drf_filters
from cm.models import Prototype


class StringInFilter(drf_filters.BaseInFilter, drf_filters.CharFilter):
    pass


class PrototypeListFilter(drf_filters.FilterSet):
    bundle_id = drf_filters.NumberFilter(
        label='bundle_id', field_name='bundle__pk', lookup_expr='exact'
    )
    type = drf_filters.CharFilter(label='type', field_name='type', lookup_expr='exact')
    name = StringInFilter(label='name', field_name='name', lookup_expr='in')
    parent_name = StringInFilter(label='parent_name', field_name='parent', lookup_expr='name__in')
    ordering = drf_filters.OrderingFilter(
        fields=(
            ('display_name', 'display_name'),
            ('version_order', 'version_order'),
        )
    )

    class Meta:
        model = Prototype
        fields = []
