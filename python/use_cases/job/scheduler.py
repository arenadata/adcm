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
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from functools import wraps
from types import ModuleType
import logging

from cm.converters import orm_object_to_action_target_descriptor
from cm.errors import AdcmEx
from cm.impl.job.repo import TaskTargetCoreObject
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.concern.locks import delete_task_flag_concern, delete_task_lock_concern
from cm.legacy.services.job.action import check_hostcomponent_and_get_delta, check_no_blocking_concerns
from cm.legacy.status_api import send_task_status_update_event
from cm.models import Cluster
from cm.transition.action import RetrieveStartImpossibleReason
from core.action import ExecutionStatus, Task, TaskRunnerEnvironment, TaskShortInfo, is_operation_step_task
from core.action.job import JobRepoI, JobShortFilter, TaskShortFilter, TaskUpdateDTO
from core.action.scheduler import Claimer, TaskLivenessStatus, TaskMonitorRegistry, TaskQueuer, TerminatorRegistry
from core.legacy.cluster.operations import construct_mapping_from_delta
from core.legacy.job.runners import RunnerEnvironment
from core.result import Fail, Success
from core.scenarios.concern import ConcernScenarios
from core.types import BundleID, TaskID
from django.db.transaction import atomic
from jobs.scheduler import repo
from use_cases.job.run import MarkTaskBroken

killer_logger = logging.getLogger("scheduler.killer")
monitor_logger = logging.getLogger("scheduler.monitor")
launcher_logger = logging.getLogger("scheduler.launcher")


class SchedulerError(Exception):
    pass


class LauncherError(SchedulerError):
    pass


def set_status_on_success(from_status: ExecutionStatus, to_status: ExecutionStatus):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_id = kwargs["task_id"]
            job_repo: JobRepoI = kwargs["job_repo"]

            res = func(*args, **kwargs)
            updated = job_repo.change_task_status(id=task_id, previous=from_status, new=to_status)
            if updated:
                launcher_logger.info(f"Task #{task_id} is {to_status.value}")

                with suppress(Exception):
                    send_task_status_update_event(task_id=task_id, status=to_status.value)

            return res

        return wrapper

    return decorator


def set_status_on_fail(
    to_status: ExecutionStatus,
    errors: type[Exception] | tuple[type[Exception]],
    return_: bool = False,
    from_status: ExecutionStatus | None = None,
):
    if not isinstance(errors, tuple):
        errors = (errors,)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_id = kwargs["task_id"]
            job_repo: JobRepoI = kwargs["job_repo"]

            try:
                return func(*args, **kwargs)
            except errors:
                launcher_logger.exception(
                    "Something gone wrong, status of task #%d will be set to %s", task_id, to_status
                )

                status_set = None
                if from_status:
                    updated = job_repo.change_task_status(id=task_id, previous=from_status, new=to_status)
                    if updated:
                        status_set = to_status
                else:
                    job_repo.update_task(id=task_id, data=TaskUpdateDTO(status=to_status))
                    status_set = to_status

                if status_set:
                    launcher_logger.info("Task #%d is %s", task_id, to_status)

                    with suppress(Exception):
                        send_task_status_update_event(task_id=task_id, status=to_status.value)

                return return_

        return wrapper

    return decorator


def clear_concerns_on_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        task_id = kwargs["task_id"]
        job_repo: JobRepoI = kwargs["job_repo"]

        try:
            return func(*args, **kwargs)
        except Exception:
            task = next(iter(job_repo.find_tasks_short(TaskShortFilter(ids=[task_id]))))

            if task.lock_id:
                delete_task_lock_concern(task_id=task.id)
            else:
                delete_task_flag_concern(task_id=task.id)

            raise

    return wrapper


