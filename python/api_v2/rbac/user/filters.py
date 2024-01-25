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

from django.db.models import QuerySet
from django_filters.rest_framework import (
    CharFilter,
    ChoiceFilter,
    FilterSet,
    OrderingFilter,
)

from api_v2.rbac.user.constants import UserStatusChoices, UserTypeChoices


class UserFilterSet(FilterSet):
    username = CharFilter(field_name="username", label="username", lookup_expr="icontains")
    status = ChoiceFilter(choices=UserStatusChoices.choices, method="filter_status", label="status")
    type = ChoiceFilter(choices=UserTypeChoices.choices, method="filter_type", label="type")
    ordering = OrderingFilter(fields={"username": "username"}, field_labels={"username": "username"}, label="ordering")

    @staticmethod
    def filter_status(queryset: QuerySet, name: str, value: str) -> QuerySet:  # noqa: ARG001, ARG004
        filter_value = False

        if value == UserStatusChoices.ACTIVE:
            filter_value = True

        return queryset.filter(blocked_at__isnull=filter_value)

    @staticmethod
    def filter_type(queryset: QuerySet, name: str, value: str) -> QuerySet:  # noqa: ARG001, ARG004
        filter_value = UserTypeChoices.LOCAL.value

        if value == UserTypeChoices.LDAP:
            filter_value = UserTypeChoices.LDAP.value

        return queryset.filter(type=filter_value)
