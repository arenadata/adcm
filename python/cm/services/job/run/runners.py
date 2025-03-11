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

from logging import Logger
from typing import Any, Protocol
import os
import signal

from core.job.dto import JobUpdateDTO, TaskUpdateDTO
from core.job.runners import ExecutionTarget, RunnerRuntime, TaskRunner
from core.job.types import ExecutionStatus, Job, Task
from core.types import ADCMCoreType, CoreObjectDescriptor

from cm.services.concern.locks import (
    delete_task_flag_concern,
    delete_task_lock_concern,
    update_task_flag_concern,
    update_task_lock_concern,
)
from cm.services.job.run._task_finalizers import (
    set_hostcomponent,
    update_object_maintenance_mode,
)
from cm.services.job.run.audit import audit_task_finish

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

    def reset_hc_map(self) -> Any:
        ...


class JobSequenceRunner(TaskRunner):
    _notifier: EventNotifier
    _status_server = StatusServerInteractor

    def __init__(
        self, *, notifier: EventNotifier, status_server: StatusServerInteractor, logger: Logger, **kwargs: Any
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
            task = self._get_updated_task(task=task)
            self._prepare_job_environment(task=task, target=current_job)

            last_processed_job = current_job.job
            last_job_result = self._execute_job(task=task, target=current_job)

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

        self._finish(task=task, last_job=last_processed_job)

    def _configure(self, task_id: int) -> tuple[Task, tuple[ExecutionTarget, ...]]:
        self._runtime: RunnerRuntime = RunnerRuntime(task_id=task_id)

        task = self._repo.get_task(id=task_id)

        if not (task.target and task.bundle):
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

    def _get_updated_task(self, task: Task) -> Task:
        """
        Update fields that can be changed during task execution EXCEPT owner object's related info
        """
        new_fields = self._repo.get_task_mutable_fields(id=task.id)
        if task.hostcomponent == new_fields.hostcomponent:
            return task

        return Task(**(task.dict() | {"hostcomponent": new_fields.hostcomponent}))

    def _prepare_job_environment(self, task: Task, target: ExecutionTarget) -> None:
        (self._settings.adcm.run_dir / str(target.job.id) / "tmp").mkdir(parents=True, exist_ok=True)

        for prepare_environment in target.environment_builders:
            prepare_environment(task=task, job=target.job, configuration=self._settings)

    def _execute_job(self, task: Task, target: ExecutionTarget) -> ExecutionStatus:
        target.executor.execute()

        self._repo.update_job(
            id=target.job.id,
            data=JobUpdateDTO(
                pid=getattr(target.executor.process, "pid", NO_PROCESS_PID),
                status=ExecutionStatus.RUNNING,
                start_date=self._environment.now(),
            ),
        )

        # it's enough to detect the function once (as the delete one),
        # but implementation of such a thing is better be done with thoughfull concerns refactoring
        if task.is_blocking:
            update_task_lock_concern(job_id=target.job.id)
        else:
            update_task_flag_concern(job_id=target.job.id)

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

        # There a some approaches to implement finalizers:
        #  1. "safe" finalizers that doesn't invoke their own errors, fail task on first error
        #  2. catch all finalizers' exceptions, write as error, continue task
        #  3. catch finalizers' exceptions, write as error, let all finalizers finish, fail task on error
        #
        # Currently **3rd** one is implemented,
        # meaning we'll try to execute all specified finalizers,
        # log their exceptions and raise the last exception
        exception_to_raise = None
        for finalizer in target.finalizers:
            try:
                finalizer(job=target.job)
            except Exception as err:
                exception_to_raise = err
                message = "Unhandled exception occurred during after-job finalization"
                self._logger.exception(message)

        if exception_to_raise:
            raise exception_to_raise

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

        if task.is_blocking:
            delete_task_lock_concern(task_id=task.id)
        else:
            delete_task_flag_concern(task_id=task.id)

        audit_task_finish(task=task, task_result=task_result)

        finished_task = self._repo.get_task(id=task.id)
        if finished_task.owner:
            self._update_owner_object(
                owner=CoreObjectDescriptor(id=finished_task.owner.id, type=finished_task.owner.type),
                finished_task=finished_task,
                last_job=last_job,
            )

        if finished_task.target:
            update_object_maintenance_mode(
                action_name=finished_task.action.name,
                object_=finished_task.target
                if isinstance(finished_task.target.type, ADCMCoreType)
                else finished_task.owner,
            )

        self._repo.update_task(id=task.id, data=TaskUpdateDTO(finish_date=self._environment.now(), status=task_result))
        self._notifier.send_task_status_update_event(task_id=self._runtime.task_id, status=task_result)

        try:
            self._status_server.reset_objects_in_mm()
        except:  # noqa: E722
            self._logger.exception("Error loading mm objects on task finish")

        try:
            self._status_server.reset_hc_map()
        except:  # noqa: E722
            self._logger.exception("Error loading host-component map on task finish")

    def _update_owner_object(self, owner: CoreObjectDescriptor, finished_task: Task, last_job: Job | None):
        """Task should be re-read before calling this method, because some flags need to be updated"""
        if last_job:
            self._update_owner_state(task=finished_task, job=last_job, owner=owner)

        if (
            self._runtime.status in {ExecutionStatus.FAILED, ExecutionStatus.ABORTED, ExecutionStatus.BROKEN}
            and finished_task.action.hc_acl
            and finished_task.hostcomponent.restore_on_fail
        ):
            set_hostcomponent(task=finished_task, logger=self._logger)

    def _update_owner_state(self, task: Task, job: Job, owner: CoreObjectDescriptor) -> None:
        if self._runtime.status == ExecutionStatus.SUCCESS:
            multi_state_set = task.on_success.multi_state_set
            multi_state_unset = task.on_success.multi_state_unset
            state = task.on_success.state
            if not state:
                self._logger.warning('task for "%s" success state is not set', task.action.display_name)

        elif self._runtime.status == ExecutionStatus.FAILED:
            job_on_fail = job.on_fail
            task_on_fail = task.on_fail
            state = job_on_fail.state or task_on_fail.state
            multi_state_set = job_on_fail.multi_state_set or task_on_fail.multi_state_set
            multi_state_unset = job_on_fail.multi_state_unset or task_on_fail.multi_state_unset
            if not state:
                self._logger.warning('task for "%s" fail state is not set', task.action.display_name)

        else:
            if self._runtime.status != ExecutionStatus.ABORTED:
                self._logger.error("unknown task status: %s", self._runtime.status)

            return

        if state:
            self._repo.update_owner_state(owner=owner, state=state)

        self._repo.update_owner_multi_states(
            owner=owner, add_multi_states=multi_state_set, remove_multi_states=multi_state_unset
        )

        if task.action.is_upgrade:
            self._notifier.send_prototype_update_event(object_=owner)
        else:
            self._notifier.send_update_event(object_=owner, changes={"state": state})
