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

from collections.abc import Iterable, Sequence
from typing import TypeAlias

from core.action import JobSpec, ScriptType, Task, TaskMappingDelta
from core.action.job import LaunchOptions, LogCreateDTO, TaskCreateDTO, TaskExtraInfo, TaskPayloadDTO
from core.action.job.errors import TaskCreateError
from core.legacy.cluster.operations import create_topology_with_new_mapping, find_hosts_difference
from core.legacy.cluster.types import ClusterTopology, HostComponentEntry
from core.templates import Template
from core.types import ActionID, ActionTargetDescriptor, BundleID, CoreObjectDescriptor, HostID
from django.conf import settings
from infra.services import get_config_service, get_wizard_service
from rest_framework.status import HTTP_409_CONFLICT
import core

from cm.converters import orm_object_to_action_target_type, orm_object_to_core_type
from cm.errors import AdcmEx
from cm.impl.job.repo import JobRepo
from cm.legacy.services.bundle import retrieve_bundle_restrictions
from cm.legacy.services.bundle_alt.render import ContextGatherer, Environment, TaskArgs, render_scripts
from cm.legacy.services.concern.checks import check_mapping_restrictions
from cm.legacy.services.job._utils import check_delta_is_allowed, construct_delta_for_task
from cm.legacy.services.job.jinja_scripts import get_job_specs_from_template
from cm.legacy.services.job.types import ActionHCRule
from cm.legacy.services.mapping import check_no_host_in_mm
from cm.models import (
    ADCM,
    Action,
    ActionHostGroup,
    Cluster,
    Component,
    ConcernType,
    Host,
    Process,
    Provider,
    Service,
)

ObjectWithAction: TypeAlias = ADCM | Cluster | Service | Component | Provider | Host
ActionTarget: TypeAlias = ObjectWithAction | ActionHostGroup


def prepare_task_for_action(
    target: ActionTargetDescriptor | CoreObjectDescriptor,
    orm_owner: ObjectWithAction,
    orm_target: ActionTarget,
    action: ActionID,
    payload: TaskPayloadDTO,
    delta: TaskMappingDelta | None = None,
    feature_scripts_jinja: bool = False,
) -> Task:
    """
    USED ONLY IN TESTS, WILL BE REMOVED
    """
    job_repo = JobRepo()
    action_repo = job_repo
    owner = CoreObjectDescriptor(id=orm_owner.pk, type=orm_object_to_core_type(orm_owner))
    orm_action = Action.objects.select_related("prototype").get(id=action)

    spec = None

    if not spec:
        if payload.conf:
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg="Absent config in action prototype")

    elif not payload.conf:
        raise AdcmEx("TASK_ERROR", "action config is required")

    action_info = action_repo.get_action(id=action)

    create_dto = TaskCreateDTO(
        owner=owner,
        target=target.as_core_or_group_descriptor if not isinstance(target, CoreObjectDescriptor) else target,
        action_id=action,
        launch=LaunchOptions(is_verbose=payload.verbose, is_blocking=payload.is_blocking),
        extra=TaskExtraInfo(
            name=orm_action.name, display_name=orm_action.display_name, description=orm_action.description
        ),
    )

    task_id = job_repo.create_task(payload=create_dto)
    task = job_repo.get_task(task_id)

    if payload.conf:
        raise NotImplementedError("Running an action with a configuration is no longer supported by this function.")

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
        if not isinstance(orm_target, Cluster | Service | Component | Host | ActionHostGroup):
            message = f"Can't render scripts for target of type {type(target)}"
            raise TypeError(message)

        if not isinstance(orm_owner, Cluster | Service | Component | Host):
            message = f"Can't render scripts for owner of type {type(orm_owner)}"
            raise TypeError(message)

        job_specifications = _render_scripts_from_template(
            template=action_info.scripts_template,
            action=orm_action,
            owner=orm_owner,
            target=orm_target,
            context_gatherer=ContextGatherer(config_service=get_config_service(), wizard_service=get_wizard_service()),
        )
    else:
        job_specifications = tuple(action_repo.get_job_specs(id=action))

    if not job_specifications:
        message = f"Can't compose task for action #{action}, because no associated jobs found"
        raise TaskCreateError(message)

    job_repo.create_jobs(task_id=task.id, scripts=job_specifications)

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
    owner: Cluster | Service | Component,
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
        owner_object=owner,
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
