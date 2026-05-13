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

from decimal import Decimal

from django.db.models import QuerySet
from django_filters.rest_framework import CharFilter, ChoiceFilter, NumberFilter, OrderingFilter
from rbac.models import OriginType

from api_v2.filters import AdvancedFilterSet, NumberInFilter
from api_v2.rbac.user.constants import UserStatusChoices


class UserFilterSet(
    AdvancedFilterSet,
    char_fields=("username", "type"),
    number_fields=("id",),
):
    # Advanced filters
    group__eq = NumberFilter(field_name="groups__id", lookup_expr="exact", label="group__eq")
    group__ne = NumberFilter(method="filter_group__ne", label="group__ne")
    group__in = NumberInFilter(field_name="groups__id", lookup_expr="in", distinct=True, label="group__in")
    group__exclude = NumberInFilter(field_name="groups__id", exclude=True, lookup_expr="in", label="group__exclude")
    # ---
    username = CharFilter(
        field_name="username", label="Case insensitive and partial filter by user name.", lookup_expr="icontains"
    )
    # The User model does not have a status field, this is the magic of annotations, see queryset
    status = ChoiceFilter(field_name="status", choices=UserStatusChoices, label="User status.")
    email = CharFilter(field_name="email", label="Filter by email.", lookup_expr="exact")
    type = ChoiceFilter(field_name="type", choices=OriginType.choices, label="User type.")
    group_name = CharFilter(
        field_name="groups__group__name",
        label="Filter by group name.",
        lookup_expr="exact",
        distinct=True,
    )
    group_display_name = CharFilter(
        field_name="groups__group__display_name",
        label="Filter by group display name.",
        lookup_expr="exact",
        distinct=True,
    )
    ordering = OrderingFilter(
        fields={
            "username": "username",
            "status": "status",
            "email": "email",
            "type": "type",
        },
        field_labels={
            "username": "Username",
            "status": "Status",
            "email": "Email",
            "type": "Type",
        },
        label="ordering",
    )

    @staticmethod
    def filter_group__ne(queryset: QuerySet, name: str, value: Decimal) -> QuerySet:
        _ = name
        m2m_model = queryset.model.groups.through
        exclude_user_ids = m2m_model.objects.filter(group_id=value).values_list("user_id", flat=True)
        return queryset.exclude(id__in=exclude_user_ids).distinct()
