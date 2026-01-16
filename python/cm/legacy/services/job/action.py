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
from typing import Iterable, Sequence, TypeAlias

from adcm.feature_flags import use_new_job_scheduler
from core.legacy.cluster.operations import create_topology_with_new_mapping, find_hosts_difference
from core.legacy.cluster.types import ClusterTopology, HostComponentEntry
from core.legacy.job.dto import LogCreateDTO, TaskPayloadDTO
from core.legacy.job.errors import TaskCreateError
from core.legacy.job.types import AssociatedProcess, JobSpec, ScriptType, Task, TaskMappingDelta
from core.templates import Template
from core.types import ActionID, ActionTargetDescriptor, BundleID, CoreObjectDescriptor, GeneralEntityDescriptor, HostID
from django.conf import settings
from django.db.transaction import atomic
from infra.services import get_config_service, get_wizard_service
from rbac.roles import re_apply_policy_for_jobs
from rest_framework.status import HTTP_409_CONFLICT
import core

from cm.converters import orm_object_to_action_target_type, orm_object_to_core_type
from cm.errors import AdcmEx
from cm.legacy.adcm_config.checks import check_attr
from cm.legacy.adcm_config.config import check_config_spec, get_prototype_config, process_config_spec
from cm.legacy.services.action_process.types import ProcessState
from cm.legacy.services.bundle import retrieve_bundle_restrictions
from cm.legacy.services.bundle_alt.render import ContextGatherer, Environment, TaskArgs, render_scripts
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.concern.checks import check_mapping_restrictions
from cm.legacy.services.config.spec import convert_to_flat_spec_from_proto_flat_spec
from cm.legacy.services.job._utils import check_delta_is_allowed, construct_delta_for_task
from cm.legacy.services.job.constants import HC_CONSTRAINT_VIOLATION_ON_UPGRADE_TEMPLATE
from cm.legacy.services.job.inventory._config import update_configuration_for_inventory_inplace
from cm.legacy.services.job.jinja_scripts import get_job_specs_from_template
from cm.legacy.services.job.run import start_task
from cm.legacy.services.job.run.repo import ActionRepoImpl, JobRepoImpl
from cm.legacy.services.job.types import ActionHCRule
from cm.legacy.services.mapping import check_no_host_in_mm
from cm.legacy.status_api import send_task_status_update_event
from cm.legacy.variant import process_variant
from cm.models import (
    ADCM,
    UNFINISHED_STATUS,
    Action,
    ActionHostGroup,
    Cluster,
    Component,
    ConcernType,
    ConfigLog,
    Host,
    JobStatus,
    Process,
    Provider,
    Service,
    TaskLog,
)

ObjectWithAction: TypeAlias = ADCM | Cluster | Service | Component | Provider | Host
ActionTarget: TypeAlias = ObjectWithAction | ActionHostGroup


@dataclass(slots=True)
class ActionRunPayload:
    conf: dict = field(default_factory=dict)
    attr: dict = field(default_factory=dict)
    hostcomponent: set[HostComponentEntry] = field(default_factory=set)
    verbose: bool = False
    is_blocking: bool = True
    process: AssociatedProcess | None = None
    description: str = ""


