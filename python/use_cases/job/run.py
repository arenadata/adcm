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
from typing import Literal, TypeAlias
import logging

from audit.alt.core import NameHalfSplitter
from cm.converters import action_target_type_to_model, core_type_to_model
from cm.legacy.services.concern.locks import (
    delete_task_flag_concern,
    delete_task_lock_concern,
    update_task_flag_concern,
    update_task_lock_concern,
)
from cm.legacy.services.job.run import create_related_configs
from cm.legacy.services.job.run.audit import audit_task_finish
from cm.legacy.services.job.run.runners import (
    NO_PROCESS_PID,
    EventNotifier,
    set_hostcomponent,
    update_object_maintenance_mode,
)
from cm.transition.status import StatusScenarios
from core.action import CallingProcess, ExecutionStatus, Job, Task, TaskOwner
from core.action.job import JobRepoI, JobUpdateDTO, TaskUpdateDTO
from core.cluster import ClusterService
from core.legacy.job.runners import ExecutionTargetFactoryI, ExternalSettings, RunnerEnvironment
from core.types import ActionTargetDescriptor, ADCMCoreType, CoreObjectDescriptor, JobID, TaskID
from django.db.transaction import atomic
from use_cases.wizard import CompleteWizardOperationStep
import core

# NOTE:
#  Type checker errors are ignored for now, because it's problematic to resolve it now reasonably

logger = logging.getLogger("task_runner_err")

PlannedJobs: TypeAlias = tuple[Job, ...]


@dataclass(slots=True)
class TaskDescription:
    jobs: PlannedJobs


@dataclass(slots=True)
class SetTaskToRunning:
    repo: JobRepoI
    notifier: EventNotifier

    def do(self, task_id: TaskID, environment: RunnerEnvironment) -> TaskDescription:
        status = ExecutionStatus.RUNNING

        with atomic():
            jobs = self.repo.get_task_jobs(task_id=task_id)

            to_update = TaskUpdateDTO(pid=environment.pid, start_date=environment.now(), status=status)
            self.repo.update_task(id=task_id, data=to_update)

        self.notifier.send_task_status_update_event(task_id=task_id, status=status.value)

        return TaskDescription(jobs=tuple(jobs))


@dataclass(slots=True)
class RunJob:
    repo: JobRepoI
    target_factory: ExecutionTargetFactoryI
    cluster_service: ClusterService
    external_settings: ExternalSettings

    def do(
        self, task_id: TaskID, job_id: JobID, environment: RunnerEnvironment
    ) -> Literal[ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.REVOKED, ExecutionStatus.ABORTED]:
        with atomic():
            task = self.repo.get_task(id=task_id)
            job = self.repo.get_job(id=job_id)

            if job.status == ExecutionStatus.REVOKED:
                return job.status

            execute_target, *_ = self.target_factory(task=task, jobs=(job,), configuration=self.external_settings)
            executor = execute_target.executor

            # prepare job environemnt
            (self.external_settings.adcm.run_dir / str(job_id) / "tmp").mkdir(parents=True, exist_ok=True)

            for prepare_environment in execute_target.environment_builders:
                prepare_environment(
                    task=task, job=job, configuration=self.external_settings, cluster_service=self.cluster_service
                )

            create_related_configs(job_id=job_id, owner=task.owner)  # pyright: ignore[reportArgumentType]

            executor.execute()

            to_update = JobUpdateDTO(
                pid=getattr(execute_target.executor.process, "pid", NO_PROCESS_PID),
                status=ExecutionStatus.RUNNING,
                start_date=environment.now(),
            )
            self.repo.update_job(id=job_id, data=to_update)

            # it's enough to detect the function once (as the delete one),
            # but implementation of such a thing is better be done with thoughfull concerns refactoring
            if task.is_blocking:
                update_task_lock_concern(job_id=job_id)
            else:
                update_task_flag_concern(job_id=job_id)

        result = executor.wait_finished().result

        if not result:
            raise RuntimeError("Unexpectedly no result written after executor is finished")

        if result.code == -15:
            job_status = ExecutionStatus.ABORTED
        elif result.code == 0:
            job_status = ExecutionStatus.SUCCESS
        else:
            job_status = ExecutionStatus.FAILED

        # Since the connection was opened outside of the Django request-response cycle and can be open for a long time,
        # you must explicitly close old and unusable connections.
        self.repo.close_old_connections()

        with atomic():
            self.repo.update_job(id=job_id, data=JobUpdateDTO(status=job_status, finish_date=environment.now()))

            # There a some approaches to implement finalizers:
            #  1. "safe" finalizers that doesn't invoke their own errors, fail task on first error
            #  2. catch all finalizers' exceptions, write as error, continue task
            #  3. catch finalizers' exceptions, write as error, let all finalizers finish, fail task on error
            #
            # Currently **3rd** one is implemented,
            # meaning we'll try to execute all specified finalizers,
            # log their exceptions and raise the last exception
            exception_to_raise = None
            for finalizer in execute_target.finalizers:
                try:
                    finalizer(job=job)
                except Exception as err:
                    exception_to_raise = err
                    message = "Unhandled exception occurred during after-job finalization"
                    logger.exception(message)

            if exception_to_raise:
                raise exception_to_raise

        return job_status


