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

from cm.models import Cluster, ClusterObject, MaintenanceMode, ServiceComponent
from cm.services.cluster import (
    retrieve_clusters_objects_maintenance_mode,
    retrieve_clusters_topology,
)
from core.cluster.operations import calculate_maintenance_mode_for_cluster_objects
from django.db.models import QuerySet
from django_filters import ChoiceFilter
from django_filters.rest_framework import CharFilter, FilterSet, OrderingFilter


class ComponentFilter(FilterSet):
    name = CharFilter(field_name="prototype__name", label="Name", lookup_expr="icontains")
    display_name = CharFilter(field_name="prototype__display_name", label="Display Name", lookup_expr="icontains")
    state = CharFilter(field_name="state", label="State", lookup_expr="icontains")
    maintenance_mode = ChoiceFilter(
        label="Maintenance mode", choices=MaintenanceMode.choices, method="filter_by_maintenance_mode"
    )
    ordering = OrderingFilter(
        fields={"id": "id", "prototype__name": "name", "prototype__display_name": "displayName", "state": "state"},
        field_labels={
            "id": "ID",
            "prototype__name": "Name",
            "prototype__display_name": "Display Name",
            "state": "State",
        },
        label="ordering",
    )

    class Meta:
        model = ServiceComponent
        fields = ["id", "name", "display_name", "state", "maintenance_mode"]

    def filter_by_maintenance_mode(self, queryset: QuerySet, name: str, value: str) -> QuerySet:  # noqa: ARG002
        cluster_id = int(self.request.parser_context["kwargs"]["cluster_pk"])
        mm_is_allowed = (
            Cluster.objects.values("prototype__allow_maintenance_mode").filter(id=cluster_id).first() or False
        )
        if not mm_is_allowed:
            if value != MaintenanceMode.OFF:
                return ClusterObject.objects.none()
            return queryset

        topology = next(retrieve_clusters_topology([cluster_id]))

        objects_mm = calculate_maintenance_mode_for_cluster_objects(
            topology=topology,
            own_maintenance_mode=retrieve_clusters_objects_maintenance_mode(cluster_ids=(topology.cluster_id,)),
        )

        objects_mm_components_ids = [c for c, v in objects_mm.components.items() if v.value == value]

        return ServiceComponent.objects.filter(id__in=objects_mm_components_ids)
