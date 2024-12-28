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

from contextlib import suppress
from copy import deepcopy
from functools import reduce
from pathlib import Path
from typing import Collection, Iterable
import operator

from core.errors import NotFoundError
from core.job.dto import JobUpdateDTO, LogCreateDTO, TaskMutableFieldsDTO, TaskPayloadDTO, TaskUpdateDTO
from core.job.repo import ActionRepoInterface, JobRepoInterface
from core.job.types import (
    ActionInfo,
    BundleInfo,
    ExecutionStatus,
    HostComponentChanges,
    Job,
    JobParams,
    JobSpec,
    RelatedObjects,
    ScriptType,
    StateChanges,
    Task,
    TaskActionInfo,
    TaskOwner,
)
from core.types import (
    ActionID,
    ActionTargetDescriptor,
    ADCMCoreType,
    CoreObjectDescriptor,
    HostID,
    NamedActionObject,
    NamedCoreObjectWithPrototype,
    PrototypeDescriptor,
)
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F, QuerySet, Value

from cm.converters import (
    core_type_to_model,
    db_record_type_to_core_type,
    model_name_to_core_type,
    orm_object_to_action_target_type,
)
from cm.models import (
    ADCM,
    Action,
    ActionHostGroup,
    Cluster,
    Component,
    Host,
    JobLog,
    LogStorage,
    Provider,
    Service,
    SubAction,
    TaskLog,
    Upgrade,
)