@dataclass(slots=True)
class Killer:
    job_repo: JobRepoI
    claimer: Claimer
    registry: TerminatorRegistry

    def do(self) -> None:
        jobs_to_terminate = [
            job.id for job in self.job_repo.find_jobs_short(JobShortFilter(statuses=[ExecutionStatus.REVOKING]))
        ]
        tasks_to_terminate = [
            task.id for task in self.job_repo.find_tasks_short(TaskShortFilter(statuses=[ExecutionStatus.REVOKING]))
        ]

        for job_id in jobs_to_terminate:
            with atomic(), self.claimer.claim_job(job_id, ExecutionStatus.REVOKING) as job_id:
                if not job_id:
                    continue

                killer_logger.debug("Terminating job with id=%d started", job_id)

                job = next(
                    iter(
                        self.job_repo.find_jobs_short(JobShortFilter(ids=[job_id], statuses=[ExecutionStatus.REVOKING]))
                    )
                )
                status_changed = self.job_repo.change_job_status(
                    id=job_id, previous=job.status, new=ExecutionStatus.TERMINATING
                )

                terminator = self.registry[job.worker["environment"]]
                terminator.terminate_job(job)

                killer_logger.debug(
                    "Terminating job with id=%d finished, status changed = %s",
                    job_id,
                    status_changed,
                )

        for task_id in tasks_to_terminate:
            with atomic(), self.claimer.claim_task(task_id, ExecutionStatus.REVOKING) as task_id:
                if not task_id:
                    continue

                killer_logger.debug("Terminating task with id=%d started", task_id)

                task = next(iter(self.job_repo.find_tasks_short(TaskShortFilter(ids=[task_id]))))
                status_changed = self.job_repo.change_task_status(
                    id=task_id, previous=task.status, new=ExecutionStatus.TERMINATING
                )

                terminator = self.registry[task.worker["environment"]]
                terminator.terminate_task(task)

                killer_logger.debug(
                    "Terminating task with id=%d finished, status changed = %s",
                    task_id,
                    status_changed,
                )


@dataclass(slots=True)
class Monitor:
    set_broken: MarkTaskBroken
    running_environment: RunnerEnvironment
    registry: TaskMonitorRegistry
    job_repo: JobRepoI

    def do(self) -> None:
        tasks_to_check: Iterable[TaskShortInfo] = self.job_repo.find_tasks_short(
            TaskShortFilter(statuses=(ExecutionStatus.RUNNING, ExecutionStatus.TERMINATING, ExecutionStatus.QUEUED))
        )

        grouped_by_environment: dict[TaskRunnerEnvironment, list[TaskShortInfo]] = defaultdict(list)
        for task in tasks_to_check:
            grouped_by_environment[task.worker["environment"]].append(task)

        for environment, tasks in grouped_by_environment.items():
            task_monitor = self.registry[environment]
            result = task_monitor.analyze_liveness(tasks)

            for dead_task in result.get(TaskLivenessStatus.DEAD, ()):
                monitor_logger.debug("Task id=%d is considered dead, setting to broken", dead_task.id)

                result = self.set_broken.do(
                    task_id=dead_task.id, environment=self.running_environment, from_status=dead_task.status
                )
                match result:
                    case Success():
                        monitor_logger.debug("Task id=%d set to broken successfuly", dead_task.id)
                    case Fail(msg):
                        monitor_logger.debug("Task id=%d set to broken failed: %s", dead_task.id, msg)


@dataclass(slots=True)
class Launcher:
    queuer: TaskQueuer
    retrieve_start_impossible_reason: RetrieveStartImpossibleReason
    job_repo: JobRepoI
    claimer: Claimer
    scheduler_repo: repo.SchedulerRepo
    concern_scenarios: ConcernScenarios

    def do(self) -> None:
        with atomic(), self.claimer.claim_first_scheduled_or_created_task() as locked:
            if locked is None:
                return

            task_id, task_status = locked
            launcher_logger.debug("Task id=%d locked in status=%s", task_id, task_status)
            match task_status:
                case ExecutionStatus.CREATED:
                    launcher_logger.debug("Scheduling task id=%d", task_id)
                    schedule_task(
                        task_id=task_id,
                        env_type=self.queuer.env,
                        job_repo=self.job_repo,
                        scheduler_repo=self.scheduler_repo,
                        retrieve_sir=self.retrieve_start_impossible_reason,
                        concern_scenarios=self.concern_scenarios,
                    )

                case ExecutionStatus.SCHEDULED:
                    launcher_logger.debug("Queueing task id=%d", task_id)
                    queue_task(queuer=self.queuer, task_id=task_id, job_repo=self.job_repo)


