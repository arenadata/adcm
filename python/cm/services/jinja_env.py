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

from typing import Annotated, TypedDict

from core.cluster.types import ClusterTopology
from core.types import HostID, HostName, ServiceName

from cm.models import (
    Action,
    ActionHostGroup,
    Cluster,
    Component,
    Host,
    MaintenanceMode,
    ObjectType,
    Prototype,
    Service,
    TaskLog,
)
from cm.services.cluster import retrieve_related_cluster_topology
from cm.services.job.inventory import (
    ClusterNode,
    ServiceNode,
    detect_host_groups_for_cluster_bundle_action,
    get_cluster_vars,
)
from cm.services.job.inventory._types import HostGroupName
from cm.services.job.types import TaskMappingDelta


class ActionContext(TypedDict):
    owner_group: str
    name: str


class TaskContext(TypedDict):
    config: dict | None
    verbose: bool


class JinjaScriptsEnvironment(TypedDict):
    cluster: Annotated[dict, ClusterNode]
    services: dict[ServiceName, Annotated[dict, ServiceNode]]
    groups: dict[HostGroupName, list[HostName]]
    task: TaskContext
    action: ActionContext


class JinjaConfigsEnvironment(TypedDict):
    cluster: ClusterNode
    services: dict[str, ServiceNode]
    groups: dict[HostGroupName, list[HostName]]
    action: ActionContext


def get_env_for_jinja_scripts(task: TaskLog, delta: TaskMappingDelta | None = None) -> JinjaScriptsEnvironment:
    action_group = None
    target_object = task.task_object
    if isinstance(target_object, ActionHostGroup):
        action_group = target_object
        target_object = target_object.object

    cluster_topology = retrieve_related_cluster_topology(orm_object=target_object)

    cluster_vars = get_cluster_vars(topology=cluster_topology)

    host_groups = _get_host_group_names_for_cluster(cluster_topology, hc_delta=delta)
    if action_group:
        host_groups |= {
            "target": Host.objects.values_list("fqdn", flat=True).filter(
                id__in=ActionHostGroup.hosts.through.objects.filter(actionhostgroup_id=action_group.id).values_list(
                    "host_id", flat=True
                )
            )
        }

    return JinjaScriptsEnvironment(
        cluster=cluster_vars.cluster.model_dump(by_alias=True),
        services={
            service_name: service_data.model_dump(by_alias=True)
            for service_name, service_data in cluster_vars.services.items()
        },
        groups=host_groups,
        task=TaskContext(config=task.config, verbose=task.verbose),
        action=_get_action_info(action=task.action),
    )


def get_env_for_jinja_config(
    action: Action, cluster_relative_object: Cluster | Service | Component | Host
) -> JinjaConfigsEnvironment:
    cluster_topology = retrieve_related_cluster_topology(orm_object=cluster_relative_object)
    clusters_vars = get_cluster_vars(topology=retrieve_related_cluster_topology(orm_object=cluster_relative_object))

    return JinjaConfigsEnvironment(
        cluster=clusters_vars.cluster,
        services=clusters_vars.services,
        groups=_get_host_group_names_for_cluster(cluster_topology=cluster_topology),
        action=_get_action_info(action=action),
    )


def _get_host_group_names_only(
    host_groups: dict[HostGroupName, set[tuple[HostID, HostName]]],
) -> dict[HostGroupName, list[HostName]]:
    return {group_name: [host_tuple[1] for host_tuple in group_data] for group_name, group_data in host_groups.items()}


def _get_action_info(action: Action) -> ActionContext:
    owner_prototype = action.prototype

    if owner_prototype.type == ObjectType.SERVICE:
        owner_group = owner_prototype.name
    elif owner_prototype.type == ObjectType.COMPONENT:
        parent_name = Prototype.objects.values_list("name", flat=True).get(id=owner_prototype.parent_id)
        owner_group = f"{parent_name}.{owner_prototype.name}"
    else:
        owner_group = owner_prototype.type.upper()

    return ActionContext(name=action.name, owner_group=owner_group)


def _get_host_group_names_for_cluster(
    cluster_topology: ClusterTopology, hc_delta: TaskMappingDelta | None = None
) -> dict[HostGroupName, list[HostName]]:
    hosts_in_maintenance_mode: set[int] = set(
        Host.objects.filter(cluster_id=cluster_topology.cluster_id, maintenance_mode=MaintenanceMode.ON).values_list(
            "id", flat=True
        )
    )
    return _get_host_group_names_only(
        host_groups=detect_host_groups_for_cluster_bundle_action(
            cluster_topology=cluster_topology,
            hosts_in_maintenance_mode=hosts_in_maintenance_mode,
            hc_delta=hc_delta or TaskMappingDelta(),
        )
    )
