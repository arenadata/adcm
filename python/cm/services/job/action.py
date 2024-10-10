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
from typing import Iterable, TypeAlias

from core.cluster.operations import create_topology_with_new_mapping, find_hosts_difference
from core.cluster.types import ClusterTopology, HostComponentEntry
from core.job.dto import TaskPayloadDTO
from core.types import ActionTargetDescriptor, BundleID, CoreObjectDescriptor, HostID
from django.conf import settings
from django.db.transaction import atomic
from rbac.roles import re_apply_policy_for_jobs
from rest_framework.status import HTTP_409_CONFLICT

from cm.adcm_config.checks import check_attr
from cm.adcm_config.config import check_config_spec, get_prototype_config, process_config_spec, process_file_type
from cm.converters import orm_object_to_action_target_type, orm_object_to_core_type
from cm.errors import AdcmEx
from cm.models import (
    ADCM,
    Action,
    ActionHostGroup,
    Cluster,
    Component,
    ConcernType,
    ConfigLog,
    Host,
    JobStatus,
    Provider,
    Service,
    TaskLog,
)
from cm.services.bundle import retrieve_bundle_restrictions
from cm.services.cluster import retrieve_cluster_topology
from cm.services.concern.checks import check_mapping_restrictions
from cm.services.config.spec import convert_to_flat_spec_from_proto_flat_spec
from cm.services.job._utils import check_delta_is_allowed, construct_delta_for_task
from cm.services.job.constants import HC_CONSTRAINT_VIOLATION_ON_UPGRADE_TEMPLATE
from cm.services.job.inventory._config import update_configuration_for_inventory_inplace
from cm.services.job.prepare import prepare_task_for_action
from cm.services.job.run import run_task
from cm.services.job.types import ActionHCRule, TaskMappingDelta
from cm.services.mapping import change_host_component_mapping, check_no_host_in_mm, check_nothing
from cm.status_api import send_task_status_update_event
from cm.variant import process_variant

ObjectWithAction: TypeAlias = ADCM | Cluster | Service | Component | Provider | Host
ActionTarget: TypeAlias = ObjectWithAction | ActionHostGroup


@dataclass
class ActionRunPayload:
    conf: dict = field(default_factory=dict)
    attr: dict = field(default_factory=dict)
    hostcomponent: set[HostComponentEntry] = field(default_factory=set)
    verbose: bool = False


def run_action(
    action: Action, obj: ActionTarget, payload: ActionRunPayload, post_upgrade_hc: list[dict] | None = None
) -> TaskLog:
    task_payload = TaskPayloadDTO(
        conf=payload.conf,
        attr=payload.attr,
        verbose=payload.verbose,
        hostcomponent=None,
        post_upgrade_hostcomponent=post_upgrade_hc,
    )

    action_objects = _ActionLaunchObjects(target=obj, action=action)

    is_upgrade_action = hasattr(action, "upgrade")
    action_has_hc_acl = bool(action.hostcomponentmap)

    if action_has_hc_acl and not action_objects.cluster:
        raise AdcmEx(code="TASK_ERROR", msg="Only cluster objects can have action with hostcomponentmap")

    _check_no_target_conflict(target=action_objects.target, action=action)
    _check_no_blocking_concerns(lock_owner=action_objects.object_to_lock, action_name=action.name)
    _check_action_is_available_for_object(owner=action_objects.owner, action=action)

    spec, flat_spec = _process_run_config(
        action=action, owner=action_objects.owner, conf=payload.conf, attr=payload.attr
    )

    delta = TaskMappingDelta()
    if action_objects.cluster and (action_has_hc_acl or is_upgrade_action):
        topology = retrieve_cluster_topology(cluster_id=action_objects.cluster.id)
        delta = _check_hostcomponent_and_get_delta(
            bundle_id=int(action.prototype.bundle_id),
            topology=topology,
            hc_payload=payload.hostcomponent,
            hc_rules=action.hostcomponentmap,
            mapping_restriction_err_template=HC_CONSTRAINT_VIOLATION_ON_UPGRADE_TEMPLATE if is_upgrade_action else "{}",
        )
        if action_has_hc_acl:
            # current topology should be saved
            task_payload.hostcomponent = {
                HostComponentEntry(host_id=host_id, component_id=component_id)
                for service in topology.services.values()
                for component_id, component in service.components.items()
                for host_id in component.hosts
            }

    with atomic():
        owner = CoreObjectDescriptor(id=action_objects.owner.id, type=orm_object_to_core_type(action_objects.owner))
        target = ActionTargetDescriptor(
            id=action_objects.target.id, type=orm_object_to_action_target_type(action_objects.target)
        )
        task = prepare_task_for_action(target=target, owner=owner, action=action.id, payload=task_payload, delta=delta)

        orm_task = TaskLog.objects.get(id=task.id)

        # Original check: `if host_map or (is_upgrade_action and host_map is not None)`.
        # I believe second condition is the same as "is cluster action with hc"
        if action_objects.cluster and (payload.hostcomponent or (is_upgrade_action and action_has_hc_acl)):
            change_host_component_mapping(
                cluster_id=action_objects.cluster.id,
                bundle_id=int(action_objects.cluster.prototype.bundle_id),
                flat_mapping=payload.hostcomponent,
                checks_func=check_nothing,
            )

        if payload.conf:
            new_conf = update_configuration_for_inventory_inplace(
                configuration=payload.conf,
                attributes=payload.attr,
                specification=convert_to_flat_spec_from_proto_flat_spec(prototypes_flat_spec=flat_spec),
                config_owner=owner,
            )
            process_file_type(obj=orm_task, spec=spec, conf=payload.conf)
            orm_task.config = new_conf
            orm_task.save(update_fields=["config"])

        re_apply_policy_for_jobs(action_object=action_objects.owner, task=orm_task)

    run_task(orm_task)

    send_task_status_update_event(task_id=task.id, status=JobStatus.CREATED.value)

    return orm_task


