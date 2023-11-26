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

from cm.models import ServiceComponent
from django_filters.rest_framework import CharFilter, FilterSet, OrderingFilter


class ComponentFilter(FilterSet):
    name = CharFilter(field_name="prototype__name", label="Name", lookup_expr="icontains")
    display_name = CharFilter(field_name="prototype__display_name", label="Display Name", lookup_expr="icontains")
    ordering = OrderingFilter(
        fields={"prototype__name": "name", "prototype__display_name": "displayName"},
        field_labels={"prototype__name": "Name", "prototype__display_name": "Display Name"},
        label="ordering",
    )

    class Meta:
        model = ServiceComponent
        fields = ["id"]
