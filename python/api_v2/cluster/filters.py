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

from cm.models import ADCMEntityStatus, MaintenanceMode
from django.db.models import QuerySet
from django_filters.rest_framework import (
    CharFilter,
    ChoiceFilter,
    FilterSet,
    NumberFilter,
    OrderingFilter,
)

from api_v2.filters import AdvancedFilterSet, filter_cluster_status, filter_host_status, filter_service_status

MM_CHOICES = ((MaintenanceMode.ON.value,) * 2, (MaintenanceMode.OFF.value,) * 2)


class ClusterFilter(
    AdvancedFilterSet,
    char_fields=("name",),
    number_fields=(("bundle", "prototype__bundle__id"),),
    with_object_status=True,
):
    id = NumberFilter(field_name="id", label="Filter by id.")
    status = ChoiceFilter(label="Filter by status.", choices=ADCMEntityStatus.choices, method="filter_status")
    prototype_name = CharFilter(label="Filter by prototype name.", field_name="prototype__name")
    prototype_display_name = CharFilter(label="Filter by prototype display name.", field_name="prototype__display_name")
    name = CharFilter(label="Case insensitive and partial filter by name.", field_name="name", lookup_expr="icontains")
    state = CharFilter(label="Filter by state.", field_name="state", lookup_expr="exact")
    prototype_version = CharFilter(
        label="Filter by prototype version.",
        field_name="prototype__version",
        lookup_expr="exact",
    )
    ordering = OrderingFilter(
        fields={
            "name": "name",
            "prototype__name": "prototypeName",
            "prototype__display_name": "prototypeDisplayName",
            "prototype__version": "prototypeVersion",
            "state": "state",
        },
        field_labels={
            "name": "Cluster name",
            "prototype__display_name": "Product",
            "prototype__version": "Version",
            "state": "State",
        },
        label="ordering",
    )

    def filter_status(self, queryset: QuerySet, _: str, value: str) -> QuerySet:
        return filter_cluster_status(queryset=queryset, value=value, request=self.request)


class ClusterStatusesHostFilter(FilterSet):
    status = ChoiceFilter(label="Host status", choices=ADCMEntityStatus.choices, method="filter_status")
    maintenance_mode = ChoiceFilter(label="Host maintenance mode", choices=MM_CHOICES, method="filter_mm")
    name = CharFilter(
        label="Case insensitive and partial filter by host name.", field_name="fqdn", lookup_expr="icontains"
    )
    ordering = OrderingFilter(fields={"id": "id"}, field_labels={"id": "Id"}, label="ordering")

    def filter_status(self, queryset: QuerySet, _: str, value: str) -> QuerySet:
        return filter_host_status(queryset=queryset, value=value, request=self.request)

    def filter_mm(self, queryset: QuerySet, _: str, value: str) -> QuerySet:
        return queryset.filter(maintenance_mode=value)


class ClusterStatusesServiceFilter(FilterSet):
    status = ChoiceFilter(label="Service status", choices=ADCMEntityStatus.choices, method="filter_status")
    maintenance_mode = ChoiceFilter(label="Service maintenance mode", choices=MM_CHOICES, method="filter_mm")
    display_name = CharFilter(
        label="Case insensitive and partial filter by service display name.",
        field_name="prototype__display_name",
        lookup_expr="icontains",
    )
    ordering = OrderingFilter(fields={"id": "id"}, field_labels={"id": "Id"}, label="ordering")

    def filter_status(self, queryset: QuerySet, _: str, value: str) -> QuerySet:
        return filter_service_status(queryset=queryset, value=value, request=self.request)

    def filter_mm(self, queryset: QuerySet, _: str, value: str) -> QuerySet:
        return queryset.filter(calculated_mm=value)  # annotated queryset here


class ClusterServiceCandidateAndPrototypeFilter(
    AdvancedFilterSet,
    char_fields=("name", "display_name"),
):
    ...


class ClusterMappingComponentFilter(
    AdvancedFilterSet,
    char_fields=(("name", "prototype__name"), ("display_name", "prototype__display_name")),
    number_fields=("id",),
):
    ...


class ClusterMappingHostFilter(
    AdvancedFilterSet,
    char_fields=(("name", "fqdn"),),
    number_fields=("id",),
):
    ...