class _ActionLaunchObjects:
    """
    Utility container to process differences in action's target/owner in one place
    """

    __slots__ = ("target", "owner", "cluster", "object_to_lock")

    target: ActionTarget
    """Object on which action will be launched: may be owner OR host with this object OR action host group"""

    owner: ObjectWithAction
    """Object that "owns" action: action is described in """

    object_to_lock: ObjectWithAction
    """Object owner of locks/issues and which will be locked on action launch"""

    cluster: Cluster | None
    """Related cluster, is None for own Provider/Host actions"""

    def __init__(self, target: ActionTarget, action: Action) -> None:
        self.target = target
        self.object_to_lock = self.target

        if isinstance(target, (Cluster, Service, Component)):
            self.owner = target
            self.cluster = target if isinstance(target, Cluster) else target.cluster
        elif action.host_action and isinstance(target, Host):
            self.cluster = target.cluster
            match action.prototype.type:
                case "component":
                    self.owner = Component.objects.get(cluster=self.cluster, prototype=action.prototype)
                case "service":
                    self.owner = Service.objects.get(cluster=self.cluster, prototype=action.prototype)
                case "cluster":
                    self.owner = self.cluster
                case _:
                    message = f"Can't handle {action.prototype.type} type for owner of host action detection"
                    raise NotImplementedError(message)
        elif isinstance(target, ActionHostGroup):
            # action group support only objects in Cluster hierarchy,
            # so we can safely assume that there is related cluster
            self.owner = target.object
            self.cluster = self.owner if isinstance(self.owner, Cluster) else self.owner.cluster
            self.object_to_lock = self.owner
        else:
            self.owner = target
            self.cluster = None  # it's safe to assume cluster is None for host own action


def _check_no_target_conflict(target: ActionTarget, action: Action) -> None:
    if action.host_action and not isinstance(target, Host):
        message = "Running host action without targeting host is prohibited"
        raise AdcmEx(code="TASK_ERROR", msg=message)

    if isinstance(target, ActionHostGroup) and not action.allow_for_action_host_group:
        message = f"Action {action.display_name} isn't allowed to be launched on action host group"
        raise AdcmEx(code="TASK_ERROR", msg=message)


