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
from collections.abc import Collection, Generator, Iterable
from contextlib import contextmanager, suppress
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from functools import reduce
from pathlib import Path
from typing import Final, Literal, TypeAlias, cast
import operator

from core.action import (
    ActionInfo,
    ActionShortInfo,
    AssociatedProcess,
    BundleInfo,
    CallingProcess,
    ExecutionEnvironment,
    ExecutionStatus,
    HcAclRule,
    HostComponentChanges,
    Job,
    JobShortInfo,
    JobSpec,
    RelatedObjects,
    ScriptType,
    StateChanges,
    Task,
    TaskActionInfo,
    TaskMappingDelta,
    TaskOwner,
    TaskShortInfo,
)
from core.action.job import (
    JobRepoI,
    JobShortFilter,
    JobUpdateDTO,
    LogCreateDTO,
    TaskCreateDTO,
    TaskMutableFieldsDTO,
    TaskShortFilter,
    TaskUpdateDTO,
    TaskUpdateMainFieldsDTO,
)
from core.action.scheduler import Claimer
from core.errors import NotFoundError
from core.types import (
    ActionID,
    ActionTargetDescriptor,
    CoreObjectDescriptor,
    ExtraActionTargetType,
    HostGroupDescriptor,
    HostID,
    JobID,
    NamedActionObject,
    NamedCoreObjectWithPrototype,
    PrototypeDescriptor,
    TaskID,
)
from django.conf import settings
from django.db import close_old_connections
from django.db.models import F, ObjectDoesNotExist, Value
from pydantic import TypeAdapter, ValidationError

from cm.converters import (
    core_type_to_model,
    db_record_type_to_core_type,
    model_name_to_core_type,
    orm_object_to_action_target_type,
    orm_object_to_core_descriptor,
)
from cm.models import (
    ADCM,
    Action,
    ActionHostGroup,
    ADCMCoreType,
    Cluster,
    Component,
    ContentType,
    Host,
    JobLog,
    LogStorage,
    Provider,
    QuerySet,
    Service,
    SubAction,
    TaskLog,
    Upgrade,
)

# need to filter out "unsupported" values, because no guarantee DB have correct ones
_SUPPORTED_STATUSES: Final = tuple(entry.value for entry in ExecutionStatus)
_SUPPORTED_SCRIPT_TYPES: Final = tuple(entry.value for entry in ScriptType)
_SELECTOR_FIELDS_MAP: Final = {
    Cluster: {"object_id": F("id"), "object_name": F("name"), "type_name": Value(ADCMCoreType.CLUSTER.value)},
    Service: {
        "object_id": F("id"),
        "object_name": F("prototype__display_name"),
        "type_name": Value(ADCMCoreType.SERVICE.value),
    },
    Component: {
        "object_id": F("id"),
        "object_name": F("prototype__display_name"),
        "type_name": Value(ADCMCoreType.COMPONENT.value),
    },
    Host: {"object_id": F("id"), "object_name": F("fqdn"), "type_name": Value(ADCMCoreType.HOST.value)},
    Provider: {"object_id": F("id"), "object_name": F("name"), "type_name": Value("provider")},
}

TaskTargetCoreObject: TypeAlias = ADCM | Cluster | Service | Component | Provider | Host
_RelatedWizardProcess = TypeAdapter(CallingProcess | AssociatedProcess)


