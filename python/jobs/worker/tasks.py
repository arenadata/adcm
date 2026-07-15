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


import logging

from celery import Task, chain, signature
from celery.canvas import Signature
from celery.signals import after_setup_logger
from core.action import ExecutionStatus
from core.action.job import JobRepoI, JobUpdateDTO
from core.legacy.job.runners import RunnerEnvironment, TaskRunner
from core.types import JobID, TaskID
from use_cases.job.run import FinalizeTask, MarkTaskBroken, PlannedJobs, RunJob, SetTaskToRunning
import dishka

from jobs.worker.celery.custom import di_task
from jobs.worker.celery.worker import app

# "INFRA"


class JobFailedFlowError(Exception):
    def __init__(self, *args, task_id: TaskID, job_id: JobID, final_status: ExecutionStatus) -> None:
        super().__init__(*args)

        self.task_id = task_id
        self.job_id = job_id
        self.final_status = final_status


class JobFailedFlowErrFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        is_special_exc = record.exc_info and record.exc_info[0] == JobFailedFlowError
        return not is_special_exc


@after_setup_logger.connect
def attach_flow_error_filter(*_, **__):
    # Need to add filter for our custom error that is used to break the celery chain flow.
    # Since it's not exactly exception, it shouldn't be shown to user.
    # Using this hook in order to avoid messing with whole logging config.
    filter_ = JobFailedFlowErrFilter(name="exc_filter")
    logging.getLogger("celery.app.trace").addFilter(filter_)


# Tasks

RUN_SCHEDULED_TASK_NAME = "adcm:jobs:task-run-scheduled"
RUN_JOB_TASK_NAME = "adcm:jobs:job-execute"
COMPLETE_TASK_TASK_NAME = "adcm:jobs:task-finalize"
SET_TASK_TO_BROKEN_TASK_NAME = "adcm:jobs:task-set-broken"


@app.task(bind=True, track_started=True)
@di_task
def run_task(*_, task_id: TaskID, task_runner: dishka.FromDishka[TaskRunner], **_kw) -> None:
    task_runner.run(task_id=task_id)


@app.task(bind=True, track_started=True, name=RUN_SCHEDULED_TASK_NAME)
@di_task
def run_scheduled_task(
    self: Task,
    task_id: TaskID,
    environment: dishka.FromDishka[RunnerEnvironment],
    set_task_to_running: dishka.FromDishka[SetTaskToRunning],
    **_,
) -> None:
    result = set_task_to_running.do(task_id, environment=environment)
    plan = prepare_execution_plan(task_id, result.jobs)
    return self.replace(plan)


@app.task(bind=True, name=RUN_JOB_TASK_NAME)
@di_task
def run_job(
    self,
    *_,
    task_id: TaskID,
    job_id: JobID,
    run_job: dishka.FromDishka[RunJob],
    environment: dishka.FromDishka[RunnerEnvironment],
    repo: dishka.FromDishka[JobRepoI],
    **__,
) -> None:
    repo.update_job(id=job_id, data=JobUpdateDTO(executor={"environment": "celery", "worker_id": self.request.id}))
    result = run_job.do(task_id=task_id, job_id=job_id, environment=environment)
    if result not in (ExecutionStatus.SUCCESS, ExecutionStatus.ABORTED):
        raise JobFailedFlowError(task_id=task_id, job_id=job_id, final_status=result)


@app.task(bind=True, name=COMPLETE_TASK_TASK_NAME)
@di_task
def complete_task(
    *_,
    task_id: TaskID,
    finalize_task: dishka.FromDishka[FinalizeTask],
    environment: dishka.FromDishka[RunnerEnvironment],
    **__,
) -> None:
    finalize_task.do(task_id=task_id, environment=environment)


@app.task(bind=True, name=SET_TASK_TO_BROKEN_TASK_NAME)
@di_task
def set_task_to_broken(
    *_,
    task_id: TaskID,
    set_task_broken: dishka.FromDishka[MarkTaskBroken],
    environment: dishka.FromDishka[RunnerEnvironment],
    **__,
) -> None:
    set_task_broken.do(task_id=task_id, environment=environment)


def prepare_execution_plan(task_id: TaskID, jobs: PlannedJobs) -> Signature:
    task_info = {"task_id": task_id}
    set_broken_task_sig = signature(SET_TASK_TO_BROKEN_TASK_NAME, kwargs=task_info, immutable=True)
    # hint silenced in here, it's unclear if signature can be truely none in here
    complete_task_sig = signature(COMPLETE_TASK_TASK_NAME, kwargs=task_info, immutable=True).on_error(  # pyright: ignore[reportOptionalMemberAccess]
        set_broken_task_sig
    )
    return chain(
        *(signature(RUN_JOB_TASK_NAME, kwargs=task_info | {"job_id": job.id}, immutable=True) for job in jobs),
        complete_task_sig,
    ).on_error(complete_task_sig)
