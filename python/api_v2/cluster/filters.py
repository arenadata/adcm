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
from cm.status_api import get_cluster_status, get_host_status, get_service_status
from django.db.models import QuerySet
from django_filters.rest_framework import (
    CharFilter,
    ChoiceFilter,
    FilterSet,
    OrderingFilter,
)


class ClusterFilter(FilterSet):
    status = ChoiceFilter(label="Cluster status", choices=ADCMEntityStatus.choices, method="filter_status")
    prototype_name = CharFilter(label="Cluster prototype name", field_name="prototype__name")
    prototype_display_name = CharFilter(label="Cluster prototype display name", field_name="prototype__display_name")
    name = CharFilter(label="Cluster name", lookup_expr="icontains")
    ordering = OrderingFilter(
        fields={
            "name": "name",
            "prototype__display_name": "prototypeDisplayName",
        },
        field_labels={
            "name": "Cluster name",
            "prototype__display_name": "Product",
        },
        label="ordering",
    )

    class Meta:
        model = Cluster
        fields = ("id", "name", "status", "prototype_name", "prototype_display_name")

    @staticmethod
    def filter_status(queryset: QuerySet, _: str, value: str) -> QuerySet:
        if value == ADCMEntityStatus.UP:
            exclude_pks = {cluster.pk for cluster in queryset if get_cluster_status(cluster=cluster) != 0}
        else:
            exclude_pks = {cluster.pk for cluster in queryset if get_cluster_status(cluster=cluster) == 0}

        return queryset.exclude(pk__in=exclude_pks)


class ClusterHostFilter(FilterSet):
    status = ChoiceFilter(label="Host status", choices=ADCMEntityStatus.choices, method="filter_status")

    @staticmethod
    def filter_status(queryset: QuerySet, _: str, value: str) -> QuerySet:
        if value == ADCMEntityStatus.UP:
            exclude_pks = {host.pk for host in queryset if get_host_status(host=host) != 0}
        else:
            exclude_pks = {host.pk for host in queryset if get_host_status(host=host) == 0}

        return queryset.exclude(pk__in=exclude_pks)


class ClusterServiceFilter(FilterSet):
    status = ChoiceFilter(label="Service status", choices=ADCMEntityStatus.choices, method="filter_status")

    @staticmethod
    def filter_status(queryset: QuerySet, _: str, value: str) -> QuerySet:
        if value == ADCMEntityStatus.UP:
            exclude_pks = {service.pk for service in queryset if get_service_status(service=service) != 0}
        else:
            exclude_pks = {service.pk for service in queryset if get_service_status(service=service) == 0}

        return queryset.exclude(pk__in=exclude_pks)
