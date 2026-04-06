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

from django_filters.rest_framework import (
    CharFilter,
    ChoiceFilter,
    OrderingFilter,
)
from rbac.models import OriginType

from api_v2.filters import AdvancedFilterSet


class GroupFilter(
    AdvancedFilterSet,
    char_fields=("name", "display_name", "type"),
    number_fields=("id",),
):
    name = CharFilter(field_name="name", lookup_expr="exact", label="Filter by name.")
    display_name = CharFilter(
        field_name="display_name",
        lookup_expr="icontains",
        label="Case insensitive and partial filter by group display name.",
    )
    type = ChoiceFilter(field_name="type", choices=OriginType.choices, label="Group type.")
    user_username = CharFilter(
        field_name="user__username",
        label="Filter by user name",
        lookup_expr="exact",
        distinct=True,
    )
    ordering = OrderingFilter(
        fields={
            "name": "name",
            "display_name": "displayName",
            "type": "type",
        },
        field_labels={
            "name": "Name",
            "display_name": "Display name",
            "type": "Type",
        },
    )
