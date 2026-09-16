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
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Final, Literal, TypeAlias, cast

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
    JobShortInfo,
    RelatedObjects,
    StateChanges,
    Task,
    TaskActionInfo,
    TaskMappingDelta,
    TaskOwner,
    TaskShortInfo,
    WorkerInfo,
)
from core.action.job import (
    JobRepoI,
    JobShortFilter,
    JobUpdateDTO,
    LogCreateDTO,
    PostInitTaskAttributesDTO,
    TaskCreateDTO,
    TaskMutableFieldsDTO,
    TaskShortFilter,
    TaskUpdateDTO,
)
from core.action.scheduler import Claimer
from core.action.types import JobSpecV1, ScriptSpec
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
from pydantic import BaseModel, TypeAdapter

from cm.converters import (
    core_type_to_model,
    db_record_type_to_core_type,
    model_name_to_core_type,
    orm_object_to_action_target_type,
    orm_object_to_core_descriptor,
)
from cm.impl.common.dto import to_update_payload
from cm.impl.common.execution_plan import dump_execution_plan, parse_execution_plan
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
    TaskLog,
    Upgrade,
)

# need to filter out "unsupported" values, because no guarantee DB have correct ones
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
            name=task_record.name,
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

    def find_scripts_of_action(self, action_id: ActionID) -> JobSpecV1:
        return _read_action_scripts(action_id=action_id)

    def get_execution_plan(self, task_id: TaskID) -> JobSpecV1:
        stored = TaskLog.objects.values_list("execution_plan", flat=True).get(id=task_id)
        return parse_execution_plan(stored)

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
            "id", "executor", "pid", "status", "lock_id", "action_id", "action__name", "action___venv"
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
            .values_list("id", "task_id", "spec_key", "finish_date", "executor", "pid", "status")
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

    def create_jobs(self, task_id: TaskID, scripts: JobSpecV1) -> tuple[JobShortInfo, ...]:
        # jobs keep their own copies of the nodes' fields for now, `spec_key` ties them back to the plan
        created = JobLog.objects.bulk_create(
            _script_spec_to_job_log(task_id=task_id, script_spec=script_spec)
            for script_spec in scripts.scripts.values()
        )

        return tuple(_created_job_to_short_info(job) for job in created)

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

    def set_post_init_task_attributes(self, task_id: TaskID, payload: PostInitTaskAttributesDTO) -> None:
        TaskLog.objects.filter(id=task_id).update(
            execution_plan=dump_execution_plan(payload.execution_plan),
            hostcomponentmap=_mapping_delta_to_db_dict(payload.mapping_delta),
            config=payload.configuration,
        )

    def update_task(self, id: int, data: TaskUpdateDTO) -> None:  # noqa: A002
        fields_to_change: dict = to_update_payload(data)
        if "status" in fields_to_change:
            fields_to_change["status"] = fields_to_change["status"].value
        if "hostcomponentmap" in fields_to_change:
            fields_to_change["hostcomponentmap"] = _convert_delta_to_db_format(fields_to_change["hostcomponentmap"])

        TaskLog.objects.filter(id=id).update(**fields_to_change)

    def update_job(self, id: int, data: JobUpdateDTO) -> None:  # noqa: A002
        fields_to_change: dict = to_update_payload(data)
        if "status" in fields_to_change:
            fields_to_change["status"] = fields_to_change["status"].value

        JobLog.objects.filter(id=id).update(**fields_to_change)

    def change_task_status(self, id: TaskID, previous: ExecutionStatus, new: ExecutionStatus) -> bool:  # noqa: A002
        updated = TaskLog.objects.filter(id=id, status=previous).update(status=new)
        return bool(updated)

    def change_job_status(self, id: JobID, previous: ExecutionStatus, new: ExecutionStatus) -> bool:  # noqa: A002
        updated = JobLog.objects.filter(id=id, status=previous).update(status=new)
        return bool(updated)

    def change_status_of_task_jobs(
        self, task_id: TaskID, previous: Iterable[ExecutionStatus], new: ExecutionStatus
    ) -> int:
        return JobLog.objects.filter(task_id=task_id, status__in=previous).update(status=new)

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
            "wizard_template",
            "scripts_template",
        ).get(id=id)
        return ActionInfo(
            id=action["id"],
            name=action["name"],
            owner_prototype=PrototypeDescriptor(
                id=action["prototype_id"], type=db_record_type_to_core_type(db_record_type=action["prototype__type"])
            ),
            scripts_template=action["scripts_template"],
            wizard_template=action["wizard_template"],
        )

    def get_job_specs(self, id: ActionID) -> JobSpecV1:  # noqa: A002
        return _read_action_scripts(action_id=id)


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
    id_, executor, pid, status, lock_id, action_id, action_name, action_venv = fields
    return TaskShortInfo(
        id=id_,
        worker=_to_worker_info(executor=executor, pid=pid),
        status=ExecutionStatus(status.lower()),
        lock_id=lock_id,
        action=ActionShortInfo(id=action_id, name=action_name, venv=action_venv),
    )