def run_action(
    action: Action,
    obj: ActionTarget,
    payload: ActionRunPayload,
    post_upgrade_hc: list[dict] | None = None,
    feature_scripts_jinja: bool = False,
) -> TaskLog:
    action_objects = _ActionLaunchObjects(target=obj, action=action)

    is_upgrade_action = hasattr(action, "upgrade")
    action_has_hc_acl = bool(action.hostcomponentmap)

    if action_has_hc_acl and not action_objects.cluster:
        raise AdcmEx(code="TASK_ERROR", msg="Only cluster objects can have action with hostcomponentmap")

    # shouldn't be here, extract and check correctly
    if action.wizard_template:
        if payload.process is None:
            raise AdcmEx(code="TASK_ERROR", msg="Process must be specified for this action")

        if not Process.objects.filter(
            id=payload.process.id,
            action=action,
            target_id=obj.id,
            target_type=orm_object_to_action_target_type(obj).value,
            state=ProcessState.COMPLETED,
        ).exists():
            raise AdcmEx(code="TASK_ERROR", msg="Process must be bound to action and be in completed state")

    _check_no_target_conflict(target=action_objects.target, action=action)
    check_no_blocking_concerns(lock_owner=action_objects.object_to_lock, action_name=action.name)
    _check_action_is_not_already_launched(owner=action_objects.object_to_lock, action_id=action.pk)
    _check_action_is_available_for_object(owner=action_objects.owner, action=action)

    delta = None
    if action_objects.cluster and (action_has_hc_acl or is_upgrade_action):
        topology = retrieve_cluster_topology(cluster_id=action_objects.cluster.id)
        delta = check_hostcomponent_and_get_delta(
            bundle_id=int(action.prototype.bundle_id),
            topology=topology,
            hc_payload=payload.hostcomponent,
            hc_rules=action.hostcomponentmap,
            mapping_restriction_err_template=HC_CONSTRAINT_VIOLATION_ON_UPGRADE_TEMPLATE if is_upgrade_action else "{}",
        )

    task_payload = TaskPayloadDTO(
        conf=payload.conf,
        attr=payload.attr,
        verbose=payload.verbose,
        mapping_delta=delta,
        post_upgrade_hostcomponent=post_upgrade_hc,
        is_blocking=payload.is_blocking,
        process=payload.process,
        description=payload.description,
    )

    with atomic():
        target = ActionTargetDescriptor(
            id=action_objects.target.pk, type=orm_object_to_action_target_type(action_objects.target)
        )
        task = prepare_task_for_action(
            target=target,
            orm_owner=action_objects.owner,
            orm_target=action_objects.target,
            action=action.pk,
            payload=task_payload,
            delta=delta,
            feature_scripts_jinja=feature_scripts_jinja,
        )

        orm_task = TaskLog.objects.get(id=task.id)
        re_apply_policy_for_jobs(action_object=action_objects.owner, task=orm_task)

    if not use_new_job_scheduler():
        start_task(orm_task)

    send_task_status_update_event(task_id=task.id, status=JobStatus.CREATED.value)

    return orm_task


def prepare_task_for_action(
    target: ActionTargetDescriptor,
    orm_owner: ObjectWithAction,
    orm_target: ActionTarget,
    action: ActionID,
    payload: TaskPayloadDTO,
    delta: TaskMappingDelta | None = None,
    feature_scripts_jinja: bool = False,
) -> Task:
    """
    Prepare task based on action, target object and task payload.

    Target object is an object on which action is going to be launched, not the on it's described on.

    `Task` is launched action, "task for ADCM to perform action" in other words.
    `Job` is an actual piece of work required by task to be performed.

    ! WARNING !
    Currently, stdout/stderr logs are created alongside the jobs
    for policies to be re-applied correctly after this method is called.

    It may be changed if favor of creating logs when job is actually prepared/started.

    ! ADCM-6012 !
    Code moved from `core.job.task` here, because it's unclear for now
    how required level of unity can be implemented with enough isolation and readability.
    """
    job_repo = JobRepoImpl
    action_repo = ActionRepoImpl
    owner = CoreObjectDescriptor(id=orm_owner.pk, type=orm_object_to_core_type(orm_owner))
    orm_action = Action.objects.select_related("prototype").get(id=action)

    spec, flat_spec, _, _ = get_prototype_config(prototype=orm_action.prototype, action=orm_action, obj=orm_owner)

    if not spec:
        if payload.conf:
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg="Absent config in action prototype")

    elif not payload.conf:
        raise AdcmEx("TASK_ERROR", "action config is required")

    action_info = action_repo.get_action(id=action)

    task = job_repo.create_task(target=target, owner=owner, action=action_info, payload=payload)

    if payload.conf:
        orm_task = TaskLog.objects.get(id=task.id)

        _process_run_config(
            action=orm_action,
            owner=orm_owner,
            task=orm_task,
            conf=payload.conf,
            attr=payload.attr or {},
            spec=spec,
            flat_spec=flat_spec,
        )

        orm_task.config = update_configuration_for_inventory_inplace(
            configuration=payload.conf,
            attributes=payload.attr or {},
            specification=convert_to_flat_spec_from_proto_flat_spec(prototypes_flat_spec=flat_spec),
            config_owner=GeneralEntityDescriptor(id=task.id, type="task"),
        )

        orm_task.save(update_fields=["config"])
        # reread to update config
        # ! this should be reworked when "layering" will be performed
        task = job_repo.get_task(id=task.id)

    if action_info.scripts_jinja:
        job_specifications = tuple(
            get_job_specs_from_template(task_id=task.id, delta=delta, feature_scripts_jinja=feature_scripts_jinja)
        )
        if any(
            specs.script_type == ScriptType.INTERNAL and specs.script == "config_apply" for specs in job_specifications
        ):
            message = "Internal script 'config_apply' can't be used for jinja action"
            raise AdcmEx(code="INTERNAL_SERVER_ERROR", msg=message)
    elif action_info.scripts_template:
        if not isinstance(orm_target, (Cluster, Service, Component, Host, ActionHostGroup)):
            message = f"Can't render scripts for target of type {type(target)}"
            raise TypeError(message)

        if not isinstance(orm_owner, (Cluster, Service, Component, Host)):
            message = f"Can't render scripts for owner of type {type(orm_owner)}"
            raise TypeError(message)

        job_specifications = _render_scripts_from_template(
            template=action_info.scripts_template,
            action=orm_action,
            target=orm_target,
            context_gatherer=ContextGatherer(config_service=get_config_service(), wizard_service=get_wizard_service()),
        )
    else:
        job_specifications = tuple(action_repo.get_job_specs(id=action))

    if not job_specifications:
        message = f"Can't compose task for action #{action}, because no associated jobs found"
        raise TaskCreateError(message)

    job_repo.create_jobs(task_id=task.id, jobs=job_specifications)

    logs = []
    for job in job_repo.get_task_jobs(task_id=task.id):
        logs.append(LogCreateDTO(job_id=job.id, name=job.type.value, type="stdout", format="txt"))
        logs.append(LogCreateDTO(job_id=job.id, name=job.type.value, type="stderr", format="txt"))

    if logs:
        job_repo.create_logs(logs)

    return task


