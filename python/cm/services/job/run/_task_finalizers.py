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

from collections import defaultdict
from logging import Logger
from typing import Protocol

from core.cluster.types import ClusterTopology, HostComponentEntry
from core.job.types import Task
from core.types import ADCMCoreType
from django.conf import settings
from django.db.models import Q

from cm.converters import core_type_to_model
from cm.models import (
    Component,
    MaintenanceMode,
    TaskLog,
    get_object_cluster,
)
from cm.services.cluster import retrieve_cluster_topology, retrieve_host_component_entries
from cm.services.job.types import TaskMappingDelta
from cm.services.mapping import change_host_component_mapping, check_nothing
from cm.status_api import send_object_update_event

# todo "unwrap" these functions to use repo without directly calling ORM,
#  try to rework functions like `save_hc` also, because they rely on API v1 input
#  which is in no way correct approach


class WithIDAndCoreType(Protocol):
    id: int
    type: ADCMCoreType


def set_hostcomponent(task: Task, logger: Logger):
    task_object = TaskLog.objects.prefetch_related("task_object").get(id=task.id).task_object

    cluster = get_object_cluster(task_object)
    if cluster is None:
        logger.error("no cluster in task #%s", task.id)

        return

    if not task.hostcomponent.mapping_delta:
        return

    cluster_topology = retrieve_cluster_topology(cluster.id)
    logger.warning("task #%s is failed, restore old hc", task.id)

    change_host_component_mapping(
        cluster_id=cluster.id,
        bundle_id=cluster.prototype.bundle_id,
        flat_mapping=retrieve_mapping_hc_delta(
            topology=cluster_topology, mapping_delta=task.hostcomponent.mapping_delta
        ),
        checks_func=check_nothing,
    )


def retrieve_mapping_hc_delta(topology: ClusterTopology, mapping_delta: TaskMappingDelta) -> set[HostComponentEntry]:
    current_entries = retrieve_host_component_entries(cluster_id=topology.cluster_id)

    # Process both additions and removals efficiently
    for operation in ("add", "remove"):
        if operation not in mapping_delta:
            continue

        # Group all hosts by component key for bulk processing
        all_component_keys = list(mapping_delta[operation].keys())
        all_hosts_by_component = defaultdict(list)

        # Collect all hosts for bulk querying
        host_map = {}
        for component_key, hosts in mapping_delta[operation].items():
            host_names = []
            for host in hosts:
                host_names.append(host[1])
                host_map[host[1]] = host[0]
            all_hosts_by_component[component_key] = host_names

        # Build component queries
        component_queries = []
        for component_key in all_component_keys:
            service_name, component_name = component_key.split(".", 1)
            component_queries.append(
                Q(
                    prototype__name=component_name,
                    cluster__id=topology.cluster_id,
                    service__prototype__name=service_name,
                )
            )

        # Batch query components
        components = {}
        if component_queries:
            query = component_queries.pop()
            for q in component_queries:
                query |= q

            for component in Component.objects.filter(query):
                key = f"{component.service.prototype.name}.{component.prototype.name}"
                components[key] = component.id

        # Apply changes to the current entries
        for component_key, hosts_to_change in all_hosts_by_component.items():
            component_id = components.get(component_key)
            if not component_id:
                continue

            for host_fqdn in hosts_to_change:
                host_id = host_map.get(host_fqdn)
                if not host_id:
                    continue

                entry = HostComponentEntry(host_id=host_id, component_id=component_id)

                if operation == "add":
                    current_entries.add(entry)
                elif operation == "remove" and entry in current_entries:
                    current_entries.remove(entry)

    return current_entries


def update_object_maintenance_mode(action_name: str, object_: WithIDAndCoreType):
    """
    If maintenance mode wasn't changed during action execution, set "opposite" (to action's name) MM
    """
    obj = core_type_to_model(core_type=object_.type).objects.get(id=object_.id)

    if (
        action_name in {settings.ADCM_TURN_ON_MM_ACTION_NAME, settings.ADCM_HOST_TURN_ON_MM_ACTION_NAME}
        and obj.maintenance_mode == MaintenanceMode.CHANGING
    ):
        obj.maintenance_mode = MaintenanceMode.OFF
        obj.save()
        send_object_update_event(object_=obj, changes={"maintenanceMode": obj.maintenance_mode})

    if (
        action_name in {settings.ADCM_TURN_OFF_MM_ACTION_NAME, settings.ADCM_HOST_TURN_OFF_MM_ACTION_NAME}
        and obj.maintenance_mode == MaintenanceMode.CHANGING
    ):
        obj.maintenance_mode = MaintenanceMode.ON
        obj.save()
        send_object_update_event(object_=obj, changes={"maintenanceMode": obj.maintenance_mode})
