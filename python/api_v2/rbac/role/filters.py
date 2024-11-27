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
from django_filters import BooleanFilter, CharFilter, ChoiceFilter, OrderingFilter
from django_filters.rest_framework import FilterSet
from rbac.models import Role, RoleTypes


class RoleFilter(FilterSet):
    display_name = CharFilter(field_name="display_name", label="Role name", lookup_expr="icontains")
    description = CharFilter(field_name="description", label="Description", lookup_expr="icontains")
    built_in = BooleanFilter(field_name="built_in", label="Built in")
    any_category = BooleanFilter(field_name="any_category", label="Any category")
    categories = CharFilter(label="Categories", method="filter_category")
    type = ChoiceFilter(choices=[(k, v) for k, v in RoleTypes.choices if k != RoleTypes.HIDDEN])
    ordering = OrderingFilter(
        fields={
            "display_name": "displayName",
            "id": "id",
            "type": "type",
            "description": "description",
            "built_in": "builtIn",
            "any_category": "anyCategory",
        },
        field_labels={
            "display_name": "Display name",
            "id": "ID",
            "type": "Type",
            "description": "Description",
            "built_in": "Built in",
            "any_category": "Any category",
        },
    )

    @staticmethod
    def filter_category(queryset: QuerySet, name: str, value: str):  # noqa: ARG001, ARG004
        return queryset.filter(Q(category__value=value) | Q(any_category=True))

    class Meta:
        model = Role
        fields = ["id", "type", "description", "display_name", "built_in", "any_category", "ordering"]