@dataclass(slots=True)
class FinalizeTask:
    job_repo: JobRepoI
    notifier: EventNotifier
    status_scenarios: StatusScenarios
    cluster_service: ClusterService

    complete_wizard_operation: CompleteWizardOperationStep

    audit_name_splitter: NameHalfSplitter

    def do(
        self,
        task_id: TaskID,
        environment: RunnerEnvironment,
    ):
        with atomic():
            task = self.job_repo.get_task(id=task_id)
            jobs = tuple(self.job_repo.get_task_jobs(task_id=task_id))

            task_is_aborted = task.status == ExecutionStatus.TERMINATING

            task_result = core.action.job.operations.calculate_task_final_status(
                last_job_status=jobs[-1].status, task_is_aborted=task_is_aborted
            )

            if task.is_blocking:
                delete_task_lock_concern(task_id=task_id)
            else:
                delete_task_flag_concern(task_id=task_id)

            audit_task_finish(task=task, task_result=task_result, name_splitter=self.audit_name_splitter)

            if task.action_process and isinstance(task.action_process, CallingProcess):
                self._update_calling_process(
                    process=task.action_process,
                    task=task,
                    task_owner=task.owner,
                    task_status=task_result,
                )
            elif task.owner:
                # Note:
                #   Owner should be updated only when action's not a part of operation step of wizard process.
                #   This patch raises questions about what can be updated and what not,
                #   but that requires clarification of task runner process and configurability of it,
                #   which for now is not achievable.

                # not very accurate status filtering, but ok since all those operations are chaotic for now
                last_finished_job = next(filter(lambda j: j.status != ExecutionStatus.CREATED, reversed(jobs)), None)
                if last_finished_job:
                    owner_descriptor = CoreObjectDescriptor(id=task.owner.id, type=task.owner.type)
                    self._update_owner_state(
                        task=task, last_finished_job=last_finished_job, owner=owner_descriptor, task_result=task_result
                    )

                # Note:
                #   In sequential runner, task was reread for that call, probably due to hostcomponent caching.
                #   Now since we read task after all jobs are finished, it __should__ work nicely,
                #   but if it fails, investigate why.
                if task_result == ExecutionStatus.SUCCESS and task.action.hc_acl:
                    set_hostcomponent(task=task, cluster_service=self.cluster_service, logger=logger)

            if task.target:
                update_object_maintenance_mode(
                    action_name=task.action.name,
                    object_=task.target if isinstance(task.target.type, ADCMCoreType) else task.owner,  # pyright: ignore[reportArgumentType]
                )

            self.job_repo.update_task(id=task.id, data=TaskUpdateDTO(finish_date=environment.now(), status=task_result))

        self.notifier.send_task_status_update_event(task_id=task_id, status=task_result)

        try:
            self.status_scenarios.reset_objects_in_mm()
        except:  # noqa: E722
            logger.exception("Error loading mm objects on task finish")

        try:
            self.status_scenarios.reset_hc_map()
        except:  # noqa: E722
            logger.exception("Error loading host-component map on task finish")

    def _update_owner_state(
        self, task: Task, last_finished_job: Job, owner: CoreObjectDescriptor, task_result: ExecutionStatus
    ) -> None:
        if task_result == ExecutionStatus.SUCCESS:
            multi_state_set = task.on_success.multi_state_set
            multi_state_unset = task.on_success.multi_state_unset
            state = task.on_success.state
            if not state:
                logger.warning('task for "%s" success state is not set', task.action.display_name)

        elif task_result == ExecutionStatus.FAILED:
            job_on_fail = last_finished_job.on_fail
            task_on_fail = task.on_fail
            state = job_on_fail.state or task_on_fail.state
            multi_state_set = job_on_fail.multi_state_set or task_on_fail.multi_state_set
            multi_state_unset = job_on_fail.multi_state_unset or task_on_fail.multi_state_unset
            if not state:
                logger.warning('task for "%s" fail state is not set', task.action.display_name)

        else:
            if task_result != ExecutionStatus.ABORTED:
                logger.error("unknown task status: %s", task_result)

            return

        if state:
            self.job_repo.update_owner_state(owner=owner, state=state)

        self.job_repo.update_owner_multi_states(
            owner=owner, add_multi_states=multi_state_set, remove_multi_states=multi_state_unset
        )

        if task.action.is_upgrade:
            self.notifier.send_prototype_update_event(object_=owner)
        else:
            self.notifier.send_update_event(object_=owner, changes={"state": state})

    def _update_calling_process(
        self, process: CallingProcess, task: Task, task_owner: TaskOwner | None, task_status: ExecutionStatus
    ) -> None:
        from cm.legacy.services.action_process.types import ProcessContext
        from cm.models import Action

        if not (task_owner and task.target):
            raise RuntimeError("Task has no owner/target")

        owner = CoreObjectDescriptor(id=task_owner.id, type=task_owner.type)
        target = ActionTargetDescriptor(id=task.target.id, type=task.target.type)
        process_context = ProcessContext(
            action=self.job_repo.get_action(id=task.action.id),
            action_orm=Action.objects.get(id=task.action.id),
            owner=owner,
            owner_orm=core_type_to_model(owner.type).objects.get(id=owner.id),  # pyright: ignore[reportArgumentType]
            target=target,
            target_orm=action_target_type_to_model(target.type).objects.get(id=target.id),  # pyright: ignore[reportArgumentType]
        )

        self.complete_wizard_operation.do(
            process_id=process.id,
            process_sync_key=process.sync_key,
            step_id=process.step_id,
            process_context=process_context,
            is_operation_success=task_status == ExecutionStatus.SUCCESS,
        )


@dataclass(slots=True)
class MarkTaskBroken:
    repo: JobRepoI

    @atomic
    def do(self, task_id: TaskID, environment: RunnerEnvironment) -> None:
        self.repo.update_task(
            id=task_id,
            data=TaskUpdateDTO(status=ExecutionStatus.BROKEN, finish_date=environment.now()),
        )
