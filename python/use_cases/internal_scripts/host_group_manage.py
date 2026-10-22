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

from dataclasses import asdict, dataclass

from cm.errors import AdcmEx
from cm.legacy.services.job.run.executors import InternalScriptResult
from cm.models import ActionHostGroup, ConfigHostGroup
from core.action import Task
from core.action.types import HostGroupManageScript
from core.config import ConfigService
from core.types import HostID, JobID
from django.db.transaction import atomic
from rbac.scenarios import RBACScenarios

from use_cases.internal_scripts.common import build_result_message, cluster_id_of_task, provider_id_of_task
from use_cases.transition.config import UpdateHostGroupConfigurationFromJob, apply_config_changes_to_host_group
from use_cases.transition.host_group import (
    GroupAddress,
    GroupOutcome,
    HostGroupOwner,
    add_hosts,
    create_group,
    drop_hosts,
    group_key,
    remove_groups,
    resolve_host_names,
    retrieve_group_hosts,
    retrieve_groups,
    set_description,
)
from use_cases.transition.object_address import ObjectContext, resolve_object_targets

SCRIPT_NAME = "host_group_manage"


@dataclass(slots=True)
class HostGroupManageInternalScript:
    rbac_scenarios: RBACScenarios
    config_service: ConfigService
    update_host_group_configuration: UpdateHostGroupConfigurationFromJob

    def do(self, task: Task, script: HostGroupManageScript, job_id: JobID) -> InternalScriptResult:
        _ = job_id

        params = script.params

        owners = resolve_object_targets(
            targets={entry.object for entry in params.groups},
            context=ObjectContext(
                cluster_id=cluster_id_of_task(task=task, script_name=SCRIPT_NAME),
                provider_id=provider_id_of_task(task=task),
            ),
            addressed_by=f"`{SCRIPT_NAME}`",
        )
        addresses = {
            id(entry): GroupAddress(kind=entry.type, owner=owners[entry.object], name=entry.name)
            for entry in params.groups
        }

        with atomic():
            if params.operation == "remove":
                removed = remove_groups(addresses=set(addresses.values()))

                return InternalScriptResult(
                    code=0,
                    message=build_result_message(
                        script_name=SCRIPT_NAME,
                        full_complete_message=f"the named host groups are gone ({len(removed)} removed)",
                        without_updates_message="the groups were removed",
                        with_updates=bool(removed),
                    ),
                )

            outcome = GroupOutcome()
            existing = retrieve_groups(addresses=set(addresses.values()))
            membership = retrieve_group_hosts(groups=existing.values())

            groups_of_entry: dict[int, ConfigHostGroup | ActionHostGroup] = {}
            owners_of_new_groups: set[HostGroupOwner] = set()

            for entry in params.groups:
                address = addresses[id(entry)]
                group = existing.get(address)

                if group is None:
                    group = create_group(
                        address=address, description=entry.description or "", config_service=self.config_service
                    )
                    if isinstance(group, ConfigHostGroup):
                        owners_of_new_groups.add(address.owner)
                    outcome.created.append(str(address))
                elif set_description(group=group, description=entry.description or ""):
                    outcome.updated.append(str(address))

                groups_of_entry[id(entry)] = group

            # A configuration group carries its own object permissions, so the owner's policies have
            # to be re-applied once a group exists - once for the whole batch, because doing it per
            # group repeats work whose cost grows with everything the policy covers.
            for owner in owners_of_new_groups:
                self.rbac_scenarios.re_apply_object_policy(apply_object=owner)

            # Removals for every group first, then additions: a host belongs to at most one
            # configuration group of an owner, so moving one between two groups of the same owner
            # only works if it has left the first before it is offered to the second.
            wanted_of_entry: dict[int, set[HostID]] = {}
            for entry in params.groups:
                if entry.hosts is None:
                    continue

                group = groups_of_entry[id(entry)]
                wanted = set(resolve_host_names(owner=addresses[id(entry)].owner, names=entry.hosts).values())
                wanted_of_entry[id(entry)] = wanted
                outcome.hosts_removed += drop_hosts(
                    group=group, wanted=wanted, held=membership.get(group_key(group), set())
                )

            for entry in params.groups:
                if entry.hosts is None:
                    continue

                group = groups_of_entry[id(entry)]
                outcome.hosts_added += add_hosts(
                    group=group, wanted=wanted_of_entry[id(entry)], held=membership.get(group_key(group), set())
                )

            for entry in params.groups:
                if not entry.parameters:
                    continue

                address = addresses[id(entry)]
                group = groups_of_entry[id(entry)]
                if not isinstance(group, ConfigHostGroup):
                    raise AdcmEx(
                        code="INTERNAL_SERVER_ERROR",
                        msg=f"`parameters` is only allowed for a `config_host_group`, {address} is not one",
                    )

                changed = apply_config_changes_to_host_group(
                    db_object=address.owner,
                    group=group,
                    parameters=[asdict(parameter) for parameter in entry.parameters],
                    changes_description=f"{task.display_name} process update",
                    update_configuration=self.update_host_group_configuration,
                )
                if changed and str(address) not in outcome.updated:
                    outcome.updated.append(str(address))

        details = [
            f"{len(outcome.created)} created",
            f"{len(outcome.updated)} updated",
            f"{outcome.hosts_added} host(s) added",
            f"{outcome.hosts_removed} host(s) removed",
        ]

        return InternalScriptResult(
            code=0,
            message=build_result_message(
                script_name=SCRIPT_NAME,
                full_complete_message=f"the named host groups are in place ({', '.join(details)})",
                without_updates_message="the groups were set up",
                with_updates=outcome.with_updates,
            ),
        )