class JobRepo(JobRepoI):
    # retrieve

    def get_task(self, id: int) -> Task:  # noqa: A002
        try:
            task_record: TaskLog = (
                TaskLog.objects.select_related("action__prototype").prefetch_related("task_object").get(id=id)
            )
        except ObjectDoesNotExist:
            message = f"Can't find task identified by {id}"
            raise NotFoundError(message) from None

        if not task_record.action:
            message = f"Task identified by {id} doesn't have linked action"
            raise RuntimeError(message)

        action_prototype = task_record.action.prototype
        target_ = bundle = None
        if target := task_record.task_object:
            target_ = NamedActionObject(
                id=target.pk, type=orm_object_to_action_target_type(object_=target), name=target.name
            )
            if action_prototype.type == "adcm":
                bundle = BundleInfo(root=settings.BASE_DIR / "conf" / "adcm", config_dir=Path())
            else:
                bundle = BundleInfo(
                    root=settings.BUNDLE_DIR / action_prototype.bundle.hash, config_dir=Path(action_prototype.path)
                )

        return Task(
            id=id,
            display_name=task_record.display_name,
            target=target_,
            owner=_get_task_owner(task_record=task_record),
            status=ExecutionStatus(task_record.status),
            is_termination_allowed=task_record.action.allow_to_terminate,
            selector=task_record.selector,
            action=TaskActionInfo(
                id=int(task_record.action_id),  # pyright: ignore[reportAttributeAccessIssue]
                name=task_record.action.name,
                display_name=task_record.action.display_name,
                venv=task_record.action.venv,
                hc_acl=[HcAclRule(**rule) for rule in task_record.action.hostcomponentmap],
                is_upgrade=Upgrade.objects.filter(action=task_record.action).exists(),
                is_host_action=task_record.action.host_action,
            ),
            action_process=task_record.process,
            bundle=bundle,
            verbose=task_record.verbose,
            config=task_record.config,
            hostcomponent=HostComponentChanges(
                post_upgrade=task_record.post_upgrade_hc_map,
                mapping_delta=_restore_delta_from_db_format(task_delta=task_record.hostcomponentmap),
            ),
            execution_env=ExecutionEnvironment(pid=task_record.pid, worker_id=task_record.executor.get("worker_id")),
            on_success=StateChanges(
                state=task_record.action.state_on_success,
                multi_state_set=tuple(task_record.action.multi_state_on_success_set or ()),
                multi_state_unset=tuple(task_record.action.multi_state_on_success_unset or ()),
            ),
            on_fail=StateChanges(
                state=task_record.action.state_on_fail,
                multi_state_set=tuple(task_record.action.multi_state_on_fail_set or ()),
                multi_state_unset=tuple(task_record.action.multi_state_on_fail_unset or ()),
            ),
            is_blocking=task_record.is_blocking,
            description=task_record.description,
        )

    def get_job(self, id: int) -> Job:  # noqa: A002
        with suppress(ObjectDoesNotExist):
            return _build_job(_job_log_qs().filter(id=id).get())

        message = f"Can't find job with id {id}"
        raise NotFoundError(message)

    def find_jobs_of_task(self, task_id: TaskID) -> tuple[Job, ...]:
        query = _job_log_qs()
        filtered_by_task_id = query.filter(task_id=task_id)
        return tuple(map(_build_job, filtered_by_task_id))

    def get_task_jobs(self, task_id: int) -> Iterable[Job]:
        return self.find_jobs_of_task(task_id)

    def find_scripts_of_action(self, action_id: ActionID) -> tuple[JobSpec, ...]:
        query = (
            SubAction.objects.filter(action_id=action_id)
            .order_by("id")
            .values(
                "name",
                "display_name",
                "script",
                "script_type",
                "allow_to_terminate",
                "state_on_fail",
                "multi_state_on_fail_set",
                "multi_state_on_fail_unset",
                "params",
            )
        )

        return tuple(map(_dict_to_job_spec, query))

    # copied from cm.legacy.services.job.action._ActionLaunchObjects
    def find_action_owner(self, action_id: ActionID, target: ActionTargetDescriptor) -> CoreObjectDescriptor:
        match target.type:
            case ADCMCoreType.HOST:
                is_host_action, owner_type, owner_prototype_id = Action.objects.values_list(
                    "host_action", "prototype__type", "prototype_id"
                ).get(id=action_id)
                cluster_id = Host.objects.values_list("cluster_id", flat=True).get(id=target.id)
                if is_host_action and cluster_id:
                    match owner_type:
                        case "component":
                            id_ = Component.objects.values_list("id", flat=True).get(
                                cluster_id=cluster_id, prototype_id=owner_prototype_id
                            )
                            type_ = ADCMCoreType.COMPONENT
                        case "service":
                            id_ = Service.objects.values_list("id", flat=True).get(
                                cluster_id=cluster_id, prototype_id=owner_prototype_id
                            )
                            type_ = ADCMCoreType.SERVICE
                        case "cluster":
                            id_ = cluster_id
                            type_ = ADCMCoreType.CLUSTER
                        case _:
                            message = f"Can't handle {owner_type} type for owner of host action detection"
                            raise NotImplementedError(message)
                else:
                    id_ = target.id
                    type_ = target.type

                return CoreObjectDescriptor(id=id_, type=type_)

            case ExtraActionTargetType.ACTION_HOST_GROUP:
                owner_orm = cast(Cluster | Service | Component, ActionHostGroup.objects.get(id=target.id).object)
                return orm_object_to_core_descriptor(object_=owner_orm)

            case _:  # cluster, service, component, provider
                return CoreObjectDescriptor(id=target.id, type=target.type)

    def find_tasks_short(self, filter_: TaskShortFilter) -> Iterable[TaskShortInfo]:
        filter_kwargs = {}
        if filter_.ids is not None:
            filter_kwargs["id__in"] = filter_.ids
        if filter_.statuses is not None:
            filter_kwargs["status__in"] = filter_.statuses

        query = TaskLog.objects.filter(**filter_kwargs).values_list(
            "id", "executor", "status", "lock_id", "action_id", "action__name"
        )
        return [_task_log_fields_to_short_info(fields) for fields in query]

    def find_jobs_short(self, filter_: JobShortFilter) -> Iterable[JobShortInfo]:
        filter_kwargs = {}
        if filter_.ids is not None:
            filter_kwargs["id__in"] = filter_.ids
        if filter_.task_ids is not None:
            filter_kwargs["task_id__in"] = filter_.task_ids
        if filter_.statuses is not None:
            filter_kwargs["status__in"] = filter_.statuses

        query = (
            JobLog.objects.filter(**filter_kwargs)
            .order_by("id")
            .values_list("id", "task_id", "finish_date", "executor", "status")
        )
        return [_job_log_fields_to_short_info(fields) for fields in query]

    def get_related_wizard_process(self, job_id: JobID) -> CallingProcess | AssociatedProcess | None:
        process_data = JobLog.objects.values_list("task__process", flat=True).get(id=job_id)
        if process_data is None:
            return None

        return _RelatedWizardProcess.validate_python(process_data)

    def get_task_mutable_fields(self, id: int) -> TaskMutableFieldsDTO:  # noqa: A002
        task_row = TaskLog.objects.values("hostcomponentmap", "post_upgrade_hc_map").get(id=id)
        return TaskMutableFieldsDTO(
            hostcomponent=HostComponentChanges(
                post_upgrade=task_row["post_upgrade_hc_map"],
                mapping_delta=_restore_delta_from_db_format(task_delta=task_row["hostcomponentmap"]),
            )
        )

    def get_target_orm(self, task_id: TaskID) -> TaskTargetCoreObject:
        target = TaskLog.objects.get(id=task_id).task_object

        if isinstance(target, ActionHostGroup):
            return cast(TaskTargetCoreObject, ActionHostGroup.objects.get(id=target.pk).object)

        return cast(TaskTargetCoreObject, target)

    # create

    def create_task(self, payload: TaskCreateDTO) -> TaskID:
        match payload.target:
            case CoreObjectDescriptor(type=ADCMCoreType.ADCM):
                selector = {"adcm": {"id": payload.target.id, "name": "adcm"}}
                object_type = ADCM.class_content_type
            case CoreObjectDescriptor():
                selector = _get_selector_for_core_object(target=payload.target, owner=payload.owner)
                object_type = core_type_to_model(core_type=payload.target.type).class_content_type
            case HostGroupDescriptor():
                group = ActionHostGroup.objects.select_related("object_type").get(id=payload.target.id)
                group_owner = CoreObjectDescriptor(
                    id=group.object_id, type=model_name_to_core_type(group.object_type.model)
                )
                selector = {"action_host_group": {"id": group.pk, "name": group.name}} | _get_selector_for_core_object(
                    target=group_owner, owner=payload.owner
                )
                object_type = ContentType.objects.get_for_model(ActionHostGroup)

        task = TaskLog.objects.create(
            action_id=payload.action_id,
            object_id=payload.target.id,
            object_type=object_type,
            owner_id=payload.owner.id,
            owner_type=payload.owner.type.value,
            verbose=payload.launch.is_verbose,
            status=ExecutionStatus.CREATED.value,
            selector=selector,
            is_blocking=payload.launch.is_blocking,
            process=payload.process.model_dump(mode="json") if payload.process else None,
            name=payload.extra.name,
            display_name=payload.extra.display_name,
            description=payload.extra.description,
        )

        return task.pk

    def create_jobs(self, task_id: TaskID, scripts: Iterable[JobSpec]) -> None:
        JobLog.objects.bulk_create(
            JobLog(
                task_id=task_id,
                status=ExecutionStatus.CREATED.value,
                **script.model_dump(),
            )
            for script in scripts
        )

    def create_logs(self, logs: Iterable[LogCreateDTO]) -> None:
        LogStorage.objects.bulk_create(
            LogStorage(job_id=log.job_id, name=log.name, type=log.type, format=log.format) for log in logs
        )

    # update

    def update_owner_state(self, owner: CoreObjectDescriptor, state: str) -> None:
        core_type_to_model(core_type=owner.type).objects.filter(id=owner.id).update(state=state)

    def update_owner_multi_states(
        self, owner: CoreObjectDescriptor, add_multi_states: Collection[str], remove_multi_states: Collection[str]
    ) -> None:
        current_multi_state: dict = (
            core_type_to_model(core_type=owner.type).objects.values_list("_multi_state", flat=True).get(id=owner.id)
        )

        current_multi_state |= {state: 1 for state in add_multi_states}
        for remove_key in remove_multi_states:
            current_multi_state.pop(remove_key, None)

        core_type_to_model(core_type=owner.type).objects.filter(id=owner.id).update(_multi_state=current_multi_state)

    def fill_task_mapping_and_configuration(self, task_id: TaskID, payload: TaskUpdateMainFieldsDTO) -> None:
        fields_to_update = {
            "hostcomponentmap": _mapping_delta_to_db_dict(payload.mapping_delta),
            "config": payload.configuration,
        }

        TaskLog.objects.filter(id=task_id).update(**fields_to_update)

    def update_task(self, id: int, data: TaskUpdateDTO) -> None:  # noqa: A002
        fields_to_change: dict = data.model_dump(exclude_unset=True)
        if "status" in fields_to_change:
            fields_to_change["status"] = fields_to_change["status"].value
        if "hostcomponentmap" in fields_to_change:
            fields_to_change["hostcomponentmap"] = _convert_delta_to_db_format(fields_to_change["hostcomponentmap"])

        TaskLog.objects.filter(id=id).update(**fields_to_change)

    def update_job(self, id: int, data: JobUpdateDTO) -> None:  # noqa: A002
        fields_to_change: dict = data.model_dump(exclude_unset=True)
        if "status" in fields_to_change:
            fields_to_change["status"] = fields_to_change["status"].value

        JobLog.objects.filter(id=id).update(**fields_to_change)

    def change_task_status(self, id: TaskID, previous: ExecutionStatus, new: ExecutionStatus) -> bool:  # noqa: A002
        updated = TaskLog.objects.filter(id=id, status=previous).update(status=new)
        return bool(updated)

    def change_job_status(self, id: JobID, previous: ExecutionStatus, new: ExecutionStatus) -> bool:  # noqa: A002
        updated = JobLog.objects.filter(id=id, status=previous).update(status=new)
        return bool(updated)

    def change_status_of_task_jobs(self, task_id: TaskID, previous: ExecutionStatus, new: ExecutionStatus) -> int:
        return JobLog.objects.filter(task_id=task_id, status=previous).update(status=new)

    # misc

    def close_old_connections(self) -> None:
        close_old_connections()

    # from action repo

    def get_action(self, id: ActionID) -> ActionInfo:  # noqa: A002
        action = Action.objects.values(
            "id",
            "name",
            "prototype_id",
            "prototype__type",
            "scripts_jinja",
            "wizard_template",
            "scripts_template",
        ).get(id=id)
        return ActionInfo(
            id=action["id"],
            name=action["name"],
            owner_prototype=PrototypeDescriptor(
                id=action["prototype_id"], type=db_record_type_to_core_type(db_record_type=action["prototype__type"])
            ),
            scripts_jinja=action["scripts_jinja"],
            scripts_template=action["scripts_template"],
            wizard_template=action["wizard_template"],
        )

    def get_job_specs(self, id: ActionID) -> Iterable[JobSpec]:  # noqa: A002
        query = _qs_with_spec_values(SubAction.objects.filter(action_id=id)).order_by("id")
        return list(map(_from_entry_to_spec, query))


