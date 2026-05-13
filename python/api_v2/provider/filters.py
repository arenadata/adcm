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

from django_filters.rest_framework import CharFilter, OrderingFilter

from api_v2.filters import AdvancedFilterSet


class ProviderFilter(
    AdvancedFilterSet,
    char_fields=("name",),
    number_fields=("id", ("bundle", "prototype__bundle__id")),
):
    name = CharFilter(
        field_name="name", label="Case insensitive and partial filter by hostprovider name.", lookup_expr="icontains"
    )
    prototype_name = CharFilter(
        field_name="prototype__name",
        label="Filter by prototype name.",
        lookup_expr="exact",
    )
    prototype_display_name = CharFilter(
        field_name="prototype__display_name", label="Filter by prototype display name.", lookup_expr="exact"
    )
    state = CharFilter(label="Filter by state.", field_name="state", lookup_expr="exact")
    prototype_version = CharFilter(
        label="Filter by prototype version.", field_name="prototype__version", lookup_expr="exact"
    )
    ordering = OrderingFilter(
        fields={
            "name": "name",
            "state": "state",
            "prototype__name": "prototypeName",
            "prototype__display_name": "prototypeDisplayName",
            "prototype__version": "prototypeVersion",
        },
        field_labels={
            "name": "Name",
            "state": "State",
            "prototype__name": "Prototype name",
            "prototype__display_name": "Prototype display name",
            "prototype__version": "Prototype version",
        },
        label="ordering",
    )
