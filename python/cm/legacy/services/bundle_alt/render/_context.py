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
from typing import TypeAlias
from uuid import UUID

from core.action._context._wizard_process import construct_process_info
from core.legacy.cluster.types import ClusterTopology
from core.legacy.job.types import TaskMappingDelta
from core.types import HostID, HostName
from django.conf import settings
from pydantic import BaseModel
from typing_extensions import Self, TypedDict
import core

from cm.legacy.services.cluster import retrieve_related_cluster_topology
from cm.legacy.services.job.context import (
    HostGroupName,
    ProcessContext,
    cluster_vars_to_dict,
    detect_host_groups_for_cluster_bundle_action,
    get_cluster_vars,
    sort_hosts_within_groups,
)
from cm.legacy.services.job.context._base import add_mapping_groups_from_process_steps
from cm.models import (
    ADCM,
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


_ActionOwner: TypeAlias = Cluster | Service | Component
_ActionTarget: TypeAlias = _ActionOwner | Host | ActionHostGroup


@dataclass(slots=True)
class ActionArgs:
    action: Action

    target_object: _ActionTarget
    owner_object: _ActionOwner

    wizard_process_id: core.action.wizard.ProcessID | None = None


@dataclass(slots=True)
class TaskArgs(ActionArgs):
    config: dict | None = None
    verbose: bool = False
    delta: TaskMappingDelta | None = None

    @classmethod
    def from_action_args(cls, args: ActionArgs, **kwargs) -> Self:
        return cls(
            action=args.action,
            target_object=args.target_object,
            owner_object=args.owner_object,
            wizard_process_id=args.wizard_process_id,
            **kwargs,
        )


# For Internal Typehint Purposes


class _ADCM(BaseModel):
    uuid: UUID


class _Env(TypedDict):
    consul_url: str | None
    consul_datacenter: str | None
    consul_cacert_file: str | None


class _ActionContext(TypedDict):
    owner_group: str
    name: str


class _ActionWithProcessContext(_ActionContext):
    process: ProcessContext


class _TaskContext(TypedDict):
    config: dict | None
    verbose: bool


class ActionRenderContext(BaseModel):
    cluster: dict  # ClusterNode
    services: dict[str, dict]  # dict[ServiceName, ServiceNode]
    groups: dict[HostGroupName, list[HostName]]
    action: _ActionContext | _ActionWithProcessContext
    env: _Env
    adcm: _ADCM


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
        context = self._prepare_context_for_action(args=args, delta=TaskMappingDelta())
        return context.model_dump(mode="json", by_alias=True)

    def prepare_context_for_task(self, args: TaskArgs) -> dict:
        action_context = self._prepare_context_for_action(args=args, delta=args.delta or TaskMappingDelta())

        task_context = _TaskContext(config=args.config, verbose=args.verbose)

        return TaskRenderContext(
            cluster=action_context.cluster,
            services=action_context.services,
            groups=action_context.groups,
            task=task_context,
            action=action_context.action,
            env=action_context.env,
            adcm=action_context.adcm,
        ).model_dump(mode="json", by_alias=True)

    def _prepare_context_for_action(
        self,
        *,
        args: ActionArgs,
        delta: TaskMappingDelta,
    ) -> ActionRenderContext:
        cluster_topology = retrieve_related_cluster_topology(orm_object=args.owner_object)

        clusters_vars = cluster_vars_to_dict(
            get_cluster_vars(topology=cluster_topology, config_service=self.config_service)
        )

        process_cumulative_delta = {}

        action_context = _get_action_info(action=args.action)

        if args.wizard_process_id:
            component_map = {v: k for k, v in cluster_topology.component_full_name_id_mapping.items()}
            steps = self.wizard_service.retrieve_steps_and_data_for_process(process_id=args.wizard_process_id)
            process_context = construct_process_info(
                process_id=args.wizard_process_id,
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
        match args.target_object:
            case Host(fqdn=name):
                groups["target"] = _get_target_for_host(name)

            case ActionHostGroup(pk=group_id):
                target_group_hosts = _get_names_of_hosts_in_action_host_group(group_id)
                groups["target"] = target_group_hosts

        return ActionRenderContext(
            cluster=clusters_vars["cluster"],
            services=clusters_vars["services"],
            groups=groups,
            action=action_context,
            env=_Env(
                consul_url=settings.CONSUL_URL,
                consul_datacenter=settings.CONSUL_DATACENTER,
                consul_cacert_file=settings.CONSUL_CACERT_FILE,
            ),
            adcm=_get_adcm_info(),
        )


# Helper Functions


def _get_host_group_names_only(
    host_groups: dict[HostGroupName, list[tuple[HostID, HostName]]],
) -> dict[HostGroupName, list[HostName]]:
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
) -> dict[HostGroupName, list[HostName]]:
    hosts_in_maintenance_mode: set[int] = set(
        Host.objects.filter(cluster_id=cluster_topology.cluster_id, maintenance_mode=MaintenanceMode.ON).values_list(
            "id", flat=True
        )
    )
    host_groups = detect_host_groups_for_cluster_bundle_action(
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


def _get_adcm_info() -> _ADCM:
    return _ADCM(uuid=ADCM.objects.filter().values("uuid").last()["uuid"])