class JobRepoImpl(JobRepoInterface):
    # need to filter out "unsupported" values, because no guarantee DB have correct ones
    _supported_statuses = tuple(entry.value for entry in ExecutionStatus)
    _supported_script_types = tuple(entry.value for entry in ScriptType)
    _selector_fields_map = {
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

    @classmethod
    def get_task(cls, id: int) -> Task:  # noqa: A002
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
            target=target_,
            owner=cls._get_task_owner(task_record=task_record),
            selector=task_record.selector,
            action=TaskActionInfo(
                name=task_record.action.name,
                display_name=task_record.action.display_name,
                venv=task_record.action.venv,
                hc_acl=task_record.action.hostcomponentmap,
                is_upgrade=Upgrade.objects.filter(action=task_record.action).exists(),
                is_host_action=task_record.action.host_action,
            ),
            bundle=bundle,
            verbose=task_record.verbose,
            config=task_record.config,
            hostcomponent=HostComponentChanges(
                saved=task_record.hostcomponentmap,
                post_upgrade=task_record.post_upgrade_hc_map,
                restore_on_fail=task_record.restore_hc_on_fail,
            ),
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
        )

    @staticmethod
    def get_task_mutable_fields(id: int) -> TaskMutableFieldsDTO:  # noqa: A002
        task_row = TaskLog.objects.values("hostcomponentmap", "post_upgrade_hc_map", "restore_hc_on_fail").get(id=id)
        return TaskMutableFieldsDTO(
            hostcomponent=HostComponentChanges(
                saved=task_row["hostcomponentmap"],
                post_upgrade=task_row["post_upgrade_hc_map"],
                restore_on_fail=task_row["restore_hc_on_fail"],
            )
        )

    @classmethod
    def create_task(
        cls, target: ActionTargetDescriptor, owner: CoreObjectDescriptor, action: ActionInfo, payload: TaskPayloadDTO
    ) -> Task:
        if action.owner_prototype.type == ADCMCoreType.ADCM:
            if target.type != ADCMCoreType.ADCM:
                message = f"ADCM actions can be launched only on ADCM: {target=} ; {action.owner_prototype=}"
                raise TypeError(message)

            selector = {"adcm": {"id": target.id, "name": "adcm"}}
            object_type = ADCM.class_content_type
        elif target.type == ADCMCoreType.ADCM:
            message = f"ADCM actions can be launched only on ADCM: {target=} ; {action.owner_prototype=}"
            raise TypeError(message)

        elif isinstance(target.type, ADCMCoreType):
            selector = cls._get_selector_for_core_object(
                target=CoreObjectDescriptor(id=target.id, type=target.type), owner=action.owner_prototype
            )
            object_type = core_type_to_model(core_type=target.type).class_content_type
        else:
            group = ActionHostGroup.objects.select_related("object_type").get(id=target.id)
            group_owner = CoreObjectDescriptor(
                id=group.object_id, type=model_name_to_core_type(group.object_type.model)
            )
            selector = {"action_host_group": {"id": group.id, "name": group.name}} | cls._get_selector_for_core_object(
                target=group_owner, owner=action.owner_prototype
            )
            object_type = ContentType.objects.get_for_model(ActionHostGroup)

        task = TaskLog.objects.create(
            action_id=action.id,
            object_id=target.id,
            object_type=object_type,
            owner_id=owner.id,
            owner_type=owner.type.value,
            config=payload.conf,
            attr=payload.attr or {},
            hostcomponentmap=[
                {"host_id": entry.host_id, "component_id": entry.component_id} for entry in payload.hostcomponent
            ]
            if payload.hostcomponent is not None
            else None,
            post_upgrade_hc_map=payload.post_upgrade_hostcomponent,
            verbose=payload.verbose,
            status=ExecutionStatus.CREATED.value,
            selector=selector,
            is_blocking=payload.is_blocking,
        )

        return cls.get_task(id=task.pk)

    @classmethod
    def get_task_jobs(cls, task_id: int) -> Iterable[Job]:
        return map(cls._job_from_job_log, cls._job_log_qs().filter(task_id=task_id))

    @classmethod
    def get_job(cls, id: int) -> Job:  # noqa: A002
        with suppress(ObjectDoesNotExist):
            return cls._job_from_job_log(cls._job_log_qs().filter(id=id).get())

        message = f"Can't find job with id {id}"
        raise NotFoundError(message)

    @staticmethod
    def update_task(id: int, data: TaskUpdateDTO) -> None:  # noqa: A002
        fields_to_change: dict = data.model_dump(exclude_unset=True)
        if "status" in fields_to_change:
            fields_to_change["status"] = fields_to_change["status"].value

        TaskLog.objects.filter(id=id).update(**fields_to_change)

    @staticmethod
    def update_job(id: int, data: JobUpdateDTO) -> None:  # noqa: A002
        fields_to_change: dict = data.model_dump(exclude_unset=True)
        if "status" in fields_to_change:
            fields_to_change["status"] = fields_to_change["status"].value

        JobLog.objects.filter(id=id).update(**fields_to_change)

    @staticmethod
    def create_jobs(task_id: int, jobs: Iterable[JobSpec]) -> None:
        JobLog.objects.bulk_create(
            JobLog(
                task_id=task_id,
                status=ExecutionStatus.CREATED.value,
                **job.dict(),
            )
            for job in jobs
        )

    @staticmethod
    def create_logs(logs: Iterable[LogCreateDTO]) -> None:
        LogStorage.objects.bulk_create(
            LogStorage(job_id=log.job_id, name=log.name, type=log.type, format=log.format) for log in logs
        )

    @classmethod
    def update_owner_state(cls, owner: CoreObjectDescriptor, state: str) -> None:
        core_type_to_model(core_type=owner.type).objects.filter(id=owner.id).update(state=state)

    @classmethod
    def update_owner_multi_states(
        cls, owner: CoreObjectDescriptor, add_multi_states: Collection[str], remove_multi_states: Collection[str]
    ) -> None:
        current_multi_state: dict = (
            core_type_to_model(core_type=owner.type).objects.values_list("_multi_state", flat=True).get(id=owner.id)
        )

        current_multi_state |= {state: 1 for state in add_multi_states}
        for remove_key in remove_multi_states:
            current_multi_state.pop(remove_key, None)

        core_type_to_model(core_type=owner.type).objects.filter(id=owner.id).update(_multi_state=current_multi_state)

    @staticmethod
    def _job_from_job_log(job: JobLog) -> Job:
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
            id=job.id,
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

    @classmethod
    def _job_log_qs(cls) -> QuerySet:
        return JobLog.objects.order_by("id").filter(
            script_type__in=cls._supported_script_types, status__in=cls._supported_statuses
        )

    @classmethod
    def _get_selector_for_core_object(cls, target: CoreObjectDescriptor, owner: PrototypeDescriptor) -> dict:
        model_ = core_type_to_model(core_type=target.type)
        query = model_.objects.values(**cls._selector_fields_map[model_]).filter(id=target.id)

        match target.type, owner.type:
            case (ADCMCoreType.HOST, ADCMCoreType.HOST):
                provider_id = Host.objects.values_list("provider_id", flat=True).get(id=target.id)
                query = query.union(
                    Provider.objects.values(**cls._selector_fields_map[Provider]).filter(id=provider_id)
                )
            case (ADCMCoreType.HOST, ADCMCoreType.CLUSTER | ADCMCoreType.SERVICE | ADCMCoreType.COMPONENT):
                query = query.union(cls._get_host_related_selector(host_id=target.id, action_owner=owner))
            case (ADCMCoreType.SERVICE, _):
                cluster_id = Service.objects.values_list("cluster_id", flat=True).get(id=target.id)
                query = query.union(Cluster.objects.values(**cls._selector_fields_map[Cluster]).filter(id=cluster_id))
            case (ADCMCoreType.COMPONENT, _):
                cluster_id, service_id = Component.objects.values_list("cluster_id", "service_id").get(id=target.id)
                cluster_qs = Cluster.objects.values(**cls._selector_fields_map[Cluster]).filter(id=cluster_id)
                service_qs = Service.objects.values(**cls._selector_fields_map[Service]).filter(id=service_id)
                query = query.union(cluster_qs).union(service_qs)

        return {entry["type_name"]: {"id": entry["object_id"], "name": entry["object_name"]} for entry in query.all()}

    @classmethod
    def _get_host_related_selector(cls, host_id: HostID, action_owner: PrototypeDescriptor) -> QuerySet:
        cluster_id = Host.objects.values_list("cluster_id", flat=True).get(id=host_id)
        if not cluster_id:
            message = "Can't detect selector for host without cluster for other targets than host itself"
            raise RuntimeError(message)

        query = Cluster.objects.values("id", object_name=F("name"), type_name=Value(ADCMCoreType.CLUSTER.value)).filter(
            id=cluster_id
        )

        if action_owner.type == ADCMCoreType.SERVICE:
            query = query.union(
                Service.objects.values(**cls._selector_fields_map[Service]).filter(
                    prototype_id=action_owner.id, cluster_id=cluster_id
                )
            )
        elif action_owner.type == ADCMCoreType.COMPONENT:
            service_id, component_id = Component.objects.values_list("service_id", "id").get(
                cluster_id=cluster_id, prototype_id=action_owner.id
            )
            query = query.union(Service.objects.values(**cls._selector_fields_map[Service]).filter(id=service_id))
            query = query.union(Component.objects.values(**cls._selector_fields_map[Component]).filter(id=component_id))

        return query

    @classmethod
    def _get_task_owner(cls, task_record: TaskLog) -> TaskOwner | None:
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