class JobClaimer(Claimer):
    @contextmanager
    def claim_first_scheduled_or_created_task(
        self,
    ) -> Generator[tuple[TaskID, Literal[ExecutionStatus.SCHEDULED, ExecutionStatus.CREATED]] | None]:
        result = None

        fields = (
            TaskLog.objects.select_for_update(skip_locked=True)
            .filter(status__in=(ExecutionStatus.CREATED, ExecutionStatus.SCHEDULED))
            .order_by("-status", "id")
            .values_list("id", "status")
            .first()
        )
        if fields:
            parsed_status = cast(
                Literal[ExecutionStatus.CREATED, ExecutionStatus.SCHEDULED], ExecutionStatus(fields[1])
            )
            result = (int(fields[0]), parsed_status)

        yield result

    @contextmanager
    def claim_task(self, task_id: TaskID, expected_status: ExecutionStatus) -> Generator[TaskID | None]:
        yield (
            TaskLog.objects.select_for_update(skip_locked=True)
            .filter(id=task_id, status=expected_status)
            .values_list("id", flat=True)
            .first()
        )

    @contextmanager
    def claim_job(self, job_id: JobID, expected_status: ExecutionStatus) -> Generator[JobID | None]:
        yield (
            JobLog.objects.select_for_update(skip_locked=True)
            .filter(id=job_id, status=expected_status)
            .values_list("id", flat=True)
            .first()
        )


