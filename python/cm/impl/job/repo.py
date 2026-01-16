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

from copy import deepcopy
from dataclasses import asdict, is_dataclass
from functools import reduce
from typing import Final, Iterable, cast
import operator

from core.legacy.job.types import ExecutionStatus, Job, JobParams, JobSpec, ScriptType, StateChanges, TaskMappingDelta
from core.types import (
    ActionID,
    ActionTargetDescriptor,
    CoreObjectDescriptor,
    ExtraActionTargetType,
    HostGroupDescriptor,
    HostID,
    TaskID,
)
from django.db.models import F, Value
import core

from cm.converters import core_type_to_model, model_name_to_core_type, orm_object_to_core_descriptor
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


class JobRepo(core.job.JobRepoI):
    # retrieve

    def find_jobs_of_task(self, task_id: TaskID) -> tuple[Job, ...]:
        query = _job_log_qs()
        filtered_by_task_id = query.filter(task_id=task_id)
        return tuple(map(_job_log_to_job, filtered_by_task_id))

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

    # create

    def create_task(self, payload: core.job.dto.TaskCreateDTO) -> TaskID:
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
            description=payload.description,
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

    def create_logs(self, logs: Iterable[core.job.dto.LogCreateDTO]) -> None:
        LogStorage.objects.bulk_create(
            LogStorage(job_id=log.job_id, name=log.name, type=log.type, format=log.format) for log in logs
        )

    # update

    def fill_task_mapping_and_configuration(
        self, task_id: TaskID, payload: core.job.dto.TaskUpdateMainFieldsDTO
    ) -> None:
        fields_to_update = {
            "hostcomponentmap": _mapping_delta_to_db_dict(payload.mapping_delta),
            "config": payload.configuration,
        }

        TaskLog.objects.filter(id=task_id).update(**fields_to_update)


# conversions


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


def _job_log_to_job(job: JobLog) -> Job:
    params = deepcopy(job.params)
    ansible_tags = params.pop("ansible_tags", "") or ""
    if not isinstance(ansible_tags, str):
        # todo I don't like to fix it here,
        #  but not sure we can validate it now on config.yaml load
        #  see https://tracker.yandex.ru/ADCM-5325
        ansible_tags = ""
        if isinstance(ansible_tags, (list, tuple)):
            ansible_tags = ",".join(map(str, ansible_tags))

    return Job(
        id=job.pk,
        pid=job.pid,
        name=job.name,
        type=ScriptType(job.script_type),
        status=ExecutionStatus(job.status),
        script=job.script,
        params=JobParams(ansible_tags=ansible_tags, **params),
        on_fail=StateChanges(
            state=job.state_on_fail,
            multi_state_set=tuple(job.multi_state_on_fail_set or ()),
            multi_state_unset=tuple(job.multi_state_on_fail_unset or ()),
        ),
    )


# queries


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
            query = query.union(values)  # pyright: ignore[reportArgumentType]

        case (ADCMCoreType.HOST, ADCMCoreType.CLUSTER | ADCMCoreType.SERVICE | ADCMCoreType.COMPONENT):
            query = query.union(_get_host_related_selector(host_id=target.id, owner=owner))

        case (ADCMCoreType.SERVICE, _):
            cluster_id = Service.objects.values_list("cluster_id", flat=True).get(id=target.id)
            values = Cluster.objects.values(**_SELECTOR_FIELDS_MAP[Cluster]).filter(id=cluster_id)
            query = query.union(values)  # pyright: ignore[reportArgumentType]

        case (ADCMCoreType.COMPONENT, _):
            cluster_id, service_id = Component.objects.values_list("cluster_id", "service_id").get(id=target.id)
            cluster_qs = Cluster.objects.values(**_SELECTOR_FIELDS_MAP[Cluster]).filter(id=cluster_id)
            service_qs = Service.objects.values(**_SELECTOR_FIELDS_MAP[Service]).filter(id=service_id)
            query = query.union(cluster_qs).union(service_qs)  # pyright: ignore[reportArgumentType]

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
        query = query.union(values)  # pyright: ignore[reportArgumentType]
    elif owner.type == ADCMCoreType.COMPONENT:
        service_id, component_id = Component.objects.values_list("service_id", "id").get(
            cluster_id=cluster_id, id=owner.id
        )
        service_values = Service.objects.values(**_SELECTOR_FIELDS_MAP[Service]).filter(id=service_id)
        component_values = Component.objects.values(**_SELECTOR_FIELDS_MAP[Component]).filter(id=component_id)
        query = query.union(service_values).union(component_values)  # pyright: ignore[reportArgumentType]

    return query
