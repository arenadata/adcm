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
from operator import itemgetter
from typing import Any, Protocol
import os
import signal
import logging

from core.job.dto import JobUpdateDTO, TaskUpdateDTO
from core.job.runners import ExecutionTarget, RunnerRuntime, TaskRunner
from core.job.types import ExecutionStatus, Job, Task
from core.types import ADCMCoreType, CoreObjectDescriptor, NamedCoreObject

NO_PROCESS_PID = 0


class EventNotifier(Protocol):
    def send_update_event(self, object_: CoreObjectDescriptor, changes: dict) -> Any:
        ...

    def send_task_status_update_event(self, task_id: int, status: str) -> Any:
        ...

    def send_prototype_update_event(self, object_: CoreObjectDescriptor) -> Any:
        ...


class StatusServerInteractor(Protocol):
    def reset_objects_in_mm(self) -> Any:
        ...


def set_job_lock(job_id: int) -> None:
    # todo move it to `cm.services.job` somewhere
    from cm.models import JobLog

    job = JobLog.objects.select_related("task").get(pk=job_id)
    if job.task.lock and job.task.task_object:
        job.task.lock.reason = job.cook_reason()
        job.task.lock.save(update_fields=["reason"])


def set_hostcomponent(task: Task, logger: logging.Logger):
    # todo move it to `cm.services.job` somewhere
    from cm.api import save_hc  # fixme no way it can be in `cm.api`
    from cm.models import ClusterObject, Host, ServiceComponent, TaskLog, get_object_cluster

    # todo no need in task here, just take owner from task
    task_ = TaskLog.objects.prefetch_related("task_object").get(id=task.id)

    cluster = get_object_cluster(task_.task_object)
    if cluster is None:
        logger.error("no cluster in task #%s", task_.pk)

        return

    new_hostcomponent = task.hostcomponent.to_set
    hosts = {
        entry.pk: entry for entry in Host.objects.filter(id__in=set(map(itemgetter("host_id"), new_hostcomponent)))
    }
    services = {
        entry.pk: entry
        for entry in ClusterObject.objects.filter(id__in=set(map(itemgetter("service_id"), new_hostcomponent)))
    }
    components = {
        entry.pk: entry
        for entry in ServiceComponent.objects.filter(id__in=set(map(itemgetter("component_id"), new_hostcomponent)))
    }

    host_comp_list = [
        (services[entry["service_id"]], hosts[entry["host_id"]], components[entry["component_id"]])
        for entry in new_hostcomponent
    ]

    logger.warning("task #%s is failed, restore old hc", task_.pk)

    save_hc(cluster, host_comp_list)


def remove_task_lock(task_id: int) -> None:
    from cm.issue import unlock_affected_objects
    from cm.models import TaskLog

    unlock_affected_objects(TaskLog.objects.get(pk=task_id))


def update_issues(object_: CoreObjectDescriptor):
    # todo move it to `cm.services.job` somewhere
    from cm.converters import core_type_to_model
    from cm.issue import update_hierarchy_issues

    update_hierarchy_issues(obj=core_type_to_model(core_type=object_.type).objects.get(id=object_.id))


def update_object_maintenance_mode(action_name: str, object_: CoreObjectDescriptor):
    # todo move it to `cm.services.job` somewhere
    from django.conf import settings

    from cm.converters import core_type_to_model
    from cm.models import MaintenanceMode

    obj = core_type_to_model(core_type=object_.type).objects.get(id=object_.id)

    if (
        action_name in {settings.ADCM_TURN_ON_MM_ACTION_NAME, settings.ADCM_HOST_TURN_ON_MM_ACTION_NAME}
        and obj.maintenance_mode == MaintenanceMode.CHANGING
    ):
        obj.maintenance_mode = MaintenanceMode.OFF
        obj.save()

    if (
        action_name in {settings.ADCM_TURN_OFF_MM_ACTION_NAME, settings.ADCM_HOST_TURN_OFF_MM_ACTION_NAME}
        and obj.maintenance_mode == MaintenanceMode.CHANGING
    ):
        obj.maintenance_mode = MaintenanceMode.ON
        obj.save()