class ActionRepoImpl(ActionRepoInterface):
    @staticmethod
    def get_action(id: ActionID) -> ActionInfo:  # noqa: A002
        action = Action.objects.values("id", "name", "prototype_id", "prototype__type", "scripts_jinja").get(id=id)
        return ActionInfo(
            id=action["id"],
            name=action["name"],
            owner_prototype=PrototypeDescriptor(
                id=action["prototype_id"], type=db_record_type_to_core_type(db_record_type=action["prototype__type"])
            ),
            scripts_jinja=action["scripts_jinja"],
        )

    @classmethod
    def get_job_specs(cls, id: ActionID) -> Iterable[JobSpec]:  # noqa: A002
        return [
            cls._from_entry_to_spec(sub_action)
            for sub_action in cls._qs_with_spec_values(SubAction.objects.filter(action_id=id)).order_by("id")
        ]

    @staticmethod
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

    @staticmethod
    def _from_entry_to_spec(entry: dict) -> JobSpec:
        # in db it can be dict, list or anything else actually
        source_params = entry.pop("params", {}) or {}
        # try to fix if it's not dict here, until
        if isinstance(source_params, list) and all(isinstance(entry, dict) for entry in source_params):
            source_params = reduce(operator.or_, source_params, {})
        elif not isinstance(source_params, dict):
            source_params = {}

        return JobSpec(**entry, params=source_params)
