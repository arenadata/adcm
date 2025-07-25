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

from cm.models import Component
from django_filters.rest_framework import CharFilter, OrderingFilter

from api_v2.filters import AdvancedFilterSet


class ComponentFilter(
    AdvancedFilterSet,
    char_fields=(("name", "prototype__name"), ("display_name", "prototype__display_name")),
    number_fields=("id",),
    with_object_status=True,
):
    name = CharFilter(
        field_name="prototype__name", label="Case insensitive and partial filter by name.", lookup_expr="icontains"
    )
    display_name = CharFilter(
        field_name="prototype__display_name",
        label="Case insensitive and partial filter by display name.",
        lookup_expr="icontains",
    )
    ordering = OrderingFilter(
        fields={"prototype__name": "name", "prototype__display_name": "displayName"},
        field_labels={
            "prototype__name": "Name",
            "prototype__display_name": "Display Name",
        },
        label="ordering",
    )

    class Meta:
        model = Component
        fields = ["id"]