def audit_job_finish(
    owner: NamedCoreObject, display_name: str, is_upgrade: bool, job_result: ExecutionStatus
) -> None:  # todo probably shouldn't be here at all
    from audit.cases.common import get_or_create_audit_obj
    from audit.cef_logger import cef_logger
    from audit.models import AuditLog, AuditLogOperationResult, AuditLogOperationType, AuditObjectType

    operation_name = f"{display_name} {'upgrade' if is_upgrade else 'action'} completed"

    if owner.type == ADCMCoreType.HOSTPROVIDER:
        obj_type = AuditObjectType.PROVIDER
    else:
        obj_type = AuditObjectType(owner.type.value)

    audit_object = get_or_create_audit_obj(
        object_id=str(owner.id),
        object_name=owner.name,
        object_type=obj_type,
    )
    operation_result = (
        AuditLogOperationResult.SUCCESS if job_result == ExecutionStatus.SUCCESS else AuditLogOperationResult.FAIL
    )

    audit_log = AuditLog.objects.create(
        audit_object=audit_object,
        operation_name=operation_name,
        operation_type=AuditLogOperationType.UPDATE,
        operation_result=operation_result,
        object_changes={},
    )

    cef_logger(audit_instance=audit_log, signature_id="Action completion")


class JobSequenceRunner(TaskRunner):
    _notifier: EventNotifier
    _status_server = StatusServerInteractor

    def __init__(
        self, *, notifier: EventNotifier, status_server: StatusServerInteractor, logger: logging.Logger, **kwargs: Any
    ):
        super().__init__(**kwargs)

        self._notifier = notifier
        self._status_server = status_server
        self._logger = logger

    def terminate(self) -> None:
        self._runtime.termination.is_requested = True
        for job_to_terminate in filter(
            lambda job_: job_.status == ExecutionStatus.RUNNING and job_.pid != NO_PROCESS_PID,
            self._repo.get_task_jobs(task_id=self._runtime.task_id),
        ):
            self._logger.info(f"Terminating job #{job_to_terminate.id} with pid {job_to_terminate.pid}")
            try:
                os.kill(job_to_terminate.pid, signal.SIGTERM)
            except OSError:
                self._logger.exception(f"Failed to abort job #{job_to_terminate.id} at pid {job_to_terminate.pid}")

    def consider_broken(self) -> None:
        # special value is used to avoid handling NPEs
        if self._runtime.task_id < 0:
            return

        self._runtime.status = ExecutionStatus.BROKEN
        try:
            self._finish(task=self._repo.get_task(id=self._runtime.task_id), last_job=None)
        except:  # noqa: E722
            # force set task finish date if something goes wrong
            self._repo.update_task(
                id=self._runtime.task_id,
                data=TaskUpdateDTO(status=self._runtime.status, finish_date=self._environment.now()),
            )

    def run(self, task_id: int):
        task, configured_jobs = self._configure(task_id=task_id)
        self._start(task_id=task_id)

        last_processed_job = None
        last_job_result = None
        for current_job in configured_jobs:
            self._prepare_job_environment(target=current_job)

            last_processed_job = current_job.job
            last_job_result = self._execute_job(target=current_job)

            if self._runtime.status != ExecutionStatus.ABORTED and last_job_result not in (
                ExecutionStatus.SUCCESS,
                ExecutionStatus.ABORTED,
            ):
                self._runtime.status = ExecutionStatus.FAILED

            if not self._should_proceed(last_job_result=last_job_result):
                break

        if self._runtime.termination.is_requested or (
            last_job_result == ExecutionStatus.ABORTED and last_processed_job.id == configured_jobs[-1].job.id
        ):
            self._runtime.status = ExecutionStatus.ABORTED
        elif self._runtime.status == ExecutionStatus.RUNNING:
            if last_job_result in (ExecutionStatus.ABORTED, None):
                self._runtime.status = ExecutionStatus.SUCCESS
            else:
                self._runtime.status = last_job_result

        self._finish(
            task=task,
            last_job=last_processed_job,
        )

    def _configure(self, task_id: int) -> tuple[Task, tuple[ExecutionTarget, ...]]:
        self._runtime: RunnerRuntime = RunnerRuntime(task_id=task_id)

        task = self._repo.get_task(id=task_id)

        if not (task.target and task.bundle_root):
            message = "Can't run task with no owner and/or bundle info"
            raise RuntimeError(message)

        configured_jobs = tuple(
            self._job_processor.convert(
                task=task,
                jobs=filter(self._job_processor.filter_predicate, self._repo.get_task_jobs(task_id=task_id)),
                configuration=self._settings,
            )
        )
        if not configured_jobs:
            raise RuntimeError()

        return task, configured_jobs

    def _start(self, task_id: int) -> None:
        self._repo.update_task(
            id=task_id,
            data=TaskUpdateDTO(
                pid=self._environment.pid, start_date=self._environment.now(), status=ExecutionStatus.RUNNING
            ),
        )
        self._runtime.status = ExecutionStatus.RUNNING
        self._notifier.send_task_status_update_event(task_id=self._runtime.task_id, status=self._runtime.status.value)

    def _prepare_job_environment(self, target: ExecutionTarget) -> None:
        (self._settings.adcm.run_dir / str(target.job.id) / "tmp").mkdir(parents=True, exist_ok=True)

        for prepare_environment in target.environment_builders:
            prepare_environment(job=target.job)

    def _execute_job(self, target: ExecutionTarget) -> ExecutionStatus:
        target.executor.execute()

        self._repo.update_job(
            id=target.job.id,
            data=JobUpdateDTO(
                pid=getattr(target.executor.process, "pid", NO_PROCESS_PID),
                status=ExecutionStatus.RUNNING,
                start_date=self._environment.now(),
            ),
        )

        # todo add object update based on job state/multi_state update rules

        set_job_lock(job_id=target.job.id)

        result = target.executor.wait_finished().result

        if result.code == -15:
            job_status = ExecutionStatus.ABORTED
        elif result.code == 0:
            job_status = ExecutionStatus.SUCCESS
        else:
            job_status = ExecutionStatus.FAILED

        self._repo.update_job(
            id=target.job.id, data=JobUpdateDTO(status=job_status, finish_date=self._environment.now())
        )

        for finalizer in target.finalizers:
            # todo should we catch any exception here and just log it?
            finalizer(job=target.job)

        return job_status

    def _should_proceed(self, last_job_result: ExecutionStatus) -> bool:
        if self._runtime.termination.is_requested:
            return False

        if last_job_result == ExecutionStatus.SUCCESS:
            return True

        # ABORTED means "skipped" here, so if it's skipped, we just continue
        return last_job_result == ExecutionStatus.ABORTED

    def _finish(self, task: Task, last_job: Job | None):
        task_result = self._runtime.status

        remove_task_lock(task_id=task.id)

        audit_job_finish(
            owner=task.target,
            display_name=task.display_name,
            is_upgrade=task.is_upgrade,
            job_result=task_result,
        )

        finished_task = self._repo.get_task(id=task.id)
        if finished_task.owner:
            self._update_owner_object(owner=finished_task.owner, finished_task=finished_task, last_job=last_job)

        if finished_task.target:
            update_object_maintenance_mode(action_name=finished_task.name, object_=finished_task.target)

        self._repo.update_task(id=task.id, data=TaskUpdateDTO(finish_date=self._environment.now(), status=task_result))
        self._notifier.send_task_status_update_event(task_id=self._runtime.task_id, status=task_result)

        try:
            self._status_server.reset_objects_in_mm()
        except:  # noqa: E722
            self._logger.exception("Error loading mm objects on task finish")

    def _update_owner_object(self, owner: CoreObjectDescriptor, finished_task: Task, last_job: Job | None):
        """Task should be re-read before calling this method, because some flags need to be updated"""
        if last_job:
            self._update_owner_state(task=finished_task, job=last_job, owner=owner)

        if (
            self._runtime.status in {ExecutionStatus.FAILED, ExecutionStatus.ABORTED, ExecutionStatus.BROKEN}
            and finished_task.hostcomponent.to_set is not None
            and finished_task.hostcomponent.restore_on_fail
        ):
            set_hostcomponent(task=finished_task, logger=self._logger)

        update_issues(object_=owner)

    def _update_owner_state(self, task: Task, job: Job, owner: CoreObjectDescriptor) -> None:
        if self._runtime.status == ExecutionStatus.SUCCESS:
            multi_state_set = task.on_success.multi_state_set
            multi_state_unset = task.on_success.multi_state_unset
            state = task.on_success.state
            if not state:
                self._logger.warning('task for "%s" success state is not set', task.display_name)

        elif self._runtime.status == ExecutionStatus.FAILED:
            job_on_fail = job.on_fail
            task_on_fail = task.on_fail
            state = job_on_fail.state or task_on_fail.state
            multi_state_set = job_on_fail.multi_state_set or task_on_fail.multi_state_set
            multi_state_unset = job_on_fail.multi_state_unset or task_on_fail.multi_state_unset
            if not state:
                self._logger.warning('task for "%s" fail state is not set', task.display_name)

        else:
            if self._runtime.status != ExecutionStatus.ABORTED:
                self._logger.error("unknown task status: %s", self._runtime.status)

            return

        if state:
            self._repo.update_owner_state(owner=owner, state=state)

        self._repo.update_owner_multi_states(
            owner=owner, add_multi_states=multi_state_set, remove_multi_states=multi_state_unset
        )

        if task.is_upgrade:
            self._notifier.send_prototype_update_event(object_=owner)
        else:
            self._notifier.send_update_event(object_=owner, changes={"state": state})
