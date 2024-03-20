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

from cm.models import ADCMEntityStatus, ClusterObject, ObjectType
from django.db.models import QuerySet
from django_filters.rest_framework import (
    CharFilter,
    ChoiceFilter,
    FilterSet,
    OrderingFilter,
)

from api_v2.filters import filter_service_status


class ServiceFilter(FilterSet):
    name = CharFilter(label="Service name", method="filter_name")
    display_name = CharFilter(label="Display name", field_name="prototype__display_name", lookup_expr="icontains")
    status = ChoiceFilter(label="Service status", choices=ADCMEntityStatus.choices, method="filter_status")
    ordering = OrderingFilter(
        fields={"prototype__display_name": "displayName"},
        field_labels={"prototype__display_name": "Display name"},
    )

    class Meta:
        model = ClusterObject
        fields = ["name", "display_name", "status"]

    @staticmethod
    def filter_status(queryset: QuerySet, _: str, value: str) -> QuerySet:
        return filter_service_status(queryset=queryset, value=value)

    @staticmethod
    def filter_name(queryset: QuerySet, name: str, value: str) -> QuerySet:  # noqa: ARG001, ARG004
        return queryset.filter(prototype__type=ObjectType.SERVICE, prototype__name__icontains=value)
