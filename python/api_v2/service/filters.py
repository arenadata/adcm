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

from cm.models import ADCMEntityStatus, Cluster, ClusterObject, MaintenanceMode, ObjectType
from cm.services.cluster import (
    retrieve_cluster_topology,
    retrieve_clusters_objects_maintenance_mode,
)
from core.cluster.operations import calculate_maintenance_mode_for_cluster_objects
from django.db.models import QuerySet
from django_filters.rest_framework import (
    CharFilter,
    ChoiceFilter,
    FilterSet,
    OrderingFilter,
)

from api_v2.filters import filter_service_status


class ServiceFilter(FilterSet):
    name = CharFilter(label="Service name", method="filter_name", lookup_expr="icontains")
    display_name = CharFilter(label="Display name", field_name="prototype__display_name", lookup_expr="icontains")
    status = ChoiceFilter(label="Service status", choices=ADCMEntityStatus.choices, method="filter_status")
    state = CharFilter(label="Cluster state", lookup_expr="icontains")
    maintenance_mode = ChoiceFilter(
        label="Maintenance mode", choices=MaintenanceMode.choices, method="filter_by_maintenance_mode"
    )
    ordering = OrderingFilter(
        fields={"id": "id", "prototype__display_name": "displayName", "prototype__name": "name", "state": "state"},
        field_labels={
            "id": "ID",
            "prototype__display_name": "Display name",
            "prototype__name": "Name",
            "state": "State",
        },
    )

    class Meta:
        model = ClusterObject
        fields = ["id", "name", "display_name", "status", "maintenance_mode", "state"]

    @staticmethod
    def filter_status(queryset: QuerySet, _: str, value: str) -> QuerySet:
        return filter_service_status(queryset=queryset, value=value)

    @staticmethod
    def filter_name(queryset: QuerySet, name: str, value: str) -> QuerySet:  # noqa: ARG001, ARG004
        return queryset.filter(prototype__type=ObjectType.SERVICE, prototype__name__icontains=value)

    def filter_by_maintenance_mode(self, queryset: QuerySet, name: str, value: str) -> QuerySet:  # noqa: ARG002
        cluster_id = int(self.request.parser_context["kwargs"]["cluster_pk"])
        mm_is_allowed = (
            Cluster.objects.values("prototype__allow_maintenance_mode").filter(id=cluster_id).first() or False
        )
        if not mm_is_allowed:
            if value != MaintenanceMode.OFF:
                return ClusterObject.objects.none()
            return queryset

        topology = retrieve_cluster_topology(cluster_id)

        objects_mm = calculate_maintenance_mode_for_cluster_objects(
            topology=topology,
            own_maintenance_mode=retrieve_clusters_objects_maintenance_mode(cluster_ids=(topology.cluster_id,)),
        )

        objects_mm_services_ids = [c for c, v in objects_mm.services.items() if v.value == value]

        return ClusterObject.objects.filter(id__in=objects_mm_services_ids)
