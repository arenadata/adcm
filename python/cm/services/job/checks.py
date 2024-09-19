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

import copy

from core.cluster.operations import create_topology_with_new_mapping, find_hosts_difference
from core.cluster.types import ClusterTopology, HostComponentEntry
from rest_framework.status import HTTP_409_CONFLICT

from cm.errors import AdcmEx
from cm.models import (
    Action,
    Cluster,
    ClusterObject,
    ConcernType,
    Host,
    Prototype,
    ServiceComponent,
)
from cm.services.cluster import retrieve_cluster_topology
from cm.services.concern.checks import check_mapping_restrictions
from cm.services.concern.repo import retrieve_bundle_restrictions
from cm.services.job._utils import cook_delta, get_old_hc
from cm.services.job.types import HcAclAction
from cm.services.mapping import check_no_host_in_mm

HC_CONSTRAINT_VIOLATION_ON_UPGRADE_TEMPLATE = (
    "Host-component map of upgraded cluster should satisfy constraints of new bundle. Now error is: {}"
)


def check_hostcomponentmap(
    cluster: Cluster | None, action: Action, new_hc: list[dict]
) -> tuple[list[tuple[ClusterObject, Host, ServiceComponent]] | None, list, dict[str, dict]]:
    from cm.api import check_sub_key, get_hc, make_host_comp_list

    if not action.hostcomponentmap:
        return None, [], {}

    if not new_hc:
        raise AdcmEx(code="TASK_ERROR", msg="hc is required")

    if not cluster:
        raise AdcmEx(code="TASK_ERROR", msg="Only cluster objects can have action with hostcomponentmap")

    if not hasattr(action, "upgrade"):
        for host_comp in new_hc:
            host = Host.obj.get(id=host_comp.get("host_id", 0))
            if host.concerns.filter(type=ConcernType.LOCK).exists():
                raise AdcmEx(code="LOCK_ERROR", msg=f"object {host} is locked")

            if host.concerns.filter(type=ConcernType.ISSUE).exists():
                raise AdcmEx(code="ISSUE_INTEGRITY_ERROR", msg=f"object {host} has issues")

    post_upgrade_hc, clear_hc = _check_upgrade_hc(action=action, new_hc=new_hc)
    check_sub_key(hc_in=clear_hc)

    old_hc = get_old_hc(saved_hostcomponent=get_hc(cluster=cluster))
    new_entries = tuple(
        HostComponentEntry(host_id=entry["host_id"], component_id=entry["component_id"]) for entry in clear_hc
    )

    # todo most likely this topology should be created somewhere above and passed in here as argument
    topology = retrieve_cluster_topology(cluster_id=cluster.id)
    _check_entries_are_related_to_topology(topology=topology, entries=new_entries)
    new_topology = create_topology_with_new_mapping(
        topology=topology,
        new_mapping=(
            HostComponentEntry(host_id=entry["host_id"], component_id=entry["component_id"]) for entry in clear_hc
        ),
    )
    host_difference = find_hosts_difference(new_topology=new_topology, old_topology=topology)
    check_no_host_in_mm(host_difference.mapped.all)

    if not hasattr(action, "upgrade"):
        bundle_restrictions = retrieve_bundle_restrictions(bundle_id=int(cluster.prototype.bundle_id))
        check_mapping_restrictions(mapping_restrictions=bundle_restrictions.mapping, topology=new_topology)

    else:
        bundle_restrictions = retrieve_bundle_restrictions(bundle_id=int(action.upgrade.bundle_id))
        check_mapping_restrictions(
            mapping_restrictions=bundle_restrictions.mapping,
            topology=new_topology,
            error_message_template=HC_CONSTRAINT_VIOLATION_ON_UPGRADE_TEMPLATE,
        )

    prepared_hc_list = make_host_comp_list(cluster=cluster, hc_in=clear_hc)

    delta = cook_delta(cluster=cluster, new_hc=prepared_hc_list, action_hc=action.hostcomponentmap, old=old_hc)

    return prepared_hc_list, post_upgrade_hc, delta


def _check_entries_are_related_to_topology(topology: ClusterTopology, entries: tuple[HostComponentEntry, ...]) -> None:
    if not {entry.host_id for entry in entries}.issubset(topology.hosts):
        raise AdcmEx(code="FOREIGN_HOST", http_code=HTTP_409_CONFLICT)

    if not {entry.component_id for entry in entries}.issubset(topology.component_ids):
        raise AdcmEx(code="COMPONENT_NOT_FOUND", http_code=HTTP_409_CONFLICT)


def _check_upgrade_hc(action, new_hc):
    post_upgrade_hc = []
    clear_hc = copy.deepcopy(new_hc)
    buff = 0
    for host_comp in new_hc:
        if "component_prototype_id" in host_comp:
            if not hasattr(action, "upgrade"):
                raise AdcmEx(
                    code="WRONG_ACTION_HC",
                    msg="Hc map with components prototype available only in upgrade action",
                )

            proto = Prototype.obj.get(
                type="component",
                id=host_comp["component_prototype_id"],
                bundle=action.upgrade.bundle,
            )
            for hc_acl in action.hostcomponentmap:
                if proto.name == hc_acl["component"]:
                    buff += 1
                    if hc_acl["action"] != HcAclAction.ADD.value:
                        raise AdcmEx(
                            code="WRONG_ACTION_HC",
                            msg="New components from bundle with upgrade you can only add, not remove",
                        )

            if buff == 0:
                raise AdcmEx(code="INVALID_INPUT", msg="hc_acl doesn't allow actions with this component")

            post_upgrade_hc.append(host_comp)
            clear_hc.remove(host_comp)

    return post_upgrade_hc, clear_hc