# we don't set from_status for broken, because it should indicate the level or error even if it'll be overwritten
@set_status_on_fail(to_status=ExecutionStatus.BROKEN, errors=Exception)
@set_status_on_fail(from_status=ExecutionStatus.CREATED, to_status=ExecutionStatus.REVOKED, errors=LauncherError)
@set_status_on_success(from_status=ExecutionStatus.CREATED, to_status=ExecutionStatus.SCHEDULED)
@clear_concerns_on_error
def schedule_task(
    *,
    task_id: TaskID,
    env_type: TaskRunnerEnvironment,
    job_repo: JobRepoI,
    scheduler_repo: ModuleType,
    retrieve_sir: RetrieveStartImpossibleReason,
    concern_scenarios: ConcernScenarios,
) -> bool:
    target_orm = job_repo.get_target_orm(task_id)
    task = job_repo.get_task(id=task_id)

    # operation step's task should not be validated
    if not is_operation_step_task(task.action_process):
        validate(
            task_id=task_id,
            target_orm=target_orm,
            job_repo=job_repo,
            scheduler_repo=scheduler_repo,
            retrieve_sir=retrieve_sir,
        )

    first_job = job_repo.find_jobs_of_task(task_id=task_id)[0]
    concern_scenarios.create_job_concern(task=task, first_job=first_job)

    launcher_logger.info(f"Task #{task_id} scheduled to {env_type} queuer")

    return True


# we don't set from_status for broken, because it should indicate the level or error even if it'll be overwritten
@set_status_on_fail(to_status=ExecutionStatus.BROKEN, errors=Exception)
@set_status_on_fail(from_status=ExecutionStatus.SCHEDULED, to_status=ExecutionStatus.REVOKED, errors=LauncherError)
@set_status_on_success(from_status=ExecutionStatus.SCHEDULED, to_status=ExecutionStatus.QUEUED)
@clear_concerns_on_error
def queue_task(*, queuer: TaskQueuer, task_id: TaskID, job_repo: JobRepoI) -> None:
    worker_info = queuer.queue(task_id)
    # disabled during use_cases/jobs.scheduler move, code wasn't pyright-checked before, must be reviewed
    job_repo.update_task(id=task_id, data=TaskUpdateDTO(executor=worker_info))  # pyright: ignore[reportArgumentType]

    launcher_logger.info(f"Task #{task_id} queued as #{worker_info['worker_id']} {worker_info['environment']} task")


def validate(
    task_id: TaskID,
    target_orm: TaskTargetCoreObject,
    job_repo: JobRepoI,
    scheduler_repo: ModuleType,
    retrieve_sir: RetrieveStartImpossibleReason,
) -> None:
    task = job_repo.get_task(id=task_id)
    if not task.target:
        raise LauncherError("Task target is absent.")

    action_orm = scheduler_repo.retrieve_action_orm(action_id=task.action.id)

    if not action_orm.allowed(obj=target_orm):
        raise LauncherError("Action is not allowed.")

    try:
        check_no_blocking_concerns(lock_owner=target_orm, action_name=task.action.name)
    except AdcmEx as e:
        raise LauncherError(e.msg) from e

    is_mm_action = next(iter(job_repo.find_tasks_short(TaskShortFilter(ids=[task_id])))).action.is_mm_action
    start_impossible_reason = retrieve_sir.for_action_target(
        target=orm_object_to_action_target_descriptor(target_orm),
        allowed_in_mm={action_orm.pk: action_orm.allow_in_maintenance_mode},
    )

    if not is_mm_action and start_impossible_reason[action_orm.pk] is not None:
        raise LauncherError(start_impossible_reason[action_orm.pk])

    if task.hostcomponent.mapping_delta:
        # disabled during use_cases/jobs.scheduler move, code wasn't pyright-checked before, must be reviewed
        cluster = (
            target_orm if isinstance(target_orm, Cluster) else target_orm.cluster  # pyright: ignore[reportAttributeAccessIssue]
        )
        _check_hc_acl(task=task, cluster=cluster, bundle_id=int(action_orm.prototype.bundle_id))


def _check_hc_acl(task: Task, cluster: Cluster | None, bundle_id: BundleID) -> None:
    if cluster is None:
        raise LauncherError("Cluster is absent.")

    # disabled during use_cases/jobs.scheduler move, code wasn't pyright-checked before, must be reviewed
    topology = retrieve_cluster_topology(cluster_id=cluster.id)  # pyright: ignore[reportAttributeAccessIssue]
    new_mapping = construct_mapping_from_delta(topology=topology, mapping_delta=task.hostcomponent.mapping_delta)

    try:
        check_hostcomponent_and_get_delta(
            bundle_id=bundle_id,
            topology=topology,
            hc_payload=new_mapping,  # pyright: ignore[reportArgumentType]
            hc_rules=[rule._asdict() for rule in task.action.hc_acl],  # pyright: ignore[reportArgumentType]
            mapping_restriction_err_template="{}",
        )
    except AdcmEx as e:
        raise LauncherError(e.msg) from e
