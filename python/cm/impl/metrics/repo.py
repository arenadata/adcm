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

from collections.abc import Generator, Iterable

from core.metrics import ClusterMetrics, ClusterMetricsRepoI, ClusterResources, format_size_from_bytes
from core.types import ClusterID
from django.db.models import BigIntegerField, QuerySet, Sum
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Coalesce

from cm.models import HostInfo


class ClusterMetricsRepo(ClusterMetricsRepoI):
    _host_info_fields = ("host__cluster_id", "cpu_vcores", "ram", "disk")

    def get_latest(self, cluster_id: ClusterID) -> ClusterMetrics:
        queryset = HostInfo.objects.filter(host__cluster_id=cluster_id, host__original_id__isnull=True)
        row = _hardware_info_query(queryset=queryset).values_list(*self._host_info_fields).get()

        cluster_id, cpu_vcores, ram, disk = row

        return ClusterMetrics(
            id=cluster_id,
            resources=ClusterResources(
                cpu_vcores=cpu_vcores,
                ram=format_size_from_bytes(ram),
                disk=format_size_from_bytes(disk),
            ),
        )

    def get_latest_many(self, cluster_ids: Iterable[ClusterID]) -> Generator[ClusterMetrics, None, None]:
        queryset = HostInfo.objects.filter(host__cluster_id__in=cluster_ids, host__original_id__isnull=True)
        rows = _hardware_info_query(queryset=queryset).values_list(*self._host_info_fields)

        return (
            ClusterMetrics(
                id=cluster_id,
                resources=ClusterResources(
                    cpu_vcores=cpu_vcores,
                    ram=format_size_from_bytes(ram),
                    disk=format_size_from_bytes(disk),
                ),
            )
            for cluster_id, cpu_vcores, ram, disk in rows
        )


def _hardware_info_query(queryset: QuerySet[HostInfo]) -> QuerySet:
    return queryset.values("host__cluster_id").annotate(
        cpu_vcores=_sum_from_json("cpu_vcores"),
        ram=_sum_from_json("ram_bytes"),
        disk=_sum_from_json("disk_size"),
    )


def _sum_from_json(key: str) -> Sum:
    value_from_json = KeyTextTransform(key, "value")
    to_bigint = Cast(value_from_json, output_field=BigIntegerField())
    value_or_zero = Coalesce(to_bigint, 0, output_field=BigIntegerField())

    return Sum(value_or_zero)