# conversions


def _task_log_fields_to_short_info(fields: tuple) -> TaskShortInfo:
    id_, executor, status, lock_id, action_id, action_name = fields
    return TaskShortInfo(
        id=id_,
        worker=executor,
        status=ExecutionStatus(status.lower()),
        lock_id=lock_id,
        action=ActionShortInfo(id=action_id, name=action_name),
    )


def _job_log_fields_to_short_info(fields: tuple) -> JobShortInfo:
    id_, task_id, finish_date, executor, status = fields
    return JobShortInfo(
        id=id_, task_id=task_id, finish_date=finish_date, worker=executor, status=ExecutionStatus(status.lower())
    )


def _mapping_delta_to_db_dict(
    mapping_delta: TaskMappingDelta | dict[str, dict[int, set[int]]] | None,
) -> dict[str, dict[int, list[int]]] | None:
    if mapping_delta is None:
        return None

    delta = asdict(mapping_delta) if is_dataclass(mapping_delta) else mapping_delta

    return {key: {k: sorted(v) for k, v in value.items()} for key, value in delta.items()}


def _dict_to_job_spec(entry: dict) -> JobSpec:
    # in db it can be dict, list or anything else actually
    source_params = entry.pop("params", {}) or {}
    # try to fix if it's not dict here
    if isinstance(source_params, list) and all(isinstance(entry, dict) for entry in source_params):
        source_params = reduce(operator.or_, source_params, {})
    elif not isinstance(source_params, dict):
        source_params = {}

    return JobSpec(**entry, params=source_params)


