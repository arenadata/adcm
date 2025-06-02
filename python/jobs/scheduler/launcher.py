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

from types import ModuleType
import os
import time
import logging

import adcm.init_django  # noqa: F401, isort:skip

from cm.errors import AdcmEx
from cm.models import Cluster
from cm.services.cluster import retrieve_cluster_topology
from cm.services.job.action import check_hostcomponent_and_get_delta, check_no_blocking_concerns
from cm.services.job.run.repo import JobRepoImpl, JobRepoInterface, TaskTargetCoreObject
from core.cluster.operations import construct_mapping_from_delta
from core.job.dto import TaskUpdateDTO
from core.job.types import ExecutionStatus, Task
from core.types import BundleID, TaskID
from django.db.transaction import atomic
from jobs.scheduler import repo as SchedulerRepo  # noqa: N812
from jobs.scheduler._types import TaskQueuer, TaskRunnerEnvironment
from jobs.scheduler.errors import LauncherError
from jobs.scheduler.queuers import LocalTaskQueuer
from jobs.scheduler.task_status import set_status_on_fail, set_status_on_success
from jobs.services.concerns import distribute_concerns

DEFAULT_JOB_EXECUTION_ENVIRONMENT = os.environ.get("DEFAULT_JOB_EXECUTION_ENVIRONMENT", "local")
EXECUTOR_REGISTRY = {
    TaskRunnerEnvironment.LOCAL: LocalTaskQueuer,
    TaskRunnerEnvironment.CELERY: ...,  # TODO
}

logger = logging.getLogger("job_scheduler")


def run_launcher_in_loop() -> None:
    job_repo: JobRepoInterface = JobRepoImpl
    scheduler_repo: ModuleType = SchedulerRepo
    queuer = EXECUTOR_REGISTRY[DEFAULT_JOB_EXECUTION_ENVIRONMENT]()

    logger.info(f"{queuer.env.capitalize()} launcher started (pid: {os.getpid()})")

    while True:
        time.sleep(1)

        scheduled = False
        with atomic(), job_repo.retrieve_and_lock_first_created_task() as task_id:
            if task_id is None:
                continue

            scheduled = schedule_task(
                task_id=task_id, env_type=queuer.env, job_repo=job_repo, scheduler_repo=scheduler_repo
            )

        if scheduled:
            with atomic():
                queue_task(queuer=queuer, task_id=task_id, job_repo=job_repo)


@set_status_on_fail(status=ExecutionStatus.BROKEN, errors=Exception)
@set_status_on_fail(status=ExecutionStatus.REVOKED, errors=LauncherError)
@set_status_on_success(status=ExecutionStatus.SCHEDULED)
def schedule_task(
    *, task_id: TaskID, env_type: TaskRunnerEnvironment, job_repo: JobRepoInterface, scheduler_repo: ModuleType
) -> bool:
    target_orm = job_repo.get_target_orm(task_id)
    validate(task_id=task_id, target_orm=target_orm, job_repo=job_repo, scheduler_repo=scheduler_repo)

    task_orm = scheduler_repo.retrieve_task_orm(task_id=task_id)
    distribute_concerns(task=task_orm, target=target_orm)

    logger.info(f"Task #{task_id} scheduled to {env_type} queuer")

    return True


@set_status_on_fail(status=ExecutionStatus.BROKEN, errors=Exception)
@set_status_on_fail(status=ExecutionStatus.REVOKED, errors=LauncherError)
@set_status_on_success(status=ExecutionStatus.QUEUED)
def queue_task(*, queuer: TaskQueuer, task_id: TaskID, job_repo: JobRepoInterface) -> None:
    worker_info = queuer.queue(task_id)
    job_repo.update_task(id=task_id, data=TaskUpdateDTO(executor=worker_info))

    logger.info(f"Task #{task_id} queued to #{worker_info['worker_id']} {worker_info['environment']} worker")


def validate(
    task_id: TaskID, target_orm: TaskTargetCoreObject, job_repo: JobRepoInterface, scheduler_repo: ModuleType
) -> None:
    task = job_repo.get_task(id=task_id)
    if not task.target:
        raise LauncherError

    action_orm = scheduler_repo.retrieve_action_orm(action_id=task.action.id)

    if not action_orm.allowed(obj=target_orm):
        raise LauncherError

    try:
        check_no_blocking_concerns(lock_owner=target_orm, action_name=task.action.name)
    except AdcmEx as e:
        raise LauncherError from e

    if action_orm.get_start_impossible_reason(obj=target_orm):
        raise LauncherError

    if task.hostcomponent.mapping_delta:
        cluster = target_orm if isinstance(target_orm, Cluster) else target_orm.cluster
        _check_hc_acl(task=task, cluster=cluster, bundle_id=int(action_orm.prototype.bundle_id))


def _check_hc_acl(task: Task, cluster: Cluster | None, bundle_id: BundleID) -> None:
    if cluster is None:
        raise LauncherError

    topology = retrieve_cluster_topology(cluster_id=cluster.id)
    new_mapping = construct_mapping_from_delta(topology=topology, mapping_delta=task.hostcomponent.mapping_delta)

    try:
        check_hostcomponent_and_get_delta(
            bundle_id=bundle_id,
            topology=topology,
            hc_payload=new_mapping,
            hc_rules=task.action.hc_acl,
            mapping_restriction_err_template="{}",
        )
    except AdcmEx as e:
        raise LauncherError from e
