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
    BooleanFilter,
    CharFilter,
    NumberFilter,
    OrderingFilter,
)

from api_v2.filters import AdvancedFilterSet


class HostFilter(
    AdvancedFilterSet,
    char_fields=(("name", "fqdn"),),
    number_fields=("id", ("hostprovider", "provider__id")),
    with_object_status=True,
):
    name = CharFilter(
        label="Case insensitive and partial filter by host name.", field_name="fqdn", lookup_expr="icontains"
    )
    hostprovider_name = CharFilter(
        label="Filter by hostprovider name.", field_name="provider__name", lookup_expr="exact"
    )
    cluster_name = CharFilter(label="Filter by cluster name.", field_name="cluster__name", lookup_expr="exact")
    is_in_cluster = BooleanFilter(label="Filter by is host in cluster.", method="filter_is_in_cluster")
    ordering = OrderingFilter(
        fields={
            "fqdn": "name",
            "id": "id",
            "state": "state",
            "provider__name": "hostproviderName",
            "cluster__name": "clusterName",
        },
        field_labels={
            "fqdn": "Name",
            "id": "Id",
            "state": "State",
            "provider__name": "Hostprovider name",
            "cluster__name": "Cluster name",
        },
        label="ordering",
    )

    @staticmethod
    def filter_is_in_cluster(queryset: QuerySet, _, value: bool) -> QuerySet:
        return queryset.filter(cluster__isnull=not value)


class ClusterHostFilter(
    AdvancedFilterSet,
    char_fields=(("name", "fqdn"),),
    number_fields=("id", ("hostprovider", "provider__id")),
    with_object_status=True,
):
    name = CharFilter(
        label="Case insensitive and partial filter by host name.", field_name="fqdn", lookup_expr="icontains"
    )
    hostprovider_name = CharFilter(
        label="Filter by hostprovider name.", field_name="provider__name", lookup_expr="exact"
    )
    component_id = NumberFilter(label="Filter by component id.", field_name="hostcomponent__component_id")
    ordering = OrderingFilter(
        fields={
            "fqdn": "name",
            "state": "state",
            "id": "id",
            "provider__name": "hostproviderName",
        },
        field_labels={
            "name": "Name",
            "id": "Id",
            "state": "State",
            "hostproviderName": "Hostprovider name",
        },
        label="ordering",
    )


class HostGroupHostFilter(
    AdvancedFilterSet,
    char_fields=(("name", "fqdn"),),
    number_fields=("id", ("hostprovider", "provider__id")),
    with_object_status=True,
):
    name = CharFilter(label="Host name", field_name="fqdn", lookup_expr="icontains")
    hostprovider_name = CharFilter(label="Hostprovider name", field_name="provider__name", lookup_expr="exact")
    ordering = OrderingFilter(
        fields={
            "fqdn": "name",
            "state": "state",
            "id": "id",
            "provider__name": "hostproviderName",
        },
        field_labels={
            "name": "Name",
            "id": "Id",
            "state": "State",
            "hostproviderName": "Hostprovider name",
        },
        label="ordering",
    )
