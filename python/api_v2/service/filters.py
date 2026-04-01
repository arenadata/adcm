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

from cm.models import ADCMEntityStatus
from django.db.models import QuerySet
from django_filters.rest_framework import (
    CharFilter,
    ChoiceFilter,
    OrderingFilter,
)

from api_v2.filters import AdvancedFilterSet, filter_service_status


class ServiceFilter(
    AdvancedFilterSet,
    char_fields=(
        ("name", "prototype__name"),
        ("display_name", "prototype__display_name"),
    ),
    number_fields=("id",),
    with_object_status=True,
):
    name = CharFilter(
        label="Case insensitive and partial filter by service name.",
        field_name="prototype__name",
        lookup_expr="icontains",
    )
    display_name = CharFilter(
        label="Case insensitive and partial filter by service display name.",
        field_name="prototype__display_name",
        lookup_expr="icontains",
    )
    status = ChoiceFilter(label="Filter by status.", choices=ADCMEntityStatus.choices, method="filter_status")
    version = CharFilter(label="Filter by version.", field_name="prototype__version")
    state = CharFilter(field_name="state", label="Filter by state.", lookup_expr="exact")

    ordering = OrderingFilter(
        fields={
            "prototype__display_name": "displayName",
            "prototype__version": "version",
            "state": "state",
        },
        field_labels={
            "prototype__display_name": "Display name",
            "prototype__version": "Version",
            "state": "State",
        },
    )

    def filter_status(self, queryset: QuerySet, _: str, value: str) -> QuerySet:
        return filter_service_status(queryset=queryset, value=value, request=self.request)
