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

from collections.abc import Iterable

from core.metrics import ClusterMetricsRepoI, ClusterResources, format_size_from_bytes
from core.metrics._types import ClusterIdResourcesDict, ObjectsMonitoring
from core.types import ClusterID, ComponentID, ServiceID
from django.db.models import BigIntegerField, ObjectDoesNotExist, QuerySet, Sum
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Coalesce

from cm.models import Component, HostInfo, Service


class ClusterMetricsRepo(ClusterMetricsRepoI):
    _host_info_fields = ("host__cluster_id", "cpu_vcores", "ram", "disk")

    def get_resources(self, cluster_ids: Iterable[ClusterID]) -> dict[ClusterID, ClusterIdResourcesDict]:
        queryset = HostInfo.objects.filter(host__cluster_id__in=cluster_ids, host__original_id__isnull=True)
        rows = _hardware_info_query(queryset=queryset)

        resources = (
            {
                cluster_id: {
                    "cpu_vcores": cpu_vcores,
                    "ram": format_size_from_bytes(ram),
                    "disk": format_size_from_bytes(disk),
                }
                for cluster_id, cpu_vcores, ram, disk in rows.values_list(*self._host_info_fields)
            }
            if rows
            else {}
        )

        return {
            cluster_id: ClusterIdResourcesDict(
                id=cluster_id,  # empty dict is for typechecker
                resources=ClusterResources(**resources.get(cluster_id, {})) if resources.get(cluster_id) else None,
            )
            for cluster_id in cluster_ids
        }

    def get_monitorings(
        self, services: Iterable[ServiceID] = (), components: Iterable[ComponentID] = ()
    ) -> ObjectsMonitoring:
        _values = ("id", "prototype__monitoring")

        services_qs = Service.objects.filter(id__in=services).values(*_values)
        components_qs = Component.objects.filter(id__in=components).values(*_values)

        return ObjectsMonitoring(
            services={s["id"]: s["prototype__monitoring"] for s in services_qs},
            components={c["id"]: c["prototype__monitoring"] for c in components_qs},
        )


def _hardware_info_query(queryset: QuerySet[HostInfo]) -> QuerySet | None:
    try:
        return queryset.values("host__cluster_id").annotate(
            cpu_vcores=_sum_from_json("cpu_vcores"),
            ram=_sum_from_json("ram_bytes"),
            disk=_sum_from_json("disk_size"),
        )
    except ObjectDoesNotExist:
        return None


def _sum_from_json(key: str) -> Sum:
    value_from_json = KeyTextTransform(key, "value")
    to_bigint = Cast(value_from_json, output_field=BigIntegerField())
    value_or_zero = Coalesce(to_bigint, 0, output_field=BigIntegerField())

    return Sum(value_or_zero)
