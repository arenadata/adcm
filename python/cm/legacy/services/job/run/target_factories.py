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

from collections import defaultdict
from collections.abc import Generator, Iterable, Sequence
from configparser import ConfigParser
from dataclasses import asdict
from functools import partial
from logging import getLogger
from pathlib import Path
from typing import Any, Literal
import json
import traceback

from core.action import (
    AnsibleJob,
    AssociatedProcess,
    ConfigApplyChangeEntry,
    ConfigApplyJob,
    HcAclRule,
    HcApplyJob,
    HostGroupManageJob,
    HostGroupReference,
    HostManageJob,
    Job,
    ScriptType,
    ServiceManageJob,
    ServiceManageServiceEntry,
    SimpleInternalJob,
    TargetCluster,
    Task,
    TaskMappingDelta,
)
from core.action.job import TaskUpdateDTO
from core.cluster import ClusterService
from core.config import ConfigService
from core.legacy.cluster.types import ClusterTopology
from core.legacy.job.executors import ExecutorConfig
from core.legacy.job.runners import ExecutionTarget, ExecutionTargetFactoryI, ExternalSettings
from core.logs import LogsService
from core.scenarios.cluster import BeforeUpgradeScenarios
from core.scenarios.config import ConfigScenarios
from core.types import ADCMCoreType, ClusterID, ComponentNameKey, HostID, ObjectID
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.db.transaction import atomic
from rbac.roles import re_apply_policy_for_jobs
from rbac.scenarios import RBACScenarios
from use_cases.cluster.update import ResetBeforeUpgradeCluster
from use_cases.provider.update import ResetBeforeUpgradeProvider
from use_cases.transition.config import (
    UpdateConfigurationFromJob,
    UpdateHostGroupConfigurationFromJob,
    apply_config_changes,
    apply_config_changes_to_host_group,
)
from use_cases.transition.host_group import (
    GroupAddress,
    GroupOutcome,
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
from use_cases.transition.service_manage import ManageClusterServices
import core

from cm.converters import CoreObject, core_type_to_model
from cm.errors import AdcmEx
from cm.impl.job.repo import JobRepo
from cm.legacy.services.action_process.types import ProcessStepState
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.config import ConfigAttrPair
from cm.legacy.services.job import context as context_m
from cm.legacy.services.job.run.executors import (
    AnsibleExecutorConfig,
    AnsibleProcessExecutor,
    InternalExecutor,
    InternalScriptResult,
    PythonExecutorConfig,
    PythonProcessExecutor,
)
from cm.legacy.services.job.types import (
    ADCMJobConfig,
    ClusterActionType,
    ComponentActionType,
    HostActionType,
    JobConfig,
    JobData,
    JobEnv,
    ProviderActionType,
    ServiceActionType,
)
from cm.legacy.services.mapping import change_host_component_mapping_no_lock, check_nothing, lock_cluster_mapping
from cm.legacy.status_api import send_prototype_and_state_update_event
from cm.legacy.utils import deep_merge
from cm.models import (
    ADCM,
    AnsibleConfig,
    Cluster,
    Component,
    ConfigHostGroup,
    LogStorage,
    Process,
    Prototype,
    TaskLog,
)
from cm.transition.status import StatusScenarios

logger = getLogger("adcm")


class ExecutionTargetFactory(ExecutionTargetFactoryI):
    def __init__(
        self,
        logs_service: LogsService,
        reset_cluster_before_upgrade: ResetBeforeUpgradeCluster,
        reset_provider_before_upgrade: ResetBeforeUpgradeProvider,
        update_configuration_from_job: UpdateConfigurationFromJob,
        manage_services: ManageClusterServices,
        cluster_service: ClusterService,
        rbac_scenarios: RBACScenarios,
        config_scenarios: ConfigScenarios,
        before_upgrade_scenarios: BeforeUpgradeScenarios,
        config_service: ConfigService,
        status_scenarios: StatusScenarios,
        update_host_group_configuration: UpdateHostGroupConfigurationFromJob,
    ):
        self._default_ansible_finalizers = (lambda job: logs_service.finish_updating_check_logs_for_job(job_id=job.id),)
        self._rbac_scenarios = rbac_scenarios
        # Reaching into `config_scenarios` for its `config_service` is just simpler than adding another
        # constructor dependency right now; `config_service` should become its own injected dependency.
        self._config_service = config_scenarios.config_service
        self._supported_internal_scripts = {
            "bundle_switch": partial(
                internal_script_bundle_switch,
                rbac_scenarios=rbac_scenarios,
                config_scenarios=config_scenarios,
                cluster_service=cluster_service,
            ),
            "bundle_revert": partial(
                internal_script_bundle_revert,
                rbac_scenarios=rbac_scenarios,
                config_scenarios=config_scenarios,
                cluster_service=cluster_service,
                before_upgrade_scenarios=before_upgrade_scenarios,
            ),
            "hc_apply": partial(internal_script_hc_apply, cluster_service=cluster_service),
            "config_apply": partial(
                internal_script_config_apply,
                update_configuration_from_job=update_configuration_from_job,
            ),
            "service_manage": partial(internal_script_service_manage, manage_services=manage_services),
            "before_upgrade_clean": partial(
                internal_script_before_upgrade_clean,
                cluster_uc=reset_cluster_before_upgrade,
                provider_uc=reset_provider_before_upgrade,
            ),
            "host_manage": partial(
                internal_script_host_manage,
                config_service=config_service,
                rbac_scenarios=rbac_scenarios,
                status_scenarios=status_scenarios,
                cluster_service=cluster_service,
            ),
            "host_group_manage": partial(
                internal_script_host_group_manage,
                rbac_scenarios=rbac_scenarios,
                config_service=config_service,
                update_host_group_configuration=update_host_group_configuration,
            ),
        }

    def __call__(
        self, task: Task, jobs: Iterable[Job], configuration: ExternalSettings
    ) -> Generator[ExecutionTarget, None, None]:
        for job_info in jobs:
            work_dir = configuration.adcm.run_dir / str(job_info.id)
            finalizers = (
                partial(save_fs_logs_to_db, work_dir=work_dir, log_type="stderr"),
                partial(save_fs_logs_to_db, work_dir=work_dir, log_type="stdout"),
            )
            match job_info.type:
                case ScriptType.ANSIBLE:
                    executor = AnsibleProcessExecutor(
                        config=AnsibleExecutorConfig(
                            job_script=job_info.script,
                            work_dir=work_dir,
                            bundle=task.bundle,
                            tags=job_info.params.ansible_tags,
                            verbose=task.verbose,
                            venv=task.action.venv,
                            ansible_secret_script=configuration.ansible.ansible_secret_script,
                        )
                    )
                    finalizers = (*self._default_ansible_finalizers, *finalizers)
                    environment_builders = (partial(prepare_ansible_environment, config_service=self._config_service),)
                case ScriptType.PYTHON:
                    executor = PythonProcessExecutor(
                        config=PythonExecutorConfig(
                            job_script=job_info.script,
                            work_dir=work_dir,
                            bundle=task.bundle,
                            venv=task.action.venv,
                        )
                    )
                    environment_builders = ()
                case ScriptType.INTERNAL:
                    internal_script_func = self._supported_internal_scripts.get(job_info.script)
                    if not internal_script_func:
                        message = f"Unknown internal script {job_info.type}, can't build runner for it"
                        raise NotImplementedError(message)

                    script = partial(internal_script_func, task=task, job=job_info)
                    executor = InternalExecutor(config=ExecutorConfig(work_dir=work_dir), script=script)
                    environment_builders = ()
                case _:
                    message = f"Can't convert job of type {job_info.type}"
                    raise NotImplementedError(message)

            yield ExecutionTarget(
                job=job_info, executor=executor, environment_builders=environment_builders, finalizers=finalizers
            )


# INTERNAL SCRIPTS


@atomic()
def internal_script_bundle_switch(
    task: Task,
    job: SimpleInternalJob,
    rbac_scenarios: RBACScenarios,
    config_scenarios: ConfigScenarios,
    cluster_service: ClusterService,
) -> InternalScriptResult:
    _ = job

    task_ = TaskLog.objects.get(id=task.id)

    from use_cases.legacy.upgrade import build_switch_revert_callbacks

    from cm.legacy.bundle_switch_revert import bundle_switch

    # Reaching into `config_scenarios` for its `config_service` is just simpler than adding another
    # constructor dependency right now; `config_service` should become its own injected dependency.
    config_service = config_scenarios.config_service
    callbacks = build_switch_revert_callbacks(
        config_service=config_service,
        rbac_scenarios=rbac_scenarios,
        cluster_service=cluster_service,
    )
    bundle_switch(
        obj=task_.task_object,
        upgrade=task_.action.upgrade,
        callbacks=callbacks,
        config_service=config_service,
        config_scenarios=config_scenarios,
    )

    _switch_hc_if_required(task=task)

    re_apply_policy_for_jobs(task=task_)

    result_message = _build_result_message(
        script_name="bundle_switch",
        full_complete_message="the prototype is switched",
        with_updates=True,
    )
    return InternalScriptResult(code=0, message=result_message)


@atomic()
def internal_script_bundle_revert(
    task: Task,
    job: SimpleInternalJob,
    rbac_scenarios: RBACScenarios,
    config_scenarios: ConfigScenarios,
    cluster_service: ClusterService,
    before_upgrade_scenarios: BeforeUpgradeScenarios,
) -> InternalScriptResult:
    _ = job

    task_ = TaskLog.objects.get(id=task.id)

    try:
        from use_cases.legacy.upgrade import build_switch_revert_callbacks

        from cm.legacy.bundle_switch_revert import bundle_revert

        # Reaching into `config_scenarios` for its `config_service` is just simpler than adding another
        # constructor dependency right now; `config_service` should become its own injected dependency.
        config_service = config_scenarios.config_service
        callbacks = build_switch_revert_callbacks(
            config_service=config_service,
            rbac_scenarios=rbac_scenarios,
            cluster_service=cluster_service,
        )

        bundle_revert(
            obj=task_.task_object,
            callbacks=callbacks,
            cluster_service=cluster_service,
            config_service=config_service,
            config_scenarios=config_scenarios,
            before_upgrade_scenarios=before_upgrade_scenarios,
        )

    except ObjectDoesNotExist as error:
        # This is a hack. We can do this, since all AdcmEx are intercepted in the Executer,
        # and a message is generated in the log there.
        raise AdcmEx(
            code="INTERNAL_SERVER_ERROR",
            msg=f"The configuration cannot be restored because the record was deleted.\n\n{traceback.format_exc()}",
        ) from error
    finally:
        send_prototype_and_state_update_event(object_=task_.task_object)

    _switch_hc_if_required(task=task)

    re_apply_policy_for_jobs(task=task_)

    result_message = _build_result_message(
        script_name="bundle_revert",
        full_complete_message="prototype reverted",
        with_updates=True,
    )
    return InternalScriptResult(code=0, message=result_message)


def internal_script_hc_apply(task: Task, job: HcApplyJob, cluster_service: ClusterService) -> InternalScriptResult:
    if task.owner and task.owner.type not in {ADCMCoreType.CLUSTER, ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT}:
        raise AdcmEx(
            code="WRONG_OWNER",
            msg="Internal script `hc_apply` can only be defined in cluster, service or component context`",
        )

    hc_apply_rules = job.params.rules if job.params else None

    if not hc_apply_rules:
        hc_apply_rules = task.action.hc_acl

    if task.owner.type == ADCMCoreType.CLUSTER:
        cluster_id = task.owner.id
        cluster_prototype_id = task.owner.prototype_id
    else:
        cluster_id = task.owner.related_objects.cluster.id
        cluster_prototype_id = task.owner.related_objects.cluster.prototype_id

    bundle_id = Prototype.objects.values_list("bundle_id", flat=True).get(id=cluster_prototype_id)

    with_updates = False
    with atomic():
        lock_cluster_mapping(cluster_id=cluster_id)

        if (
            isinstance(task.action_process, AssociatedProcess)
            and (process := Process.objects.filter(id=task.action_process.id)).exists()
        ):
            mapping_delta = _extract_hc_apply_delta_for_process(process.first())
            #  hc rule for process are validated during step submissions hence cumulative delta is valid
            delta_part = mapping_delta
        else:
            mapping_delta = task.hostcomponent.mapping_delta
            delta_part = _extract_mapping_delta_part(
                cluster_id=cluster_id, mapping_delta=mapping_delta, hc_apply_rules=hc_apply_rules
            )

        with_updates = not delta_part.is_empty
        if with_updates:
            change_host_component_mapping_no_lock(
                cluster_id=cluster_id,
                bundle_id=bundle_id,
                mapping_delta=delta_part,
                cluster_service=cluster_service,
                checks_func=check_nothing,
            )

    result_message = _build_result_message(
        script_name="hc_apply",
        full_complete_message="the component mapping is complete",
        without_updates_message="the component mapping was done",
        with_updates=with_updates,
    )
    return InternalScriptResult(code=0, message=result_message)


def internal_script_config_apply(
    task: Task,
    job: ConfigApplyJob,
    update_configuration_from_job: UpdateConfigurationFromJob,
) -> InternalScriptResult:
    with_updates = False
    # are we going to allow to change one component from context of another?
    for change in job.params.changes:
        changing_object = _extract_apply_config_target(task=task, change=change)
        has_changed = apply_config_changes(
            job_id=job.id,
            db_object=changing_object,
            parameters=[asdict(parameter) for parameter in change.parameters],
            changes_description=f"{task.display_name} process update",
            update_configuration_from_job=update_configuration_from_job,
        )
        # if at least one change has been applied, the script is marked as completed with updates
        with_updates = has_changed or with_updates

    result_message = _build_result_message(
        script_name="config_apply",
        full_complete_message="the configuration updates are done",
        without_updates_message="the configuration was updated",
        with_updates=with_updates,
    )
    return InternalScriptResult(code=0, message=result_message)


def internal_script_service_manage(
    task: Task,
    job: ServiceManageJob,
    manage_services: ManageClusterServices,
) -> InternalScriptResult:
    cluster_id, entries = _parse_service_manage_arguments(task=task, job=job)

    outcome = manage_services.add(
        cluster_id=cluster_id,
        entries=entries,
        job_id=job.id,
        task_owner=task.owner,
        changes_description=f"{task.display_name} process update",
    )

    result_message = _build_result_message(
        script_name="service_manage",
        full_complete_message=f"services are in place: {', '.join(entry.name for entry in entries)}",
        without_updates_message="the requested services were already in place",
        with_updates=outcome.with_updates,
    )
    return InternalScriptResult(code=0, message=result_message)


def _parse_service_manage_arguments(
    task: Task, job: ServiceManageJob
) -> tuple[ClusterID, tuple[ServiceManageServiceEntry, ...]]:
    if task.owner is None:
        raise RuntimeError("misconfigured task runner: no owner")

    cluster_id = task.owner.id if task.owner.type == ADCMCoreType.CLUSTER else task.owner.related_objects.cluster.id

    return cluster_id, tuple(job.params.services or ())


def internal_script_before_upgrade_clean(
    task: Task,
    job: SimpleInternalJob,
    cluster_uc: ResetBeforeUpgradeCluster,
    provider_uc: ResetBeforeUpgradeProvider,
) -> InternalScriptResult:
    _ = job

    if not task.owner:
        raise RuntimeError("misconfigured task runner: no owner")

    descriptor = task.owner.as_descriptor

    match descriptor.type:
        case ADCMCoreType.CLUSTER | ADCMCoreType.SERVICE | ADCMCoreType.COMPONENT if task.owner.related_objects:
            if descriptor.type == ADCMCoreType.CLUSTER:
                cluster_id = descriptor.id
            else:
                if not task.owner.related_objects.cluster:
                    raise RuntimeError("cluster is missing")

                cluster_id = task.owner.related_objects.cluster.id

            cluster_uc.do(target=descriptor, cluster_id=cluster_id)

        case ADCMCoreType.PROVIDER | ADCMCoreType.HOST:
            provider_uc.do(target=descriptor)

        case _:
            raise RuntimeError("misconfigured task runner")

    result_message = _build_result_message(
        script_name="before_upgrade_clean",
        full_complete_message='"before_upgrade" section has been cleared',
        with_updates=True,
    )
    return InternalScriptResult(code=0, message=result_message)


def internal_script_host_manage(
    task: Task,
    job: HostManageJob,
    config_service: ConfigService,
    rbac_scenarios: RBACScenarios,
    status_scenarios: StatusScenarios,
    cluster_service: ClusterService,
) -> InternalScriptResult:
    script_name = "host_manage"
    cluster_id = _cluster_id_of_task_owner(task=task, script_name=script_name)
    params = job.params

    context = SelectionContext(cluster_id=cluster_id, provider_id=_provider_id_of_task(task=task))

    with atomic():
        selected = resolve_source(source=params.source, context=context)

        match params.operation:
            case "add_duplicates":
                return _host_manage_add_duplicates(
                    task=task,
                    job=job,
                    selected=selected,
                    cluster_id=cluster_id,
                    config_service=config_service,
                    rbac_scenarios=rbac_scenarios,
                    status_scenarios=status_scenarios,
                )

            case "add_to_groups":
                added, removed = _apply_group_membership(
                    task=task,
                    references=params.groups or (),
                    host_ids=duplicates_here(host_ids=selected, cluster_id=cluster_id),
                    cluster_id=cluster_id,
                    script_name=script_name,
                )

                return InternalScriptResult(
                    code=0,
                    message=_build_result_message(
                        script_name=script_name,
                        full_complete_message=f"the hosts are in their groups ({added} membership(s) added)",
                        without_updates_message="the hosts were added to their groups",
                        with_updates=bool(added or removed),
                    ),
                )

            case _:
                return _host_manage_remove_duplicates(
                    task=task,
                    selected=selected,
                    cluster_id=cluster_id,
                    cluster_service=cluster_service,
                    rbac_scenarios=rbac_scenarios,
                )


def _host_manage_add_duplicates(
    task: Task,
    job: HostManageJob,
    selected: list[HostID],
    cluster_id: ClusterID,
    config_service: ConfigService,
    rbac_scenarios: RBACScenarios,
    status_scenarios: StatusScenarios,
) -> InternalScriptResult:
    script_name = "host_manage"
    params = job.params

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
        config_service=config_service,
        rbac_scenarios=rbac_scenarios,
        status_scenarios=status_scenarios,
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
            JobRepo().update_task(id=task.id, data=TaskUpdateDTO(hostcomponentmap=delta))

    added, _ = _apply_group_membership(
        task=task,
        references=params.groups or (),
        host_ids=set(outcome.here),
        cluster_id=cluster_id,
        script_name=script_name,
    )

    details = [f"{outcome.created_count} created", f"{outcome.existing_count} already here"]
    if mapped:
        details.append(f"{sum(mapped.values())} mapping change(s) prepared")
    if added:
        details.append(f"{added} group membership(s) added")

    return InternalScriptResult(
        code=0,
        message=_build_result_message(
            script_name=script_name,
            full_complete_message=f"the selected hosts are duplicated here ({', '.join(details)})",
            without_updates_message="the hosts were duplicated",
            with_updates=bool(outcome.created_count or mapped or added),
        ),
    )


def _host_manage_remove_duplicates(
    task: Task,
    selected: list[HostID],
    cluster_id: ClusterID,
    cluster_service: ClusterService,
    rbac_scenarios: RBACScenarios,
) -> InternalScriptResult:
    outcome = remove_duplicates(
        source_host_ids=selected,
        here=cluster_id,
        cluster_service=cluster_service,
        rbac_scenarios=rbac_scenarios,
    )

    # The delta is applied once more when the task finishes; a host deleted here must not be
    # left in it, or that final application fails on a host the cluster no longer has.
    delta = task.hostcomponent.mapping_delta
    if delta is not None and outcome.removed_ids and forget_hosts_in_delta(delta=delta, host_ids=outcome.removed_ids):
        JobRepo().update_task(id=task.id, data=TaskUpdateDTO(hostcomponentmap=delta))

    return InternalScriptResult(
        code=0,
        message=_build_result_message(
            script_name="host_manage",
            full_complete_message=f"the duplicates of the selected hosts are gone ({len(outcome.removed)} deleted)",
            without_updates_message="the duplicates were removed",
            with_updates=bool(outcome.removed),
        ),
    )


def internal_script_host_group_manage(
    task: Task,
    job: HostGroupManageJob,
    rbac_scenarios: RBACScenarios,
    config_service: ConfigService,
    update_host_group_configuration: UpdateHostGroupConfigurationFromJob,
) -> InternalScriptResult:
    script_name = "host_group_manage"
    cluster_id = _cluster_id_of_task_owner(task=task, script_name=script_name, required=False)
    params = job.params

    owners = resolve_object_targets(
        targets={entry.object for entry in params.groups},
        context=ObjectContext(cluster_id=cluster_id, provider_id=_provider_id_of_task(task=task)),
        addressed_by=f"`{script_name}`",
    )
    addresses = {
        id(entry): GroupAddress(kind=entry.type, owner=owners[entry.object], name=entry.name) for entry in params.groups
    }

    with atomic():
        if params.operation == "remove":
            removed = remove_groups(addresses=set(addresses.values()))

            return InternalScriptResult(
                code=0,
                message=_build_result_message(
                    script_name=script_name,
                    full_complete_message=f"the named host groups are gone ({len(removed)} removed)",
                    without_updates_message="the groups were removed",
                    with_updates=bool(removed),
                ),
            )

        outcome = GroupOutcome()
        existing = retrieve_groups(addresses=set(addresses.values()))
        membership = retrieve_group_hosts(groups=existing.values())

        groups_of_entry = {}
        owners_of_new_groups = []

        for entry in params.groups:
            address = addresses[id(entry)]
            group = existing.get(address)

            if group is None:
                group = create_group(
                    address=address, description=entry.description or "", config_service=config_service
                )
                owners_of_new_groups.append(address.owner if isinstance(group, ConfigHostGroup) else None)
                outcome.created.append(str(address))
            elif set_description(group=group, description=entry.description or ""):
                outcome.updated.append(str(address))

            groups_of_entry[id(entry)] = group

        # A configuration group carries its own object permissions, so the owner's policies have
        # to be re-applied once a group exists - once for the whole batch, because doing it per
        # group repeats work whose cost grows with everything the policy covers.
        for owner in {owner for owner in owners_of_new_groups if owner is not None}:
            rbac_scenarios.re_apply_object_policy(apply_object=owner)

        # Removals for every group first, then additions: a host belongs to at most one
        # configuration group of an owner, so moving one between two groups of the same owner
        # only works if it has left the first before it is offered to the second.
        wanted_of_entry = {}
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
            changed = apply_config_changes_to_host_group(
                db_object=address.owner,
                group=groups_of_entry[id(entry)],
                parameters=[asdict(parameter) for parameter in entry.parameters],
                changes_description=f"{task.display_name} process update",
                update_configuration=update_host_group_configuration,
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
        message=_build_result_message(
            script_name=script_name,
            full_complete_message=f"the named host groups are in place ({', '.join(details)})",
            without_updates_message="the groups were set up",
            with_updates=outcome.with_updates,
        ),
    )


def _cluster_id_of_task_owner(task: Task, script_name: str, required: bool = True) -> ClusterID | None:
    if task.owner is None:
        raise AdcmEx(
            code="WRONG_OWNER",
            msg=f"Internal script `{script_name}` can't run in a task without an owner",
        )

    if task.owner.type == ADCMCoreType.CLUSTER:
        return task.owner.id

    if task.owner.type in {ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT}:
        return task.owner.related_objects.cluster.id

    if required:
        raise AdcmEx(
            code="WRONG_OWNER",
            msg=f"Internal script `{script_name}` can only be defined in cluster, service or component context",
        )

    return None


def _provider_id_of_task(task: Task) -> ObjectID | None:
    if task.owner is None:
        return None

    if task.owner.type == ADCMCoreType.PROVIDER:
        return task.owner.id

    provider = task.owner.related_objects.provider
    return provider.id if provider else None


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

    return task.hostcomponent.mapping_delta


def _apply_group_membership(
    task: Task,
    references: Sequence[HostGroupReference],
    host_ids: set[HostID],
    cluster_id: ClusterID,
    script_name: str,
) -> tuple[int, int]:
    """Add the given hosts to every named group. The groups must already exist."""

    if not references or not host_ids:
        return 0, 0

    default_owner = core_type_to_model(core_type=task.owner.type).objects.get(pk=task.owner.id)

    explicit = {reference.object for reference in references if reference.object is not None}
    owners = resolve_object_targets(
        targets=explicit,
        context=ObjectContext(cluster_id=cluster_id, provider_id=_provider_id_of_task(task=task)),
        addressed_by=f"`{script_name}` `groups`",
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
            msg=f"`{script_name}` puts hosts into {', '.join(missing)}, which does not exist. "
            "Create it with `host_group_manage` first - this script only manages membership.",
        )

    membership = retrieve_group_hosts(groups=existing.values())

    added = 0
    # deduplicated: two references naming the same group would otherwise be handed the same
    # "already held" set twice and try to insert the same membership rows again
    for address in sorted(set(addresses), key=str):
        group = existing[address]
        added += add_hosts(group=group, wanted=host_ids, held=membership.get(group_key(group), set()))

    return added, 0


def _build_result_message(
    script_name: str,
    full_complete_message: str,
    with_updates: bool,
    without_updates_message: str | None = None,
) -> str:
    base_template = "The script `{script_name}` completed successfully, {completed_info}."

    if with_updates or without_updates_message is None:
        complete_info = full_complete_message
    else:
        complete_info = f"but {without_updates_message} earlier"

    return base_template.format(script_name=script_name, completed_info=complete_info)


def _extract_hc_apply_delta_for_process(process: Process) -> TaskMappingDelta:
    last_mapping_step = (
        process.steps.filter(state=ProcessStepState.COMPLETED)
        .exclude(Q(processstepinput__mapping__isnull=True) | Q(processstepinput__mapping={}))
        .order_by("-id")
        .first()
    )

    if not last_mapping_step:
        return TaskMappingDelta(add={}, remove={})

    cumulative_delta = last_mapping_step.processstepinput.mapping["cumulative_delta"]

    add_mapping: dict[int, set[int]] = {}
    for entry in cumulative_delta.get("add", []):
        add_mapping.setdefault(entry["component_id"], set()).add(entry["host_id"])

    remove_mapping: dict[int, set[int]] = {}
    for entry in cumulative_delta.get("remove", []):
        remove_mapping.setdefault(entry["component_id"], set()).add(entry["host_id"])

    return TaskMappingDelta(add=add_mapping, remove=remove_mapping)


def _prepare_changes(parameters: list[dict], spec: dict) -> ConfigAttrPair:
    changes = ConfigAttrPair(config={}, attr={})

    for parameter in parameters:
        key = parameter["key"]
        value = parameter.get("value")

        if "/" not in key:
            key = f"{key}/"

        param_spec = spec.get(key)
        if not param_spec:
            continue

        if param_spec.type == "group" and param_spec.limits["activatable"]:
            if not isinstance(value, bool):
                raise AdcmEx(code="INTERNAL_SERVER_ERROR", msg=f"Value for {key} expected to be boolean")
            changes.attr[key] = {"active": bool(value)}
        else:
            changes.config[key] = value

    return changes


def _extract_apply_config_target(task: Task, change: ConfigApplyChangeEntry) -> ADCM | CoreObject:
    # in order to preserve single mechanism with adcm_config plugin.
    # Requires refactoring to move it common location with plugins
    from ansible_plugin.base import CoreObjectTargetDescription, VarsContextSection, _from_target_description
    from ansible_plugin.errors import PluginTargetDetectionError

    context = VarsContextSection(**context_m.get_run_context(task=task))
    target_description = CoreObjectTargetDescription(**asdict(change.object))

    try:
        target = _from_target_description(target_description, context)
    except PluginTargetDetectionError as e:
        raise AdcmEx(
            code="INTERNAL_SERVER_ERROR",
            msg=f"The configuration contains non-existing object of owner {change['object']}",
        ) from e

    return core_type_to_model(core_type=target.type).objects.get(pk=target.id)


def _extract_mapping_delta_part(
    cluster_id: ClusterID, mapping_delta: TaskMappingDelta, hc_apply_rules: list[HcAclRule]
) -> TaskMappingDelta:
    topology = retrieve_cluster_topology(cluster_id=cluster_id)
    components_map = topology.component_full_name_id_mapping

    delta_data = defaultdict(lambda: defaultdict(set))
    for hc_rule in hc_apply_rules:
        component_id = components_map.get(ComponentNameKey(service=hc_rule.service, component=hc_rule.component))
        if component_id is None:
            continue
        delta_data[hc_rule.action][component_id].update(
            getattr(mapping_delta, hc_rule.action, {}).get(component_id, ())
        )

    return TaskMappingDelta(**delta_data)


def _switch_hc_if_required(task: Task) -> None:
    """
    Should be performed during upgrade of cluster, if not cluster, no need in HC update.
    Because it's upgrade, it will be called either on cluster or provider,
    so task object will be one of those too.
    """

    if not task.hostcomponent.post_upgrade:
        return

    if task.target.type != ADCMCoreType.CLUSTER:
        return

    delta = task.hostcomponent.mapping_delta

    # `post_upgrade_hc_map` contains records with "component_prototype_id" which are "extra" to regular hc
    for new_entry in task.hostcomponent.post_upgrade:
        if "component_prototype_id" in new_entry:
            # if optimized to 1 request, it's probably good to filter by prototype__type="component"
            component_id = Component.objects.values_list("id", flat=True).get(
                cluster_id=task.target.id, prototype_id=new_entry["component_prototype_id"]
            )
            if component_id not in delta.add:
                delta.add[component_id] = {new_entry["host_id"]}
            else:
                delta.add[component_id].add(new_entry["host_id"])

    JobRepo().update_task(id=task.id, data=TaskUpdateDTO(post_upgrade_hc_map=None, hostcomponentmap=delta))


# ENVIRONMENT BUILDERS


def prepare_ansible_environment(
    task: Task,
    job: AnsibleJob,
    configuration: ExternalSettings,
    cluster_service: ClusterService,
    config_service: core.config.ConfigService,
) -> None:
    cluster_id, topology = None, None
    if task.owner:
        if task.owner.type == ADCMCoreType.CLUSTER:
            cluster_id = task.owner.id
        elif task.owner.related_objects.cluster is not None:
            cluster_id = task.owner.related_objects.cluster.id

    if cluster_id:
        topology = retrieve_cluster_topology(cluster_id)

    job_config = prepare_ansible_job_config(
        task=task, job=job, configuration=configuration, config_service=config_service, topology=topology
    )
    job_run_dir = configuration.adcm.run_dir / str(job.id)

    with (job_run_dir / "config.json").open(mode="w", encoding="utf-8") as config_file:
        json.dump(obj=job_config, fp=config_file, sort_keys=True, separators=(",", ":"))

    inventory = prepare_ansible_inventory(
        task=task, topology=topology, cluster_service=cluster_service, config_service=config_service
    )
    with (job_run_dir / "inventory.json").open(mode="w", encoding="utf-8") as file_descriptor:
        json.dump(obj=inventory, fp=file_descriptor, separators=(",", ":"))

    ansible_cfg_config_parser: ConfigParser = prepare_ansible_cfg(task=task)
    with (job_run_dir / "ansible.cfg").open(mode="w", encoding="utf-8") as config_file:
        ansible_cfg_config_parser.write(config_file)


def prepare_ansible_inventory(
    task: Task,
    cluster_service: ClusterService,
    config_service: core.config.ConfigService,
    topology: ClusterTopology | None = None,
) -> dict[str, Any]:
    delta, process_context, process_mapping_delta = None, None, {}

    # `host_manage` writes a mapping delta of its own, and an action that uses it does not have
    # to declare `hc_acl`: the `.add` and `.remove` groups the delta puts in this inventory are
    # how the job after it finds the hosts it has to work on.
    if task.action.hc_acl or task.hostcomponent.mapping_delta is not None:
        delta = task.hostcomponent.mapping_delta

    if task.action_process and topology:
        process = Process.objects.get(id=task.action_process.id)
        process_context = context_m.get_action_process_context(process, topology, config_service=config_service)
        process_mapping_delta = process_context.cumulative_delta

    return context_m.get_inventory_data(
        target=task.target,
        is_host_action=task.action.is_host_action,
        delta=delta,
        related_objects=task.owner.related_objects,
        process_mapping_delta=process_mapping_delta,
        cluster_service=cluster_service,
        config_service=config_service,
    )


def prepare_ansible_job_config(
    task: Task,
    job: AnsibleJob,
    configuration: ExternalSettings,
    config_service: core.config.ConfigService,
    topology: ClusterTopology | None = None,
) -> dict[str, Any]:
    job_data = JobData(
        id=job.id,
        action=task.action.name,
        job_name=job.name,
        command=job.name,
        script=job.script,
        verbose=task.verbose,
        playbook=str(task.bundle.root / job.script),
        action_type_specification=_get_owner_specific_data(task=task),
    )

    if task.owner and topology:
        job_data.cluster_id = topology.cluster_id

    if task.config:
        job_data.config = task.config

    params: dict = job.params.model_dump()
    if not params["ansible_tags"]:
        # if it's empty, it shouldn't be included
        # and since it's the only "pre-defined" field we want empty dict if that's the case
        params.pop("ansible_tags")

    if params:
        job_data.params = params

    process_context = None

    if task.action_process and topology:
        process = Process.objects.get(id=task.action_process.id)
        process_context = context_m.get_action_process_context(process, topology, config_service=config_service)

    adcm = ADCM.objects.select_related("config").get()

    return JobConfig(
        adcm=ADCMJobConfig(
            uuid=adcm.uuid, config=context_m.get_adcm_configuration(adcm, config_service=config_service)
        ),
        context=context_m.get_run_context(task=task),
        env=JobEnv(
            run_dir=str(configuration.adcm.run_dir),
            log_dir=str(configuration.adcm.log_dir),
            tmp_dir=str(configuration.adcm.run_dir / str(job.id) / "tmp"),
            stack_dir=str(task.bundle.root),
            status_api_token=configuration.integrations.status_server_token,
            consul_url=configuration.consul.url,
            consul_datacenter=configuration.consul.datacenter,
            consul_cacert_file=configuration.consul.cacert_file,
        ),
        job=job_data,
        process=process_context.to_context() if process_context else None,
    ).model_dump(mode="json", exclude_unset=True)


def prepare_ansible_cfg(task: Task) -> ConfigParser:
    config_parser = ConfigParser()

    ansible_cfg_from_bundle = task.bundle.root / "ansible.cfg"
    if ansible_cfg_from_bundle.is_file():
        config_parser.read(filenames=ansible_cfg_from_bundle, encoding="utf-8")
    else:
        config_parser["defaults"] = {
            "deprecation_warnings": False,
            "callback_whitelist": "profile_tasks",
            "stdout_callback": "yaml",
        }
        config_parser["ssh_connection"] = {"retries": "3"}

    if task.owner.type in {ADCMCoreType.CLUSTER, ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT}:
        cluster_id = task.owner.id if task.owner.type == ADCMCoreType.CLUSTER else task.owner.related_objects.cluster.id

        settings_to_override = (
            AnsibleConfig.objects.values_list("value", flat=True)
            .filter(object_id=cluster_id, object_type=ContentType.objects.get_for_model(Cluster))
            .first()
        )
        # we consider that if we got settings, they are of correct form (string values),
        # otherwise `deep_merge` might fail
        deep_merge(origin=config_parser, renovator=settings_to_override or {})

    return config_parser


def _get_owner_specific_data(
    task: Task,
) -> ClusterActionType | ServiceActionType | ComponentActionType | ProviderActionType | HostActionType:
    owner = task.owner
    if not owner:
        message = "Can't get owner task data for task without owner"
        raise RuntimeError(message)

    match owner.type:
        case ADCMCoreType.CLUSTER:
            return ClusterActionType(action_proto_type="cluster", hostgroup="CLUSTER")
        case ADCMCoreType.PROVIDER:
            return ProviderActionType(
                action_proto_type="provider",
                hostgroup="PROVIDER",
                provider_id=task.owner.id,
            )
        case ADCMCoreType.HOST:
            return HostActionType(
                action_proto_type="host",
                hostgroup="HOST",
                hostname=task.owner.name,
                host_id=task.owner.id,
                host_type_id=task.owner.prototype_id,
                provider_id=task.owner.related_objects.provider.id,
            )
        case ADCMCoreType.SERVICE:
            return ServiceActionType(
                action_proto_type="service",
                hostgroup=task.owner.name,
                service_id=task.owner.id,
                service_type_id=task.owner.prototype_id,
            )
        case ADCMCoreType.COMPONENT:
            return ComponentActionType(
                action_proto_type="component",
                hostgroup=f"{owner.related_objects.service.name}.{owner.name}",
                service_id=owner.related_objects.service.id,
                component_id=owner.id,
                component_type_id=owner.prototype_id,
            )
        case _:
            message = f"Can't get task data for task with owner {owner.type}"
            raise NotImplementedError(message)


# FINALIZERS


def save_fs_logs_to_db(job: Job, work_dir: Path, log_type: Literal["stdout", "stderr"]) -> None:
    log_path = work_dir / f"{job.type.value}-{log_type}.txt"
    if not log_path.is_file():
        return

    corresponding_log = LogStorage.objects.filter(job_id=job.id, name=job.type.value, type=log_type).first()
    if not corresponding_log:
        return

    corresponding_log.body = log_path.read_text(encoding="utf-8")
    corresponding_log.save(update_fields=["body"])
