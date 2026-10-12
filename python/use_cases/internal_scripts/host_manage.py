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

from collections.abc import Sequence
from dataclasses import dataclass

from cm.converters import core_type_to_model
from cm.errors import AdcmEx
from cm.legacy.services.job.run.executors import InternalScriptResult
from cm.models import Cluster, Component, Service
from cm.transition.status import StatusScenarios
from core.action import HostGroupReference, TargetCluster, Task, TaskMappingDelta
from core.action.job import JobRepoI, TaskUpdateDTO
from core.action.types import HostManageScript, HostManageScriptParams
from core.cluster import ClusterService
from core.config import ConfigService
from core.types import ClusterID, HostID, JobID
from django.db.transaction import atomic
from rbac.scenarios import RBACScenarios

from use_cases.internal_scripts.common import build_result_message, cluster_id_of_task, provider_id_of_task
from use_cases.transition.host_group import GroupAddress, add_hosts, group_key, retrieve_group_hosts, retrieve_groups
from use_cases.transition.host_manage import (
    SelectionContext,
    add_duplicates,
    duplicates_here,
    forget_hosts_in_delta,
    merge_mapping_delta,
    remove_duplicates,
    resolve_source,
    write_mapping_delta,
)
from use_cases.transition.object_address import ObjectContext, resolve_object_targets

SCRIPT_NAME = "host_manage"


@dataclass(slots=True)
class HostManageInternalScript:
    config_service: ConfigService
    cluster_service: ClusterService
    rbac_scenarios: RBACScenarios
    status_scenarios: StatusScenarios
    job_repo: JobRepoI

    def do(self, task: Task, script: HostManageScript, job_id: JobID) -> InternalScriptResult:
        _ = job_id

        cluster_id = cluster_id_of_task(task=task, script_name=SCRIPT_NAME)
        if cluster_id is None:
            raise AdcmEx(
                code="WRONG_OWNER",
                msg=f"Internal script `{SCRIPT_NAME}` can only be defined in cluster, service or component context",
            )

        params = script.params
        context = SelectionContext(cluster_id=cluster_id, provider_id=provider_id_of_task(task=task))

        with atomic():
            selected = resolve_source(source=params.source, context=context)

            match params.operation:
                case "add_duplicates":
                    return self._add_duplicates(task=task, params=params, selected=selected, cluster_id=cluster_id)

                case "add_to_groups":
                    added = _apply_group_membership(
                        task=task,
                        references=params.groups or (),
                        host_ids=duplicates_here(host_ids=selected, cluster_id=cluster_id),
                        cluster_id=cluster_id,
                    )

                    return InternalScriptResult(
                        code=0,
                        message=build_result_message(
                            script_name=SCRIPT_NAME,
                            full_complete_message=f"the hosts are in their groups ({added} membership(s) added)",
                            without_updates_message="the hosts were added to their groups",
                            with_updates=bool(added),
                        ),
                    )

                case _:
                    return self._remove_duplicates(task=task, selected=selected, cluster_id=cluster_id)

    def _add_duplicates(
        self, task: Task, params: HostManageScriptParams, selected: list[HostID], cluster_id: ClusterID
    ) -> InternalScriptResult:
        target_cluster_ids = _resolve_target_clusters(targets=params.target, here=cluster_id)

        if cluster_id not in target_cluster_ids and (params.mapping_rules or params.groups):
            raise AdcmEx(
                code="INTERNAL_SERVER_ERROR",
                msg="`mapping_rules` and `groups` act on this cluster, but `target` sends every "
                "duplicate somewhere else - there would be nothing here for them to apply to",
            )

        outcome = add_duplicates(
            source_host_ids=selected,
            target_cluster_ids=target_cluster_ids,
            here=cluster_id,
            config_service=self.config_service,
            rbac_scenarios=self.rbac_scenarios,
            status_scenarios=self.status_scenarios,
        )

        mapped = {}
        if params.mapping_rules:
            # into a delta of its own first: a task that turns out to need no mapping change must
            # not end up carrying an empty delta it did not have before
            prepared = TaskMappingDelta()
            mapped = write_mapping_delta(
                delta=prepared, rules=params.mapping_rules, host_ids=outcome.here, cluster_id=cluster_id
            )
            if mapped:
                delta = _mapping_delta_of_task(task=task)
                merge_mapping_delta(into=delta, addition=prepared)
                self.job_repo.update_task(id=task.id, data=TaskUpdateDTO(hostcomponentmap=delta))

        added = _apply_group_membership(
            task=task, references=params.groups or (), host_ids=set(outcome.here), cluster_id=cluster_id
        )

        details = [f"{outcome.created_count} created", f"{outcome.existing_count} already here"]
        if mapped:
            details.append(f"{sum(mapped.values())} mapping change(s) prepared")
        if added:
            details.append(f"{added} group membership(s) added")

        return InternalScriptResult(
            code=0,
            message=build_result_message(
                script_name=SCRIPT_NAME,
                full_complete_message=f"the selected hosts are duplicated here ({', '.join(details)})",
                without_updates_message="the hosts were duplicated",
                with_updates=bool(outcome.created_count or mapped or added),
            ),
        )

    def _remove_duplicates(self, task: Task, selected: list[HostID], cluster_id: ClusterID) -> InternalScriptResult:
        outcome = remove_duplicates(
            source_host_ids=selected,
            here=cluster_id,
            cluster_service=self.cluster_service,
            rbac_scenarios=self.rbac_scenarios,
        )

        # The delta is applied once more when the task finishes; a host deleted here must not be
        # left in it, or that final application fails on a host the cluster no longer has.
        delta = task.hostcomponent.mapping_delta
        if (
            delta is not None
            and outcome.removed_ids
            and forget_hosts_in_delta(delta=delta, host_ids=outcome.removed_ids)
        ):
            self.job_repo.update_task(id=task.id, data=TaskUpdateDTO(hostcomponentmap=delta))

        return InternalScriptResult(
            code=0,
            message=build_result_message(
                script_name=SCRIPT_NAME,
                full_complete_message=f"the duplicates of the selected hosts are gone ({len(outcome.removed)} deleted)",
                without_updates_message="the duplicates were removed",
                with_updates=bool(outcome.removed),
            ),
        )