def _render_scripts_from_template(
    template: Template,
    target: Cluster | Service | Component | Host | ActionHostGroup,
    action: Action,
    context_gatherer: ContextGatherer,
) -> tuple[JobSpec, ...]:
    # todo this level is too deep for working with that stuff, it should be passed from outside
    #      yet it's a problem to do this now,
    #      request for process should be separated too
    bundle_root = settings.BUNDLE_DIR / action.prototype.bundle.hash
    process_id: core.action.wizard.ProcessID | None = (
        Process.objects.filter(
            action_id=action.pk,
            target_id=target.pk,
            target_type=orm_object_to_action_target_type(target).value,
        )
        .values_list("id", flat=True)
        .order_by("-created_at")
        .first()
    )

    environment = Environment(bundle_root=bundle_root)
    task_args = TaskArgs(
        target_object=target,
        action=action,
        config={},
        verbose=False,
        delta=None,
        wizard_process_id=process_id,
    )
    step_spec = render_scripts(
        template=template, environment=environment, context_args=task_args, context_gatherer=context_gatherer
    )
    return tuple(step_spec)


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


def check_no_blocking_concerns(lock_owner: ObjectWithAction, action_name: str) -> None:
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


def _check_action_is_not_already_launched(owner: ObjectWithAction, action_id: ActionID) -> None:
    """
    Since ADCM-6081 it's possible to launch action that won't "lock" objects with concern.
    So it was decided to introduce a general rule that the same action shouldn't be "running" (not finished).
    """

    if TaskLog.objects.filter(
        action_id=action_id,
        status__in=UNFINISHED_STATUS,
        owner_id=owner.pk,
        owner_type=orm_object_to_core_type(owner).value,
    ).exists():
        raise AdcmEx(code="TASK_ERROR", msg=f"object {owner} already have this action (id={action_id}) running")


def _check_action_is_available_for_object(owner: ObjectWithAction, action: Action) -> None:
    if not action.allowed(obj=owner):
        raise AdcmEx(code="TASK_ERROR", msg="action is disabled")


def _process_run_config(
    action: Action, owner: ObjectWithAction, task: TaskLog, conf: dict, attr: dict, spec: dict, flat_spec: dict
) -> None:
    check_attr(action.prototype, action, attr, flat_spec)

    object_config = {}

    if owner.config is not None:
        object_config = ConfigLog.objects.get(id=owner.config.current).config

    process_variant(obj=owner, spec=spec, conf=object_config)
    check_config_spec(proto=action.prototype, obj=action, spec=spec, flat_spec=flat_spec, conf=conf, attr=attr)

    process_config_spec(obj=task, spec=spec, new_config=conf)


def check_hostcomponent_and_get_delta(
    bundle_id: BundleID,
    topology: ClusterTopology,
    hc_payload: Sequence[HostComponentEntry],
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
        delta = construct_delta_for_task(host_difference=host_difference)
        check_delta_is_allowed(delta=delta, rules=hc_rules, full_name_mapping=topology.component_full_name_id_mapping)
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
