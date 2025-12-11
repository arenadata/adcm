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

from dataclasses import dataclass
from functools import partial

from adcm.feature_flags import use_new_config_processing
from core.action._context._wizard_process import construct_process_info
from core.legacy.cluster.types import ClusterTopology
from core.legacy.job.types import TaskMappingDelta
from core.types import HostID, HostName, ServiceName
from pydantic import BaseModel
from typing_extensions import TypedDict
import core

from cm.legacy.services.cluster import retrieve_related_cluster_topology
from cm.legacy.services.job import context as context_m
from cm.legacy.services.job import inventory
from cm.legacy.services.job.inventory import (
    sort_hosts_within_groups,
)
from cm.legacy.services.job.inventory._base import add_mapping_groups_from_process_steps
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
)

# For keeping garbage coupled


@dataclass(slots=True)
class ActionArgs:
    action: Action
    cluster_relative_object: Cluster | Service | Component | Host
    wizard_process_id: core.action.wizard.ProcessID | None = None


@dataclass(slots=True)
class TaskArgs:
    target_object: Cluster | Service | Component | Host | ActionHostGroup
    action: Action
    wizard_process_id: core.action.wizard.ProcessID | None = None

    config: dict | None = None
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


# Context Preparation


@dataclass(slots=True)
class ContextGatherer:
    config_service: core.config.ConfigService
    wizard_service: core.action.wizard.WizardService

    def prepare_context_for_action(
        self,
        args: ActionArgs,
    ) -> dict:
        context = self._prepare_context_for_action(
            action=args.action,
            cluster_relative_object=args.cluster_relative_object,
            wizard_process_id=args.wizard_process_id,
            delta=TaskMappingDelta(),
        )
        return context.model_dump(mode="python", by_alias=True)

    def prepare_context_for_task(self, args: TaskArgs) -> dict:
        target_object = args.target_object
        extra_groups = {}

        if isinstance(target_object, ActionHostGroup):
            target_group_hosts = _get_names_of_hosts_in_action_host_group(target_object.pk)
            extra_groups = {"target": target_group_hosts}

            # override target object for further processing
            target_object = target_object.object
        elif isinstance(target_object, Host):
            extra_groups = {"target": _get_target_for_host(target_object.fqdn)}

        if not isinstance(target_object, (Cluster, Service, Component, Host)):
            message = f"Target for task context can't be of type {type(target_object)}"
            raise TypeError(message)

        action_context = self._prepare_context_for_action(
            action=args.action,
            cluster_relative_object=target_object,
            wizard_process_id=args.wizard_process_id,
            delta=args.delta or TaskMappingDelta(),
        )

        action_context.groups |= extra_groups

        task_context = _TaskContext(config=args.config, verbose=args.verbose)

        return TaskRenderContext(
            cluster=action_context.cluster,
            services=action_context.services,
            groups=action_context.groups,
            task=task_context,
            action=action_context.action,
        ).model_dump(mode="python", by_alias=True)

    def _prepare_context_for_action(
        self,
        *,
        action: Action,
        cluster_relative_object: Cluster | Service | Component | Host,
        delta: TaskMappingDelta,
        wizard_process_id: core.action.wizard.ProcessID | None,
    ) -> ActionRenderContext:
        cluster_topology = retrieve_related_cluster_topology(orm_object=cluster_relative_object)

        if use_new_config_processing():
            get_cluster_vars = partial(context_m.get_cluster_vars, config_service=self.config_service)
        else:
            get_cluster_vars = inventory.get_cluster_vars

        clusters_vars = get_cluster_vars(topology=cluster_topology)

        process_cumulative_delta = {}

        action_context = _get_action_info(action=action)

        if wizard_process_id:
            component_map = {v: k for k, v in cluster_topology.component_full_name_id_mapping.items()}
            steps = self.wizard_service.retrieve_steps_and_data_for_process(process_id=wizard_process_id)
            process_context = construct_process_info(
                process_id=wizard_process_id,
                steps_with_data=steps,
                component_map=component_map,
                host_map=cluster_topology.hosts,
                config_service=self.config_service,
            )
            process_cumulative_delta = process_context.cumulative_delta
            action_context = _ActionWithProcessContext(**action_context, process=process_context.to_context())

        groups = _get_host_group_names_for_cluster(
            cluster_topology=cluster_topology,
            hc_delta=delta,
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
    hc_delta: TaskMappingDelta,
    process_cumulative_delta: dict[str, set[tuple[int, str]]],
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
        hc_delta=hc_delta,
    )

    host_groups = add_mapping_groups_from_process_steps(
        host_groups=host_groups, process_mapping_delta=process_cumulative_delta
    )
    return _get_host_group_names_only(host_groups=sort_hosts_within_groups(host_groups))


def _get_target_for_host(host_name: HostName) -> list[HostName]:
    return [host_name]


def _get_names_of_hosts_in_action_host_group(action_host_group_id: int) -> list[HostName]:
    return sorted(
        Host.objects.values_list("fqdn", flat=True).filter(
            id__in=ActionHostGroup.hosts.through.objects.filter(actionhostgroup_id=action_host_group_id).values_list(
                "host_id", flat=True
            )
        )
    )