def _created_job_to_short_info(job: JobLog) -> JobShortInfo:
    # nothing of it has happened yet, so everything but its identity is at its initial value
    return JobShortInfo(
        id=job.pk,
        task_id=job.task.pk,
        spec_key=job.spec_key,
        finish_date=None,
        worker=WorkerInfo(),
        status=ExecutionStatus(job.status),
    )


def _job_log_fields_to_short_info(fields: tuple) -> JobShortInfo:
    id_, task_id, spec_key, finish_date, executor, pid, status = fields
    return JobShortInfo(
        id=id_,
        task_id=task_id,
        spec_key=spec_key,
        finish_date=finish_date,
        worker=_to_worker_info(executor=executor, pid=pid),
        status=ExecutionStatus(status.lower()),
    )


def _to_worker_info(executor: dict, pid: int) -> WorkerInfo:
    # nothing has been executed yet while a record is only created, the column keeps an empty object for that
    return WorkerInfo(environment=executor.get("environment"), worker_id=executor.get("worker_id"), pid=pid)


def _mapping_delta_to_db_dict(
    mapping_delta: TaskMappingDelta | dict[str, dict[int, set[int]]] | None,
) -> dict[str, dict[int, list[int]]] | None:
    if mapping_delta is None:
        return None

    delta = asdict(mapping_delta) if is_dataclass(mapping_delta) else mapping_delta

    return {key: {k: sorted(v) for k, v in value.items()} for key, value in delta.items()}


def _read_action_scripts(action_id: ActionID) -> JobSpecV1:
    stored = Action.objects.values_list("scripts", flat=True).filter(id=action_id).first()

    if not stored:
        # either no such action or its plan is rendered from a template rather than stored
        return JobSpecV1()

    return parse_execution_plan(stored)


def _script_spec_to_job_log(task_id: TaskID, script_spec: ScriptSpec) -> JobLog:
    return JobLog(
        task_id=task_id,
        status=ExecutionStatus.CREATED.value,
        spec_key=script_spec.key,
        name=script_spec.names.internal,
        display_name=script_spec.names.display,
        script=script_spec.script.path,
        script_type=script_spec.script.type.value,
        params=_script_params_to_db(script_spec),
        allow_to_terminate=script_spec.details.terminatable,
        state_on_fail=script_spec.on_fail.state or "",
        multi_state_on_fail_set=list(script_spec.on_fail.multi_state_set),
        multi_state_on_fail_unset=list(script_spec.on_fail.multi_state_unset),
    )


def _script_params_to_db(script_spec: ScriptSpec) -> dict:
    params = script_spec.script.params

    if params is None:
        return {}

    if isinstance(params, BaseModel):
        return params.model_dump(mode="json")

    return asdict(params)


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
