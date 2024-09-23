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
from functools import partial
from typing import TypeAlias

from core.cluster.types import HostComponentEntry
from core.job.dto import TaskPayloadDTO
from core.types import ActionTargetDescriptor, CoreObjectDescriptor
from django.conf import settings
from django.db.transaction import atomic, on_commit
from rbac.roles import re_apply_policy_for_jobs

from cm.adcm_config.checks import check_attr
from cm.adcm_config.config import check_config_spec, get_prototype_config, process_config_spec, process_file_type
from cm.api import get_hc
from cm.converters import model_name_to_core_type, orm_object_to_action_target_type, orm_object_to_core_type
from cm.errors import AdcmEx
from cm.models import (
    ADCM,
    Action,
    ActionHostGroup,
    Cluster,
    ClusterObject,
    ConcernType,
    ConfigLog,
    Host,
    HostProvider,
    JobStatus,
    ServiceComponent,
    TaskLog,
)
from cm.services.cluster import retrieve_cluster_topology
from cm.services.concern.repo import retrieve_bundle_restrictions
from cm.services.config.spec import convert_to_flat_spec_from_proto_flat_spec
from cm.services.job.checks import (
    HC_CONSTRAINT_VIOLATION_ON_UPGRADE_TEMPLATE,
    check_hostcomponentmap,
    check_mapping_restrictions,
)
from cm.services.job.inventory._config import update_configuration_for_inventory_inplace
from cm.services.job.prepare import prepare_task_for_action
from cm.services.job.run import run_task
from cm.services.mapping import change_host_component_mapping
from cm.status_api import send_task_status_update_event
from cm.variant import process_variant

ObjectWithAction: TypeAlias = ADCM | Cluster | ClusterObject | ServiceComponent | HostProvider | Host
ActionTarget: TypeAlias = ObjectWithAction | ActionHostGroup


@dataclass
class ActionRunPayload:
    conf: dict = field(default_factory=dict)
    attr: dict = field(default_factory=dict)
    hostcomponent: list[dict] = field(default_factory=list)
    verbose: bool = False


def run_action(action: Action, obj: ActionTarget, payload: ActionRunPayload) -> TaskLog:
    action_objects = _ActionLaunchObjects(target=obj, action=action)

    _check_no_target_conflict(target=action_objects.target, action=action)
    _check_no_blocking_concerns(lock_owner=action_objects.object_to_lock, action_name=action.name)
    _check_action_is_available_for_object(owner=action_objects.owner, action=action)

    spec, flat_spec = _process_run_config(
        action=action, owner=action_objects.owner, conf=payload.conf, attr=payload.attr
    )
    host_map, post_upgrade_hc, delta, is_upgrade_action = _process_hostcomponent(
        cluster=action_objects.cluster, action=action, new_hostcomponent=payload.hostcomponent
    )

    with atomic():
        task = prepare_task_for_action(
            target=ActionTargetDescriptor(
                id=action_objects.target.id, type=orm_object_to_action_target_type(action_objects.target)
            ),
            owner=CoreObjectDescriptor(id=action_objects.owner.id, type=orm_object_to_core_type(action_objects.owner)),
            action=action.pk,
            payload=TaskPayloadDTO(
                conf=payload.conf,
                attr=payload.attr,
                verbose=payload.verbose,
                hostcomponent=get_hc(cluster=action_objects.cluster),
                post_upgrade_hostcomponent=post_upgrade_hc,
            ),
            delta=delta,
        )

        on_commit(func=partial(send_task_status_update_event, task_id=task.id, status=JobStatus.CREATED.value))

        task_ = TaskLog.objects.get(id=task.id)
        _finish_task_preparation(
            task=task_,
            owner=action_objects.owner,
            cluster=action_objects.cluster,
            host_map=host_map,
            is_upgrade_action=is_upgrade_action,
            payload=payload,
            spec=spec,
            flat_spec=flat_spec,
        )

    re_apply_policy_for_jobs(action_object=action_objects.owner, task=task_)

    run_task(task_)

    return task_


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
    """Related cluster, is None for own HostProvider/Host actions"""

    def __init__(self, target: ActionTarget, action: Action) -> None:
        self.target = target
        self.object_to_lock = self.target

        if isinstance(target, (Cluster, ClusterObject, ServiceComponent)):
            self.owner = target
            self.cluster = target if isinstance(target, Cluster) else target.cluster
        elif action.host_action and isinstance(target, Host):
            self.cluster = target.cluster
            match action.prototype.type:
                case "component":
                    self.owner = ServiceComponent.objects.get(cluster=self.cluster, prototype=action.prototype)
                case "service":
                    self.owner = ClusterObject.objects.get(cluster=self.cluster, prototype=action.prototype)
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


def _process_hostcomponent(
    cluster: Cluster | None, action: Action, new_hostcomponent: list[dict]
) -> tuple[list[tuple[ClusterObject, Host, ServiceComponent]] | None, list, dict[str, dict], bool]:
    is_upgrade_action = hasattr(action, "upgrade")

    if not cluster:
        if not new_hostcomponent:
            return None, [], {}, is_upgrade_action

        # Don't think it's even required check on action preparation,
        # should be handled one level above
        raise AdcmEx(code="TASK_ERROR", msg="Only cluster objects can have action with hostcomponentmap")

    # `check_hostcomponentmap` won't run checks in these conditions, because it's checking actions with `hc_acl`.
    # But this code checks whether existing hostcomponent satisfies constraints from new bundle.
    if is_upgrade_action and not action.hostcomponentmap:
        topology = retrieve_cluster_topology(cluster_id=cluster.id)
        bundle_restrictions = retrieve_bundle_restrictions(bundle_id=int(action.upgrade.bundle_id))

        check_mapping_restrictions(
            mapping_restrictions=bundle_restrictions.mapping,
            topology=topology,
            error_message_template=HC_CONSTRAINT_VIOLATION_ON_UPGRADE_TEMPLATE,
        )

        return None, [], {}, is_upgrade_action

    host_map, post_upgrade_hc, delta = check_hostcomponentmap(cluster=cluster, action=action, new_hc=new_hostcomponent)

    return host_map, post_upgrade_hc, delta, is_upgrade_action


def _finish_task_preparation(
    task: TaskLog,
    owner: ObjectWithAction,
    cluster: Cluster | None,
    host_map: list[tuple[ClusterObject, Host, ServiceComponent]] | None,
    is_upgrade_action: bool,
    payload: ActionRunPayload,
    spec: dict,
    flat_spec: dict,
):
    if host_map or (is_upgrade_action and host_map is not None):
        change_host_component_mapping(
            cluster_id=cluster.id,
            bundle_id=cluster.prototype.bundle_id,
            flat_mapping=(
                HostComponentEntry(host_id=host.id, component_id=component.id) for (_, host, component) in host_map
            ),
            skip_checks=True,
        )

    if payload.conf:
        new_conf = update_configuration_for_inventory_inplace(
            configuration=payload.conf,
            attributes=payload.attr,
            specification=convert_to_flat_spec_from_proto_flat_spec(prototypes_flat_spec=flat_spec),
            config_owner=CoreObjectDescriptor(
                id=owner.pk, type=model_name_to_core_type(model_name=owner._meta.model_name)
            ),
        )
        process_file_type(obj=task, spec=spec, conf=payload.conf)
        task.config = new_conf
        task.save(update_fields=["config"])