def _from_entry_to_spec(entry: dict) -> JobSpec:
    # in db it can be dict, list or anything else actually
    source_params = entry.pop("params", {}) or {}
    # try to fix if it's not dict here, until
    if isinstance(source_params, list) and all(isinstance(entry, dict) for entry in source_params):
        source_params = reduce(operator.or_, source_params, {})
    elif not isinstance(source_params, dict):
        source_params = {}

    return JobSpec(**entry, params=source_params)


_JOB_TYPE_ADAPTER: Final = TypeAdapter(Job)


def _normalize_ansible_tags(raw_params: dict) -> None:
    ansible_tags = raw_params.pop("ansible_tags", "") or ""
    # todo I don't like to fix it here,
    #  but not sure we can validate it now on config.yaml load
    #  see https://tracker.yandex.ru/ADCM-5325
    if isinstance(ansible_tags, list | tuple):
        ansible_tags = ",".join(map(str, ansible_tags))
    elif not isinstance(ansible_tags, str):
        ansible_tags = ""

    raw_params["ansible_tags"] = ansible_tags


def _build_job(job: JobLog) -> Job:
    script_type = ScriptType(job.script_type)
    raw_params = deepcopy(job.params) or {}
    if not isinstance(raw_params, dict):
        message = f"Job {job.pk} has params of unexpected shape: {raw_params!r}"
        raise TypeError(message)

    if script_type == ScriptType.ANSIBLE:
        _normalize_ansible_tags(raw_params)
        params = raw_params
    else:
        # python jobs and parameterless internal scripts carry no params;
        # hc_apply/config_apply/service_manage params are validated below,
        # matched against `script` by `Job`'s own discriminated union
        params = raw_params or None

    data = {
        "id": job.pk,
        "pid": job.pid,
        "name": job.name,
        "type": script_type,
        "script": job.script,
        "status": ExecutionStatus(job.status),
        "params": params,
        "on_fail": StateChanges(
            state=job.state_on_fail,
            multi_state_set=tuple(job.multi_state_on_fail_set or ()),
            multi_state_unset=tuple(job.multi_state_on_fail_unset or ()),
        ),
        "is_termination_allowed": job.allow_to_terminate,
        "execution_env": ExecutionEnvironment(pid=job.pid, worker_id=job.executor.get("worker_id")),
    }

    try:
        return _JOB_TYPE_ADAPTER.validate_python(data)
    except ValidationError as error:
        message = f"Can't build Job {job.pk} for script_type={script_type!r} script={job.script!r}: {error}"
        raise ValueError(message) from error


