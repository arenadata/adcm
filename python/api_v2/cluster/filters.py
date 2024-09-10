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

from cm.models import ADCMEntityStatus, Cluster
from cm.services.status.client import retrieve_status_map
from django.db.models import QuerySet
from django_filters.rest_framework import (
    CharFilter,
    ChoiceFilter,
    FilterSet,
    OrderingFilter,
)

from api_v2.filters import filter_service_status


class ClusterFilter(FilterSet):
    status = ChoiceFilter(label="Cluster status", choices=ADCMEntityStatus.choices, method="filter_status")
    prototype_name = CharFilter(label="Cluster prototype name", field_name="prototype__name", lookup_expr="icontains")
    prototype_display_name = CharFilter(
        label="Cluster prototype display name", field_name="prototype__display_name", lookup_expr="icontains"
    )
    name = CharFilter(label="Cluster name", lookup_expr="icontains")
    description = CharFilter(label="Cluster description", lookup_expr="icontains")
    state = CharFilter(label="Cluster state", lookup_expr="icontains")
    ordering = OrderingFilter(
        fields={
            "name": "name",
            "prototype__display_name": "prototypeDisplayName",
            "state": "state",
            "description": "description",
        },
        field_labels={
            "name": "Cluster name",
            "prototype__display_name": "Product",
            "state": "State",
            "description": "Description",
        },
        label="ordering",
    )

    class Meta:
        model = Cluster
        fields = ("id", "name", "status", "prototype_name", "prototype_display_name", "state", "description")

    @staticmethod
    def filter_status(queryset: QuerySet, _: str, value: str) -> QuerySet:
        status_map = retrieve_status_map()

        if value == ADCMEntityStatus.UP:
            exclude_pks = {
                cluster_id for cluster_id, status_info in status_map.clusters.items() if status_info.status != 0
            }
        else:
            exclude_pks = {
                cluster_id for cluster_id, status_info in status_map.clusters.items() if status_info.status == 0
            }

        return queryset.exclude(pk__in=exclude_pks)


class ClusterHostFilter(FilterSet):
    status = ChoiceFilter(label="Host status", choices=ADCMEntityStatus.choices, method="filter_status")

    @staticmethod
    def filter_status(queryset: QuerySet, _: str, value: str) -> QuerySet:
        status_map = retrieve_status_map()

        hosts_up = {host_id for host_id, status_info in status_map.hosts.items() if status_info.status == 0}

        if value == ADCMEntityStatus.UP:
            return queryset.filter(pk__in=hosts_up)

        return queryset.exclude(pk__in=hosts_up)


class ClusterServiceFilter(FilterSet):
    status = ChoiceFilter(label="Service status", choices=ADCMEntityStatus.choices, method="filter_status")

    @staticmethod
    def filter_status(queryset: QuerySet, _: str, value: str) -> QuerySet:
        return filter_service_status(queryset=queryset, value=value)
