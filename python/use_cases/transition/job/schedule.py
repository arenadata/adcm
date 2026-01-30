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
from typing import Iterable, NamedTuple, NewType, TypeAlias

from cm.converters import orm_object_to_action_target_type, orm_object_to_core_descriptor, orm_object_to_core_type
from cm.errors import AdcmEx
from cm.legacy.services import mapping
from cm.legacy.services.action_process.types import ProcessState
from cm.legacy.services.bundle import retrieve_bundle_restrictions
from cm.legacy.services.bundle_alt.errors import convert_bundle_errors_to_adcm_ex
from cm.legacy.services.bundle_alt.render import (
    ActionArgs,
    Environment,
    TaskArgs,
)
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.config.jinja import get_jinja_config
from cm.legacy.services.job._utils import check_delta_is_allowed, construct_delta_for_task
from cm.legacy.services.job.constants import HC_CONSTRAINT_VIOLATION_ON_UPGRADE_TEMPLATE
from cm.legacy.services.job.jinja_scripts import get_job_specs_from_template_new
from cm.legacy.services.job.run import start_task
from cm.legacy.services.job.types import ActionHCRule
from cm.legacy.status_api import send_task_status_update_event
from cm.models import (
    ADCM,
    UNFINISHED_STATUS,
    Action,
    ActionHostGroup,
    Cluster,
    Component,
    ConcernType,
    Host,
    JobStatus,
    Process,
    Provider,
    Service,
    TaskLog,
)
from core.dynamic_bundle.render import BundleRenderer
from core.dynamic_bundle.types import ContextGathererI
from core.legacy.cluster.operations import create_topology_with_new_mapping, find_hosts_difference
from core.legacy.cluster.types import ClusterTopology, HostComponentEntry
from core.legacy.job.types import (
    ScriptType,
    TaskMappingDelta,
)
from core.templates import parse_template
from core.types import (
    ActionID,
    ADCMHostGroupType,
    BundleID,
    CoreObjectDescriptor,
    Descriptor,
    HostGroupDescriptor,
    HostID,
)
from django.conf import settings
from django.db.transaction import atomic
from rbac.roles import re_apply_policy_for_jobs
from rest_framework.status import HTTP_409_CONFLICT
import core

from use_cases.dto import ConfigurationDTO, RunActionDTO

ObjectWithAction: TypeAlias = ADCM | Cluster | Service | Component | Provider | Host
ActionTarget: TypeAlias = ObjectWithAction | ActionHostGroup

UseNewScheduler = NewType("UseNewScheduler", bool)


class SpecPair(NamedTuple):
    spec: core.config.spec.FullSpec
    defaults: core.config.Defaults


class JobConfig(NamedTuple):
    configuration: core.config.Configuration
    specification: core.config.spec.FullSpec


