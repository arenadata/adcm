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

from cm.api import check_hc, check_maintenance_mode, check_sub_key, get_hc, make_host_comp_list
from cm.errors import AdcmEx
from cm.issue import check_bound_components, check_component_constraint, check_hc_requires, check_service_requires
from cm.models import Action, Cluster, ClusterObject, ConcernType, Host, Prototype, ServiceComponent
from cm.services.job._utils import cook_delta, get_old_hc
from cm.services.job.types import HcAclAction


def check_hostcomponentmap(
    cluster: Cluster | None, action: Action, new_hc: list[dict]
) -> tuple[list[tuple[ClusterObject, Host, ServiceComponent]] | None, list]:
    if not action.hostcomponentmap:
        return None, []

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

    old_hc = get_old_hc(saved_hostcomponent=get_hc(cluster=cluster))
    if not hasattr(action, "upgrade"):
        prepared_hc_list = check_hc(cluster=cluster, hc_in=clear_hc)
    else:
        check_sub_key(hc_in=clear_hc)
        prepared_hc_list = make_host_comp_list(cluster=cluster, hc_in=clear_hc)
        check_constraints_for_upgrade(cluster=cluster, upgrade=action.upgrade, host_comp_list=prepared_hc_list)

    cook_delta(cluster=cluster, new_hc=prepared_hc_list, action_hc=action.hostcomponentmap, old=old_hc)

    return prepared_hc_list, post_upgrade_hc


def check_constraints_for_upgrade(cluster, upgrade, host_comp_list):
    try:
        for service in ClusterObject.objects.filter(cluster=cluster):
            try:
                prototype = Prototype.objects.get(name=service.name, type="service", bundle=upgrade.bundle)
                check_component_constraint(
                    cluster=cluster,
                    service_prototype=prototype,
                    hc_in=[i for i in host_comp_list if i[0] == service],
                    old_bundle=cluster.prototype.bundle,
                )
                check_service_requires(cluster=cluster, proto=prototype)
            except Prototype.DoesNotExist:
                pass

        check_hc_requires(shc_list=host_comp_list)
        check_bound_components(shc_list=host_comp_list)
        check_maintenance_mode(cluster=cluster, host_comp_list=host_comp_list)
    except AdcmEx as e:
        if e.code == "COMPONENT_CONSTRAINT_ERROR":
            e.msg = (
                f"Host-component map of upgraded cluster should satisfy "
                f"constraints of new bundle. Now error is: {e.msg}"
            )

        raise AdcmEx(code=e.code, msg=e.msg) from e


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
