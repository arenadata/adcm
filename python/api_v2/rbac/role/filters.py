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

from django.db.models import Q, QuerySet
from django_filters import CharFilter, ChoiceFilter, OrderingFilter
from rbac.models import RoleTypes

from api_v2.filters import AdvancedFilterSet


class RoleFilter(
    AdvancedFilterSet,
    char_fields=("name", "display_name", "type"),
    number_fields=("id",),
):
    name = CharFilter(
        field_name="name",
        label="Filter by name.",
        lookup_expr="exact",
    )
    display_name = CharFilter(
        field_name="display_name",
        label="Case insensitive and partial filter by role display name.",
        lookup_expr="icontains",
    )
    categories = CharFilter(
        label="Filter by a comma-separated list of categories in the role.", method="filter_category"
    )
    type = ChoiceFilter(
        field_name="type",
        choices=[(k, v) for k, v in RoleTypes.choices if k != RoleTypes.HIDDEN],
        label="Filter by type.",
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

    @staticmethod
    def filter_category(queryset: QuerySet, name: str, value: str):  # noqa: ARG001, ARG004
        return queryset.filter(Q(category__value=value) | Q(any_category=True))
