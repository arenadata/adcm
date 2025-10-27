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

from dataclasses import dataclass, field

from adcm.feature_flags import use_new_config_processing
from core.cluster.types import ClusterTopology
from core.job.types import TaskMappingDelta
from core.types import HostID, HostName, ServiceName
from pydantic import BaseModel
from typing_extensions import TypedDict

from cm.models import (
    Action,
    ActionHostGroup,
    Cluster,
    Component,
    Host,
    MaintenanceMode,
    ObjectType,
    Process,
    Prototype,
    Service,
)
from cm.services.cluster import retrieve_related_cluster_topology
from cm.services.job.inventory import (
    ClusterNode,
    HostGroupName,
    ProcessContext,
    ServiceNode,
    detect_host_groups_for_cluster_bundle_action,
    get_action_process_context,
    get_cluster_vars,
    sort_hosts_within_groups,
)
from cm.services.job.inventory._base import add_mapping_groups_from_process_steps
from cm.services.job import context as context_m
from cm.services.job import inventory

# For keeping garbage coupled


@dataclass(slots=True)
class ActionArgs:
    action: Action
    cluster_relative_object: Cluster | Service | Component | Host
    action_process: Process | None = None


@dataclass(slots=True)
class TaskArgs:
    target_object: Cluster | Service | Component | Host | ActionHostGroup
    action: Action
    action_process: Process | None = None

    config: dict = field(default_factory=dict)
    verbose: bool = False
    delta: TaskMappingDelta | None = None


# For Internal Typehint Purposes


class _ActionContext(TypedDict):
    owner_group: str
    name: str


class _ActionWithProcessContext(_ActionContext):
    process: inventory.ProcessContext


class _TaskContext(TypedDict):
    config: dict | None
    verbose: bool


class ActionRenderContext(BaseModel):
    cluster: inventory.ClusterNode
    services: dict[ServiceName, inventory.ServiceNode]
    groups: dict[inventory.HostGroupName, list[HostName]]
    action: _ActionContext | _ActionWithProcessContext


class TaskRenderContext(ActionRenderContext):
    task: _TaskContext


# Context Preparation Functions


def prepare_context_for_action(args: ActionArgs) -> dict:
    context = _prepare_context_for_action(
        action=args.action,
        cluster_relative_object=args.cluster_relative_object,
        action_process=args.action_process,
        delta=None,
    )
    return context.model_dump(mode="python")


def prepare_context_for_task(args: TaskArgs) -> dict:
    action_group = None
    target_object = args.target_object
    if isinstance(target_object, ActionHostGroup):
        action_group = target_object
        target_object = target_object.object

    if not isinstance(target_object, (Cluster, Service, Component, Host)):
        message = f"Target for task context can't be of type {type(target_object)}"
        raise TypeError(message)

    action_context = _prepare_context_for_action(
        action=args.action,
        cluster_relative_object=target_object,
        action_process=args.action_process,
        delta=args.delta,
    )

    if action_group:
        target_group_hosts = _get_names_of_hosts_in_action_host_group(action_group.pk)
        action_context.groups |= {"target": target_group_hosts}

    task_context = _TaskContext(config=args.config, verbose=args.verbose)

    return TaskRenderContext(
        cluster=action_context.cluster,
        services=action_context.services,
        groups=action_context.groups,
        task=task_context,
        action=action_context.action,
    ).model_dump(mode="python")


def _prepare_context_for_action(
    action: Action,
    cluster_relative_object: Cluster | Service | Component | Host,
    action_process: Process | None = None,
    delta: TaskMappingDelta | None = None,
) -> ActionRenderContext:
    cluster_topology = retrieve_related_cluster_topology(orm_object=cluster_relative_object)

    module = context_m if use_new_config_processing else inventory

    clusters_vars = module.get_cluster_vars(topology=cluster_topology)

    process_cumulative_delta = {}

    action_context = _get_action_info(action=action)

    if action_process:
        process_context = get_action_process_context(action_process, cluster_topology)
        process_cumulative_delta = process_context.cumulative_delta
        action_context = _ActionWithProcessContext(**action_context, process=process_context.to_context())

    groups = _get_host_group_names_for_cluster(
        cluster_topology=cluster_topology,
        hc_delta=delta or TaskMappingDelta(),
        process_cumulative_delta=process_cumulative_delta,
    )

    return ActionRenderContext(
        cluster=clusters_vars.cluster,
        services=clusters_vars.services,
        groups=groups,
        action=action_context,
    )


# Helper Functions


def _get_host_group_names_only(
    host_groups: dict[inventory.HostGroupName, list[tuple[HostID, HostName]]],
) -> dict[inventory.HostGroupName, list[HostName]]:
    return {group_name: [host_name for _, host_name in group_data] for group_name, group_data in host_groups.items()}


def _get_action_info(action: Action) -> _ActionContext:
    owner_prototype = action.prototype

    if owner_prototype.type == ObjectType.SERVICE:
        owner_group = owner_prototype.name
    elif owner_prototype.type == ObjectType.COMPONENT:
        parent_name = Prototype.objects.values_list("name", flat=True).get(id=owner_prototype.parent_id)
        owner_group = f"{parent_name}.{owner_prototype.name}"
    else:
        owner_group = owner_prototype.type.upper()

    return _ActionContext(name=action.name, owner_group=owner_group)


def _get_host_group_names_for_cluster(
    cluster_topology: ClusterTopology,
    hc_delta: TaskMappingDelta | None = None,
    process_cumulative_delta: dict[str, set[str]] | None = None,
) -> dict[inventory.HostGroupName, list[HostName]]:
    hosts_in_maintenance_mode: set[int] = set(
        Host.objects.filter(cluster_id=cluster_topology.cluster_id, maintenance_mode=MaintenanceMode.ON).values_list(
            "id", flat=True
        )
    )
    module = context_m if use_new_config_processing() else inventory
    host_groups = module.detect_host_groups_for_cluster_bundle_action(
            cluster_topology=cluster_topology,
            hosts_in_maintenance_mode=hosts_in_maintenance_mode,
            hc_delta=hc_delta or TaskMappingDelta(),
        )

    host_groups = add_mapping_groups_from_process_steps(
        host_groups=host_groups, process_mapping_delta=process_cumulative_delta or {}
    )
    return _get_host_group_names_only(host_groups=sort_hosts_within_groups(host_groups))


def _get_names_of_hosts_in_action_host_group(action_host_group_id: int) -> list[HostName]:
    return sorted(
        Host.objects.values_list("fqdn", flat=True).filter(
            id__in=ActionHostGroup.hosts.through.objects.filter(actionhostgroup_id=action_host_group_id).values_list(
                "host_id", flat=True
            )
        )
    )
