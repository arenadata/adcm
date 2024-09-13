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

from cm.models import Host, MaintenanceMode
from django.db.models import QuerySet
from django_filters import ChoiceFilter
from django_filters.rest_framework import (
    BooleanFilter,
    CharFilter,
    FilterSet,
    NumberFilter,
    OrderingFilter,
)


class HostFilter(FilterSet):
    name = CharFilter(label="Host name", field_name="fqdn", lookup_expr="icontains")
    hostprovider_name = CharFilter(label="Hostprovider name", field_name="provider__name", lookup_expr="icontains")
    cluster_name = CharFilter(label="Cluster name", field_name="cluster__name", lookup_expr="icontains")
    is_in_cluster = BooleanFilter(label="Is host in cluster", method="filter_is_in_cluster")
    state = CharFilter(field_name="state", label="Host state", lookup_expr="icontains")
    description = CharFilter(field_name="description", label="Host description", lookup_expr="icontains")
    maintenance_mode = ChoiceFilter(
        label="Maintenance mode", choices=MaintenanceMode.choices, method="filter_by_maintenance_mode"
    )
    ordering = OrderingFilter(
        fields={
            "description": "description",
            "fqdn": "name",
            "id": "id",
            "state": "state",
            "provider__name": "hostproviderName",
            "cluster__name": "clusterName",
        },
        field_labels={
            "description": "Description",
            "fqdn": "Name",
            "id": "Id",
            "state": "State",
            "provider__name": "Hostprovider name",
            "cluster__name": "Cluster name",
        },
        label="ordering",
    )

    class Meta:
        model = Host
        fields = [
            "id",
            "state",
            "description",
            "name",
            "hostprovider_name",
            "cluster_name",
            "is_in_cluster",
            "maintenance_mode",
        ]

    @staticmethod
    def filter_is_in_cluster(queryset: QuerySet, _, value: bool) -> QuerySet:
        return queryset.filter(cluster__isnull=not value)

    @staticmethod
    def filter_by_maintenance_mode(queryset: QuerySet, name: str, value: str) -> QuerySet:  # noqa: ARG004
        return queryset.filter(maintenance_mode=value)


class HostMemberFilter(FilterSet):
    name = CharFilter(label="Host name", field_name="fqdn", lookup_expr="icontains")
    hostprovider_name = CharFilter(label="Hostprovider name", field_name="provider__name", lookup_expr="icontains")
    component_id = NumberFilter(label="Component id", field_name="hostcomponent__component_id")
    state = CharFilter(field_name="state", label="Host state", lookup_expr="icontains")
    description = CharFilter(field_name="description", label="Host description", lookup_expr="icontains")
    maintenance_mode = ChoiceFilter(
        label="Maintenance mode", choices=MaintenanceMode.choices, method="filter_by_maintenance_mode"
    )
    ordering = OrderingFilter(
        fields={
            "description": "description",
            "fqdn": "name",
            "state": "state",
            "id": "id",
            "provider__name": "hostproviderName",
        },
        field_labels={
            "description": "Description",
            "name": "Name",
            "id": "Id",
            "state": "State",
            "hostproviderName": "Hostprovider name",
        },
        label="ordering",
    )

    class Meta:
        model = Host
        fields = [
            "id",
            "name",
            "hostprovider_name",
            "component_id",
            "maintenance_mode",
            "state",
            "description",
        ]

    @staticmethod
    def filter_by_maintenance_mode(queryset: QuerySet, name: str, value: str) -> QuerySet:  # noqa: ARG004
        return queryset.filter(maintenance_mode=value)