@dataclass(slots=True)
class ScheduleTask:
    job_service: core.job.JobService
    config_service: core.config.ConfigService
    context_gatherer: ContextGathererI[ActionArgs, TaskArgs]
    bundle_renderer: BundleRenderer[ActionArgs, TaskArgs]
    use_new_scheduler: UseNewScheduler

    def do(self, *, action_orm: Action, target: ActionTarget, payload: RunActionDTO) -> TaskLog:
        action_objects = _ActionLaunchObjects(target=target, action=action_orm)

        is_upgrade_action = hasattr(action_orm, "upgrade")
        action_has_hc_acl = bool(action_orm.hostcomponentmap)

        if action_has_hc_acl and not action_objects.cluster:
            raise AdcmEx(code="TASK_ERROR", msg="Only cluster objects can have action with hostcomponentmap")

        # shouldn't be here, extract and check correctly
        if action_orm.wizard_template:
            if payload.process is None:
                raise AdcmEx(code="TASK_ERROR", msg="Process must be specified for this action")

            if not Process.objects.filter(
                id=payload.process.id,
                action=action_orm,
                target_id=target.pk,
                target_type=orm_object_to_action_target_type(target).value,
                state=ProcessState.COMPLETED,
            ).exists():
                raise AdcmEx(code="TASK_ERROR", msg="Process must be bound to action and be in completed state")

        with atomic():
            _check_no_target_conflict(target=action_objects.target, action=action_orm)
            _check_no_blocking_concerns(lock_owner=action_objects.object_to_lock, action_name=action_orm.name)
            _check_action_is_not_already_launched(owner=action_objects.object_to_lock, action_id=action_orm.pk)
            _check_action_is_available_for_object(owner=action_objects.owner, action=action_orm)

            descriptor = orm_object_to_core_descriptor(action_objects.owner)

            match action_objects.target:
                case ActionHostGroup():
                    target_descriptor = HostGroupDescriptor(id=action_objects.target.pk, type=ADCMHostGroupType.ACTION)
                case _:
                    target_descriptor = orm_object_to_core_descriptor(action_objects.target)

            task_extra = core.job.dto.TaskExtraInfo(
                name=action_orm.name, display_name=action_orm.display_name, description=payload.description
            )
            create_dto = core.job.dto.TaskCreateDTO(
                action_id=action_orm.pk,
                owner=descriptor,
                target=target_descriptor,
                launch=payload.launch,
                process=payload.process,
                extra=task_extra,
            )
            task_id = self.job_service.create_task(payload=create_dto)

            process_id = None if not payload.process else payload.process.id
            bundle_context = core.bundle.BundleContext(
                id=action_orm.prototype.bundle.id,
                root=settings.BUNDLE_DIR / action_orm.prototype.bundle.hash,
                contract_version=action_orm.prototype.bundle.contract_version,
            )

            job_config = None
            delta = None
            config_to_set = None

            match action_objects.owner:
                case Provider() | Host() | ADCM():
                    spec_pair = _retrieve_static_spec(action_id=action_orm.pk, config_service=self.config_service)
                    job_config = _prepare_configuration(
                        spec=spec_pair,
                        config=payload.configuration,
                        owner=descriptor,
                        config_service=self.config_service,
                    )

                case Cluster() | Service() | Component():
                    if isinstance(action_objects.target, Provider | ADCM):
                        message = f"Can't handle target {type(action_objects.target)} for cluster hierarchy action"
                        raise TypeError(message)

                    action_args = ActionArgs(
                        action=action_orm,
                        owner_object=action_objects.owner,
                        target_object=action_objects.target,
                        wizard_process_id=process_id,
                    )
                    spec_pair = _resolve_spec(
                        action=action_orm,
                        action_args=action_args,
                        bundle_context=bundle_context,
                        config_service=self.config_service,
                        bundle_renderer=self.bundle_renderer,
                    )
                    job_config = _prepare_configuration(
                        spec=spec_pair,
                        config=payload.configuration,
                        owner=descriptor,
                        config_service=self.config_service,
                    )

            if job_config:
                update_result = self.config_service.prepare_configuration_for_ansible(
                    configuration=job_config.configuration,
                    specification=job_config.specification,
                    file_owner=Descriptor(id=task_id, type="task"),
                )
                config_to_set = update_result.values
                self.config_service.prepare_file_parameter_values_on_fs(
                    configuration=job_config.configuration,
                    specification=job_config.specification,
                    owner_prefix=f"task.{task_id}",
                )

            match action_objects.owner:
                case Provider() | Host() | ADCM():
                    scripts = self.job_service.retrieve_scripts(action_id=action_orm.pk)

                case Cluster(id=cluster_id) | Service(cluster_id=cluster_id) | Component(cluster_id=cluster_id):
                    topology = retrieve_cluster_topology(cluster_id=cluster_id)

                    # it's actually an incorrect possibility for target, should be resolved earlier
                    if isinstance(action_objects.target, (ADCM, Provider)):
                        message = f"Can't render scripts for target of type {type(action_objects.target)}"
                        raise TypeError(message)

                    if action_has_hc_acl or is_upgrade_action:
                        delta = _check_hostcomponent_and_get_delta(
                            bundle_id=int(action_orm.prototype.bundle_id),
                            topology=topology,
                            hc_payload=payload.mapping or set(),
                            hc_rules=action_orm.hostcomponentmap,
                            mapping_restriction_err_template=HC_CONSTRAINT_VIOLATION_ON_UPGRADE_TEMPLATE
                            if is_upgrade_action
                            else "{}",
                        )

                    task_args = TaskArgs(
                        target_object=action_objects.target,
                        owner_object=action_objects.owner,
                        action=action_orm,
                        config=config_to_set or {},
                        verbose=payload.launch.is_verbose,
                        delta=delta,
                        wizard_process_id=process_id,
                    )
                    scripts = _resolve_scripts(
                        action=action_orm,
                        bundle_context=bundle_context,
                        task_args=task_args,
                        job_service=self.job_service,
                        context_gatherer=self.context_gatherer,
                        bundle_renderer=self.bundle_renderer,
                    )

                case _:
                    message = f"Unexpected owner: {action_objects.owner}"
                    raise RuntimeError(message)

            self.job_service.create_jobs(task_id=task_id, scripts=scripts)

            if config_to_set is not None or delta is not None:
                update_dto = core.job.dto.TaskUpdateMainFieldsDTO(configuration=config_to_set, mapping_delta=delta)
                self.job_service.set_task_mapping_and_configuration(task_id=task_id, payload=update_dto)

            orm_task = TaskLog.objects.get(id=task_id)
            re_apply_policy_for_jobs(action_object=action_objects.owner, task=orm_task)

        send_task_status_update_event(task_id=task_id, status=JobStatus.CREATED.value)

        if not self.use_new_scheduler:
            start_task(orm_task)

        return orm_task


