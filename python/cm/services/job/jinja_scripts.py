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

from typing import Annotated, Generator, TypedDict

from core.job.types import JobSpec
from core.types import HostID, HostName, ServiceName, TaskID

from cm.errors import AdcmEx
from cm.models import (
    Action,
    Cluster,
    ClusterObject,
    Host,
    MaintenanceMode,
    ObjectType,
    Prototype,
    ServiceComponent,
    TaskLog,
)
from cm.services.bundle import BundlePathResolver
from cm.services.cluster import retrieve_clusters_topology
from cm.services.job.inventory import (
    ClusterNode,
    ServiceNode,
    detect_host_groups_for_cluster_bundle_action,
    get_cluster_vars,
)
from cm.services.job.inventory._types import HostGroupName
from cm.services.template import TemplateBuilder
from cm.utils import get_on_fail_states


class TaskContext(TypedDict):
    config: dict | None
    verbose: bool


class ActionContext(TypedDict):
    owner_group: str
    name: str


class JinjaScriptsEnvironment(TypedDict):
    cluster: Annotated[dict, ClusterNode]
    services: dict[ServiceName, Annotated[dict, ServiceNode]]
    groups: dict[HostGroupName, list[HostName]]
    task: TaskContext
    action: ActionContext


def get_env(task: TaskLog, delta: dict | None = None) -> JinjaScriptsEnvironment:
    target_object = task.task_object

    if isinstance(target_object, Cluster):
        cluster_topology = next(retrieve_clusters_topology([target_object.pk]))
    elif isinstance(target_object, (ClusterObject, ServiceComponent, Host)):
        cluster_topology = next(retrieve_clusters_topology([target_object.cluster_id]))
    else:
        message = f"Can't detect cluster variables for {target_object}"
        raise RuntimeError(message)  # noqa: TRY004

    cluster_vars = get_cluster_vars(topology=cluster_topology)

    hosts_in_maintenance_mode: set[int] = set(
        Host.objects.filter(cluster_id=cluster_topology.cluster_id, maintenance_mode=MaintenanceMode.ON).values_list(
            "id", flat=True
        )
    )
    host_groups = detect_host_groups_for_cluster_bundle_action(
        cluster_topology=cluster_topology, hosts_in_maintenance_mode=hosts_in_maintenance_mode, hc_delta=delta
    )

    return JinjaScriptsEnvironment(
        cluster=cluster_vars.cluster.dict(by_alias=True),
        services={
            service_name: service_data.dict(by_alias=True)
            for service_name, service_data in cluster_vars.services.items()
        },
        groups=_get_host_group_names_only(host_groups=host_groups),
        task=TaskContext(config=task.config, verbose=task.verbose),
        action=get_action_info(action=task.action),
    )


def get_job_specs_from_template(task_id: TaskID, delta: dict | None) -> Generator[JobSpec, None, None]:
    task = TaskLog.objects.select_related("action", "action__prototype__bundle").get(pk=task_id)

    scripts_jinja_file = BundlePathResolver(bundle_hash=task.action.prototype.bundle.hash).resolve(
        task.action.scripts_jinja
    )
    template_builder = TemplateBuilder(
        template_path=scripts_jinja_file,
        context=get_env(task=task, delta=delta),
        error=AdcmEx(code="UNPROCESSABLE_ENTITY", msg="Can't render jinja template"),
    )

    if not template_builder.data:
        raise RuntimeError(f'Template "{scripts_jinja_file}" has no jobs')

    for job in template_builder.data:
        state_on_fail, multi_state_on_fail_set, multi_state_on_fail_unset = get_on_fail_states(config=job)

        yield JobSpec(
            name=job["name"],
            display_name=job.get("display_name", ""),
            script=job["script"],
            script_type=job["script_type"],
            allow_to_terminate=job.get("allow_to_terminate", task.action.allow_to_terminate),
            state_on_fail=state_on_fail,
            multi_state_on_fail_set=multi_state_on_fail_set,
            multi_state_on_fail_unset=multi_state_on_fail_unset,
            params=job.get("params", {}),
        )


def _get_host_group_names_only(
    host_groups: dict[HostGroupName, set[tuple[HostID, HostName]]],
) -> dict[HostGroupName, list[HostName]]:
    return {group_name: [host_tuple[1] for host_tuple in group_data] for group_name, group_data in host_groups.items()}


def get_action_info(action: Action) -> ActionContext:
    owner_prototype = action.prototype

    if owner_prototype.type == ObjectType.SERVICE:
        owner_group = owner_prototype.name
    elif owner_prototype.type == ObjectType.COMPONENT:
        parent_name = Prototype.objects.values_list("name", flat=True).get(id=owner_prototype.parent_id)
        owner_group = f"{parent_name}.{owner_prototype.name}"
    else:
        owner_group = owner_prototype.type.upper()

    return ActionContext(name=action.name, owner_group=owner_group)


def _get_host_group_names_only(
    host_groups: dict[HostGroupName, set[tuple[HostID, HostName]]],
) -> dict[HostGroupName, list[HostName]]:
    return {group_name: [host_tuple[1] for host_tuple in group_data] for group_name, group_data in host_groups.items()}