# queries


def _qs_with_spec_values(query: QuerySet) -> QuerySet:
    return query.values(
        "name",
        "display_name",
        "script",
        "script_type",
        "allow_to_terminate",
        "state_on_fail",
        "multi_state_on_fail_set",
        "multi_state_on_fail_unset",
        "params",
    )


def _job_log_qs() -> QuerySet[JobLog]:
    return JobLog.objects.order_by("id").filter(script_type__in=_SUPPORTED_SCRIPT_TYPES, status__in=_SUPPORTED_STATUSES)


# utilities


def _get_selector_for_core_object(target: CoreObjectDescriptor, owner: CoreObjectDescriptor) -> dict:
    model_ = core_type_to_model(core_type=target.type)
    # todo Most likely we should use `Descriptor[X]` instead of `CoreObjectDescriptor`
    #      in order to specify what can and can't be passed in functions,
    #      because in this case ADCM descriptor shouldn't be in here
    query = model_.objects.values(**_SELECTOR_FIELDS_MAP[model_]).filter(id=target.id)

    match target.type, owner.type:
        case (ADCMCoreType.HOST, ADCMCoreType.HOST):
            provider_id = Host.objects.values_list("provider_id", flat=True).get(id=target.id)
            values = Provider.objects.values(**_SELECTOR_FIELDS_MAP[Provider]).filter(id=provider_id)
            # todo ??? stabs for django doesn't cover that case?
            query = query.union(values)

        case (ADCMCoreType.HOST, ADCMCoreType.CLUSTER | ADCMCoreType.SERVICE | ADCMCoreType.COMPONENT):
            query = query.union(_get_host_related_selector(host_id=target.id, owner=owner))

        case (ADCMCoreType.SERVICE, _):
            cluster_id = Service.objects.values_list("cluster_id", flat=True).get(id=target.id)
            values = Cluster.objects.values(**_SELECTOR_FIELDS_MAP[Cluster]).filter(id=cluster_id)
            query = query.union(values)

        case (ADCMCoreType.COMPONENT, _):
            cluster_id, service_id = Component.objects.values_list("cluster_id", "service_id").get(id=target.id)
            cluster_qs = Cluster.objects.values(**_SELECTOR_FIELDS_MAP[Cluster]).filter(id=cluster_id)
            service_qs = Service.objects.values(**_SELECTOR_FIELDS_MAP[Service]).filter(id=service_id)
            query = query.union(cluster_qs).union(service_qs)

    return {entry["type_name"]: {"id": entry["object_id"], "name": entry["object_name"]} for entry in query.all()}