def _check_no_blocking_concerns(lock_owner: ObjectWithAction, action_name: str) -> None:
    object_locks = lock_owner.concerns.filter(type=ConcernType.LOCK)

    if action_name == settings.ADCM_DELETE_SERVICE_ACTION_NAME:
        object_locks = object_locks.exclude(owner_id=lock_owner.id, owner_type=lock_owner.content_type)

    if object_locks.exists():
        raise AdcmEx(code="LOCK_ERROR", msg=f"object {lock_owner} is locked")

    if (
        action_name not in settings.ADCM_SERVICE_ACTION_NAMES_SET
        and lock_owner.concerns.filter(type=ConcernType.ISSUE).exists()
    ):
        raise AdcmEx(code="ISSUE_INTEGRITY_ERROR", msg=f"object {lock_owner} has issues")


def _check_action_is_available_for_object(owner: ObjectWithAction, action: Action) -> None:
    if not action.allowed(obj=owner):
        raise AdcmEx(code="TASK_ERROR", msg="action is disabled")


def _process_run_config(action: Action, owner: ObjectWithAction, conf: dict, attr: dict) -> tuple[dict, dict]:
    proto = action.prototype
    spec, flat_spec, _, _ = get_prototype_config(prototype=proto, action=action, obj=owner)
    if not spec:
        if conf:
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg="Absent config in action prototype")

        return {}, {}

    if not conf:
        raise AdcmEx("TASK_ERROR", "action config is required")

    check_attr(proto, action, attr, flat_spec)

    object_config = {}
    if owner.config is not None:
        object_config = ConfigLog.objects.get(id=owner.config.current).config

    process_variant(obj=owner, spec=spec, conf=object_config)
    check_config_spec(proto=proto, obj=action, spec=spec, flat_spec=flat_spec, conf=conf, attr=attr)

    process_config_spec(obj=owner, spec=spec, new_config=conf)

    return spec, flat_spec


def _check_hostcomponent_and_get_delta(
    bundle_id: BundleID,
    topology: ClusterTopology,
    hc_payload: set[HostComponentEntry],
    hc_rules: list[ActionHCRule],
    mapping_restriction_err_template: str,
) -> TaskMappingDelta | None:
    existing_hosts = set(topology.hosts)
    existing_components = set(topology.component_ids)

    for entry in hc_payload:
        if entry.host_id not in existing_hosts:
            raise AdcmEx(code="FOREIGN_HOST", http_code=HTTP_409_CONFLICT)

        if entry.component_id not in existing_components:
            raise AdcmEx(code="COMPONENT_NOT_FOUND", http_code=HTTP_409_CONFLICT)

    with_hc_acl = bool(hc_rules)
    # if there aren't hc_acl rules, then `payload.hostcomponent` is irrelevant
    new_topology = (
        create_topology_with_new_mapping(topology=topology, new_mapping=hc_payload) if with_hc_acl else topology
    )

    bundle_restrictions = retrieve_bundle_restrictions(bundle_id=bundle_id)
    check_mapping_restrictions(
        mapping_restrictions=bundle_restrictions.mapping,
        topology=new_topology,
        error_message_template=mapping_restriction_err_template,
    )

    host_difference = find_hosts_difference(new_topology=new_topology, old_topology=topology)
    check_no_host_in_mm(host_difference.mapped.all)
    # some of newly mapped hosts may have concerns
    _check_no_blocking_concerns_on_hosts(host_difference.mapped.all)

    if with_hc_acl:
        delta = construct_delta_for_task(topology=new_topology, host_difference=host_difference)
        check_delta_is_allowed(delta=delta, rules=hc_rules)
        return delta

    return None


def _check_no_blocking_concerns_on_hosts(hosts: Iterable[HostID]) -> None:
    # this function should be a generic function like "retrieve_concerns_from_objects",
    # but exact use cases (=> API) aren't clear now, so implementation is put out for later.
    hosts_with_concerns = tuple(
        Host.concerns.through.objects.filter(host_id__in=hosts, concernitem__blocking=True)
        .values_list("host_id", flat=True)
        .distinct()
    )
    if hosts_with_concerns:
        host_names = ",".join(sorted(Host.objects.filter(id__in=hosts_with_concerns).values_list("fqdn", flat=True)))
        raise AdcmEx(code="ISSUE_INTEGRITY_ERROR", msg=f"Hosts are locked or have issues: {host_names}")
