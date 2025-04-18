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

from typing import Iterable

from core.types import ClusterID, ComponentID, HostID
from django.db import transaction
from django.db.models import Q

from cm.models import Component, HostComponent


def lock_cluster_mapping(cluster_id: ClusterID) -> None:
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("There is no sense in using SELECT FOR UPDATE outside of a transaction")

    tuple(HostComponent.objects.select_for_update().filter(cluster_id=cluster_id).values_list())


def _apply_mapping_delta_in_db(
    cluster_id: ClusterID,
    to_add: Iterable[tuple[HostID, ComponentID]],
    to_remove: Iterable[tuple[HostID, ComponentID]],
) -> None:
    to_add = list(to_add)  # ensure value can be reused if it is a generator

    remove_condition = Q()
    for host_id, component_id in to_remove:
        remove_condition |= Q(host_id=host_id, component_id=component_id)

    if remove_condition:
        HostComponent.objects.filter(remove_condition).delete()

    if not to_add:
        return

    comp_service_ids_map = {
        component.id: component.service_id
        for component in Component.objects.filter(id__in=(item[1] for item in to_add))
    }

    hc_create = []
    for host_id, component_id in to_add:
        hc_create.append(
            HostComponent(
                cluster_id=cluster_id,
                host_id=host_id,
                component_id=component_id,
                service_id=comp_service_ids_map[component_id],
            )
        )
    HostComponent.objects.bulk_create(objs=hc_create, ignore_conflicts=True)