# todo should be moved out of here, just a "simple" cover-up of most cornerstones
#      when we are working with action's configuration.
#      not even a use case.
@dataclass(slots=True)
class RetrieveConfigurationForAction:
    config_service: core.config.ConfigService
    bundle_renderer: BundleRenderer[ActionArgs, TaskArgs]

    def do(
        self, *, action_orm: Action, target: ActionTarget
    ) -> (
        tuple[core.config.spec.FullSpec, core.config.Defaults, core.config.Configuration, core.config.ConfigOwner]
        | None
    ):
        action_objects = _ActionLaunchObjects(target=target, action=action_orm)

        descriptor = orm_object_to_core_descriptor(action_objects.owner)

        match action_objects.owner:
            case Provider() | Host() | ADCM():
                spec_pair = _retrieve_static_spec(action_id=action_orm.pk, config_service=self.config_service)

            case Cluster() | Service() | Component():
                bundle_context = core.bundle.BundleContext(
                    id=action_orm.prototype.bundle.id,
                    root=settings.BUNDLE_DIR / action_orm.prototype.bundle.hash,
                    contract_version=action_orm.prototype.bundle.contract_version,
                )
                if isinstance(action_objects.target, Provider | ADCM):
                    message = f"Can't handle target {type(action_objects.target)} for cluster hierarchy action"
                    raise TypeError(message)

                action_args = ActionArgs(
                    action=action_orm,
                    owner_object=action_objects.owner,
                    target_object=action_objects.target,
                    wizard_process_id=None,
                )
                spec_pair = _resolve_spec(
                    action=action_orm,
                    action_args=action_args,
                    bundle_context=bundle_context,
                    config_service=self.config_service,
                    bundle_renderer=self.bundle_renderer,
                )

        if not spec_pair:
            return None

        configuration = self.config_service.prepare_default_configuration(
            defaults=spec_pair.defaults, specification=spec_pair.spec
        )

        return (
            spec_pair.spec,
            spec_pair.defaults,
            configuration,
            core.config.ConfigOwner(descriptor=descriptor, state=action_objects.owner.state),
        )


def _retrieve_static_spec(action_id: ActionID, config_service: core.config.ConfigService) -> SpecPair | None:
    try:
        specification, defaults = config_service.retrieve_specification_with_defaults_for_action(action_id=action_id)
        return SpecPair(spec=specification, defaults=defaults)
    except core.config.ObjectWithoutConfigError:
        return None


@convert_bundle_errors_to_adcm_ex
def _resolve_spec(
    action: Action,
    action_args: ActionArgs,
    bundle_context: core.bundle.BundleContext,
    config_service: core.config.ConfigService,
    bundle_renderer: BundleRenderer[ActionArgs, TaskArgs],
) -> SpecPair | None:
    if not (action.config_jinja or action.config_template):
        return _retrieve_static_spec(action_id=action.pk, config_service=config_service)

    if action.config_jinja:
        prototype_configs, _ = get_jinja_config(action=action, cluster_relative_object=action_args.owner_object)
        # todo rework, it shouldn't be imported in here, nor used "plainly" at all
        from cm.impl.config.repo import build_specification_from_prototype_config_records

        # todo raise error on empty spec?
        spec, defaults = build_specification_from_prototype_config_records(
            records=tuple(prototype_configs),
            group_customization_flag=False,
            secrets_service=config_service.secrets,
            bundle_root=bundle_context.root,
        )
        return SpecPair(spec=spec, defaults=defaults)

    template = parse_template(action.config_template)

    spec, defaults = bundle_renderer.render_config(template=template, args=action_args, bundle_context=bundle_context)

    return SpecPair(spec=spec, defaults=defaults)