def _resolve_target_clusters(targets: Sequence[TargetCluster] | None, here: ClusterID) -> list[ClusterID]:
    if not targets:
        return [here]

    names = {target.cluster_name for target in targets}
    found = dict(Cluster.objects.filter(name__in=names).values_list("name", "id"))

    missing = sorted(names - set(found))
    if missing:
        raise AdcmEx(
            code="CLUSTER_NOT_FOUND",
            msg=f"`target` names {', '.join(missing)}, which this ADCM does not manage",
        )

    return sorted(found.values())


def _mapping_delta_of_task(task: Task) -> TaskMappingDelta:
    """The delta this task carries, created on demand.

    Internal scripts of one task all hold the same `Task`, so a delta put here is what a later
    `hc_apply` in the same task reads. It is written to the database as well, which is where
    the inventory of every job after this one picks it up.
    """

    if task.hostcomponent.mapping_delta is None:
        task.hostcomponent = task.hostcomponent._replace(mapping_delta=TaskMappingDelta())

    delta = task.hostcomponent.mapping_delta
    if delta is None:
        raise RuntimeError("Task mapping delta: was given None, expected an object")

    return delta


def _apply_group_membership(
    task: Task, references: Sequence[HostGroupReference], host_ids: set[HostID], cluster_id: ClusterID
) -> int:
    """Add the given hosts to every named group. The groups must already exist."""

    if not references or not host_ids:
        return 0

    if task.owner is None:
        raise RuntimeError("Task owner: was given None, expected an object")

    default_owner = core_type_to_model(core_type=task.owner.type).objects.get(pk=task.owner.id)
    if not isinstance(default_owner, Cluster | Service | Component):
        message = f"Task owner: was given {type(default_owner).__name__}, expected Cluster, Service or Component"
        raise RuntimeError(message)  # noqa: TRY004

    explicit = {reference.object for reference in references if reference.object is not None}
    owners = resolve_object_targets(
        targets=explicit,
        context=ObjectContext(cluster_id=cluster_id, provider_id=provider_id_of_task(task=task)),
        addressed_by=f"`{SCRIPT_NAME}` `groups`",
    )

    addresses = [
        GroupAddress(
            kind=reference.type,
            owner=owners[reference.object] if reference.object is not None else default_owner,
            name=reference.name,
        )
        for reference in references
    ]

    existing = retrieve_groups(addresses=set(addresses))
    missing = sorted(str(address) for address in addresses if address not in existing)
    if missing:
        raise AdcmEx(
            code="GROUP_CONFIG_NOT_FOUND",
            msg=f"`{SCRIPT_NAME}` puts hosts into {', '.join(missing)}, which does not exist. "
            "Create it with `host_group_manage` first - this script only manages membership.",
        )

    membership = retrieve_group_hosts(groups=existing.values())

    added = 0
    # deduplicated: two references naming the same group would otherwise be handed the same
    # "already held" set twice and try to insert the same membership rows again
    for address in sorted(set(addresses), key=str):
        group = existing[address]
        added += add_hosts(group=group, wanted=host_ids, held=membership.get(group_key(group), set()))

    return added