def _get_host_related_selector(host_id: HostID, owner: CoreObjectDescriptor) -> QuerySet:
    cluster_id = Host.objects.values_list("cluster_id", flat=True).get(id=host_id)
    if not cluster_id:
        message = "Can't detect selector for host without cluster for other targets than host itself"
        raise RuntimeError(message)

    query = Cluster.objects.values("id", object_name=F("name"), type_name=Value(ADCMCoreType.CLUSTER.value)).filter(
        id=cluster_id
    )

    if owner.type == ADCMCoreType.SERVICE:
        values = Service.objects.values(**_SELECTOR_FIELDS_MAP[Service]).filter(id=owner.id, cluster_id=cluster_id)
        query = query.union(values)
    elif owner.type == ADCMCoreType.COMPONENT:
        service_id, component_id = Component.objects.values_list("service_id", "id").get(
            cluster_id=cluster_id, id=owner.id
        )
        service_values = Service.objects.values(**_SELECTOR_FIELDS_MAP[Service]).filter(id=service_id)
        component_values = Component.objects.values(**_SELECTOR_FIELDS_MAP[Component]).filter(id=component_id)
        query = query.union(service_values).union(component_values)

    return query


def _get_task_owner(task_record: TaskLog) -> TaskOwner | None:
    if not (task_record.owner_type and task_record.owner_id):
        return None

    owner_type = ADCMCoreType(task_record.owner_type)
    owner_model = core_type_to_model(core_type=owner_type)
    # object can be deleted at any point, so if it doesn't exist anymore, owner should be None
    if not owner_model.objects.filter(id=task_record.owner_id).exists():
        return None

    owner_id = task_record.owner_id

    related_cluster_values = ("cluster_id", "cluster__prototype_id", "cluster__name")
    related_service_values = ("service_id", "service__prototype_id", "service__prototype__name")
    related_provider_values = ("provider_id", "provider__prototype_id", "provider__name")

    match owner_type:
        case ADCMCoreType.ADCM | ADCMCoreType.CLUSTER | ADCMCoreType.PROVIDER:
            return TaskOwner(
                id=owner_id,
                type=owner_type,
                **owner_model.objects.values("name", "prototype_id").get(id=owner_id),
                related_objects=RelatedObjects(),
            )
        case ADCMCoreType.SERVICE:
            data = owner_model.objects.values("prototype__name", "prototype_id", *related_cluster_values).get(
                id=owner_id
            )
            cluster = NamedCoreObjectWithPrototype(
                id=data["cluster_id"],
                prototype_id=data["cluster__prototype_id"],
                type=ADCMCoreType.CLUSTER,
                name=data["cluster__name"],
            )
            return TaskOwner(
                id=owner_id,
                type=ADCMCoreType.SERVICE,
                prototype_id=data["prototype_id"],
                name=data["prototype__name"],
                related_objects=RelatedObjects(cluster=cluster),
            )
        case ADCMCoreType.COMPONENT:
            data = owner_model.objects.values(
                "prototype__name", "prototype_id", *related_cluster_values, *related_service_values
            ).get(id=owner_id)
            cluster = NamedCoreObjectWithPrototype(
                id=data["cluster_id"],
                prototype_id=data["cluster__prototype_id"],
                type=ADCMCoreType.CLUSTER,
                name=data["cluster__name"],
            )
            service = NamedCoreObjectWithPrototype(
                id=data["service_id"],
                prototype_id=data["service__prototype_id"],
                type=ADCMCoreType.SERVICE,
                name=data["service__prototype__name"],
            )
            return TaskOwner(
                id=owner_id,
                type=ADCMCoreType.COMPONENT,
                prototype_id=data["prototype_id"],
                name=data["prototype__name"],
                related_objects=RelatedObjects(cluster=cluster, service=service),
            )
        case ADCMCoreType.HOST:
            data = owner_model.objects.values(
                "prototype_id",
                *related_cluster_values,
                *related_provider_values,
                name=F("fqdn"),
            ).get(id=owner_id)
            cluster = (
                NamedCoreObjectWithPrototype(
                    id=data["cluster_id"],
                    prototype_id=data["cluster__prototype_id"],
                    type=ADCMCoreType.CLUSTER,
                    name=data["cluster__name"],
                )
                if data["cluster_id"]
                else None
            )
            provider = NamedCoreObjectWithPrototype(
                id=data["provider_id"],
                prototype_id=data["provider__prototype_id"],
                type=ADCMCoreType.PROVIDER,
                name=data["provider__name"],
            )
            return TaskOwner(
                id=owner_id,
                type=ADCMCoreType.HOST,
                prototype_id=data["prototype_id"],
                name=data["name"],
                related_objects=RelatedObjects(cluster=cluster, provider=provider),
            )
        case _:
            message = f"Can't detect owner of type {owner_type}"
            raise NotImplementedError(message)


def _restore_delta_from_db_format(task_delta: dict | None) -> TaskMappingDelta | None:
    if task_delta is None:
        return None

    to_add, to_remove = defaultdict(set), defaultdict(set)
    for component_id, host_ids in task_delta.get("add", {}).items():
        to_add[int(component_id)].update(host_ids)
    for component_id, host_ids in task_delta.get("remove", {}).items():
        to_remove[int(component_id)].update(host_ids)

    return TaskMappingDelta(add=to_add, remove=to_remove)


def _convert_delta_to_db_format(
    mapping_delta: TaskMappingDelta | dict[str, dict[int, set[int]]] | None,
) -> dict[str, dict[int, list[int]]] | None:
    if mapping_delta is None:
        return None

    delta = asdict(mapping_delta) if is_dataclass(mapping_delta) else mapping_delta

    return {key: {k: sorted(v) for k, v in value.items()} for key, value in delta.items()}