def _prepare_configuration(
    spec: SpecPair | None,
    config: ConfigurationDTO | None,
    owner: CoreObjectDescriptor,
    config_service: core.config.ConfigService,
) -> JobConfig | None:
    match spec, config:
        case None, None:
            return None

        case SpecPair(spec=specification), ConfigurationDTO(convert=to_configuration, input_config=input_config):
            input_configuration = to_configuration(input_config, specification)

            try:
                owner_configuration = config_service.retrieve_current_configuration(owner=owner)
            except core.config.ObjectWithoutConfigError:
                owner_configuration = None

            configuration = config_service.prepare_action_configuration(
                configuration=input_configuration,
                specification=specification,
                owner=owner,
                owner_configuration=owner_configuration,
            )
            return JobConfig(configuration=configuration, specification=specification)

        case SpecPair(), _:
            raise AdcmEx(code="TASK_ERROR", msg="Configuration is expected for action, but missing")

        case _, ConfigurationDTO():
            raise AdcmEx(code="TASK_ERROR", msg="No configuration expected for action")


def _resolve_scripts(
    action: Action,
    bundle_context: core.bundle.BundleContext,
    task_args: TaskArgs,
    job_service: core.job.JobService,
    context_gatherer: ContextGathererI[ActionArgs, TaskArgs],
    bundle_renderer: BundleRenderer[ActionArgs, TaskArgs],
) -> tuple[core.action.JobSpec, ...]:
    if not (action.scripts_jinja or action.scripts_template):
        return job_service.retrieve_scripts(action_id=action.pk)

    if action.scripts_jinja:
        script_generator = get_job_specs_from_template_new(
            jinja_path=action.scripts_jinja,
            allow_to_terminate=action.allow_to_terminate,
            environment=Environment(bundle_root=bundle_context.root),
            task_args=task_args,
            context_gatherer=context_gatherer,
        )

        scripts = tuple(script_generator)
        if any(script.script_type == ScriptType.INTERNAL and script.script == "config_apply" for script in scripts):
            message = "Internal script 'config_apply' can't be used for jinja action"
            raise AdcmEx(code="INTERNAL_SERVER_ERROR", msg=message)

        return scripts

    template = parse_template(action.scripts_template)
    scripts = bundle_renderer.render_scripts_for_action(
        template=template,
        args=task_args,
        bundle_context=bundle_context,
        action_allow_to_terminate=action.allow_to_terminate,
    )
    return tuple(scripts)


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
        self.object_to_lock = self.target  # pyright: ignore [reportAttributeAccessIssue]

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
                case "cluster" if self.cluster:
                    self.owner = self.cluster
                case _:
                    message = f"Can't handle {action.prototype.type} type for owner of host action detection"
                    raise NotImplementedError(message)
        elif isinstance(target, ActionHostGroup):
            # action group support only objects in Cluster hierarchy,
            # so we can safely assume that there is related cluster
            self.owner = target.object  # pyright: ignore
            self.cluster = self.owner if isinstance(self.owner, Cluster) else self.owner.cluster  # pyright: ignore
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
        object_locks = object_locks.exclude(owner_id=lock_owner.pk, owner_type=lock_owner.content_type)

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


def _check_hostcomponent_and_get_delta(
    bundle_id: BundleID,
    topology: ClusterTopology,
    hc_payload: set[HostComponentEntry] | list[HostComponentEntry],
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
    host_difference = find_hosts_difference(new_topology=new_topology, old_topology=topology)
    mapping.check_for_action_mapping(  # TODO: put checks above and below to this use case
        bundle_restrictions=bundle_restrictions,
        new_topology=new_topology,
        host_difference=host_difference,
        err_template=mapping_restriction_err_template,
    )
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
