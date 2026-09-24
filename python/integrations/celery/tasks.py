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


from collections.abc import Mapping
from functools import reduce
import logging
import operator

from celery import Task, chain, chord, shared_task, signature
from celery.canvas import Signature
from core.action import ExecutionStatus
from core.action.job import JobRepoI, JobUpdateDTO
from core.action.types import ExecutionStyle, JobHierarchyLevel, JobSpecV1, RichJob
from core.legacy.job.runners import RunnerEnvironment
from core.spec.keys import level_keys_to_full_key
from core.spec.types import FullSpecKey, LevelSpecKey
from core.types import JobID, TaskID
from use_cases.job.run import FinalizeTask, MarkTaskBroken, RunJob, SetTaskToRunning
import dishka

from integrations.celery.di import di_task
from integrations.celery.errors import JobFailedFlowError

RUN_SCHEDULED_TASK_NAME = "adcm:jobs:task-run-scheduled"
RUN_JOB_TASK_NAME = "adcm:jobs:job-execute"
COMPLETE_TASK_TASK_NAME = "adcm:jobs:task-finalize"
SET_TASK_TO_BROKEN_TASK_NAME = "adcm:jobs:task-set-broken"
GROUP_FINISHED_TASK_NAME = "adcm:jobs:group-finished"

logger = logging.getLogger("worker.celery")


@shared_task(bind=True, track_started=True, name=RUN_SCHEDULED_TASK_NAME)
@di_task
def run_scheduled_task(
    self: Task,
    task_id: TaskID,
    environment: dishka.FromDishka[RunnerEnvironment],
    set_task_to_running: dishka.FromDishka[SetTaskToRunning],
    **_,
) -> None:
    result = set_task_to_running.do(task_id, environment=environment)
    plan = prepare_execution_plan(task_id=task_id, plan=result.plan, jobs=result.jobs)
    return self.replace(plan)


@shared_task(bind=True, name=RUN_JOB_TASK_NAME)
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
    # only failed job stops the plan (or branch of parallel group): it continues after aborted job,
    # and revoked job (not executed at all) is just skipped
    if result == ExecutionStatus.FAILED:
        raise JobFailedFlowError(task_id=task_id, job_id=job_id, final_status=result)


@shared_task(bind=True, name=COMPLETE_TASK_TASK_NAME)
@di_task
def complete_task(
    *_,
    task_id: TaskID,
    finalize_task: dishka.FromDishka[FinalizeTask],
    environment: dishka.FromDishka[RunnerEnvironment],
    **__,
) -> None:
    finalize_task.do(task_id=task_id, environment=environment)


@shared_task(bind=True, name=SET_TASK_TO_BROKEN_TASK_NAME)
@di_task
def set_task_to_broken(
    *_,
    task_id: TaskID,
    set_task_broken: dishka.FromDishka[MarkTaskBroken],
    environment: dishka.FromDishka[RunnerEnvironment],
    **__,
) -> None:
    set_task_broken.do(task_id=task_id, environment=environment)


@shared_task(name=GROUP_FINISHED_TASK_NAME)
def log_group_finished(*args, group_key: FullSpecKey, **kwargs) -> None:
    # temporary callback of parallel group's chord, for debug purposes only
    logger.info('Called for group with key "%s": args=%r kwargs=%r', group_key, args, kwargs)


def prepare_execution_plan(task_id: TaskID, plan: JobSpecV1, jobs: Mapping[FullSpecKey, RichJob]) -> Signature:
    """
    Build celery canvas out of execution plan.
    Sequential levels become chains, parallel ones become chords.

    Celery merges nested chains into one and moves steps that follow chord into its body.
    It doesn't change the order of execution, but errbacks attached before that may be lost,
    so task finalization is attached only after the whole canvas is built:
    - errback of every top-level step, for chord it's its body;
    - success callback of the last top-level step.
    Nothing within chord header gets finalization,
    so failed job stops only its own branch and task is finalized once all branches are finished.

    Why `chord`, not `group`:
    group has no body to carry errback, and nothing waits for all its branches to finish.
    Celery upgrades group into chord only when something follows it within chain,
    so group at the end of plan calls success callback per branch,
    and failure within it never finalizes task.

    Prepared against celery 5.6.3 with database (PostgreSQL) result backend.

    Caveats:
    - chord's header failure is detected by `chord_unlock` polling of stored results,
      so task is finalized with a delay after the last branch is finished;
    - backends with native chord support (e.g. Redis) handle chords differently
      and must be rechecked before use;
    - parallel group within parallel one isn't allowed by bundle validation and isn't rechecked here.
      It may hang or finalize task early, especially on backends with native chord support;
    - `task_allow_error_cb_on_chord_header` isn't relied on, errbacks are attached explicitly.
    """

    task_info = {"task_id": task_id}
    set_broken_task_sig = signature(SET_TASK_TO_BROKEN_TASK_NAME, kwargs=task_info, immutable=True)
    # hint silenced in here, it's unclear if signature can be truely none in here
    complete_task_sig = signature(COMPLETE_TASK_TASK_NAME, kwargs=task_info, immutable=True).on_error(  # pyright: ignore[reportOptionalMemberAccess]
        set_broken_task_sig
    )

    # root level is sequential by definition, so it's always a chain
    entries = _level_entries(level=plan.hierarchy, group_levels=(), plan=plan, task_info=task_info, jobs=jobs)
    root = _join_sequentially(entries)

    # celery types chain as plain `Signature` and chord's body as optional,
    # hints are silenced, since chain and body are always built above
    for step in root.tasks:  # pyright: ignore[reportAttributeAccessIssue]
        (step.body if isinstance(step, chord) else step).link_error(complete_task_sig)  # pyright: ignore[reportOptionalMemberAccess]

    # Linked to the last step, not to the chain:
    # `Task.replace` copies chain-level links onto the last step without removing them from the chain,
    # so they'd be applied twice, which is avoided by last step link.
    root.tasks[-1].link(complete_task_sig)  # pyright: ignore[reportAttributeAccessIssue]

    return root


def _level_entries(
    level: JobHierarchyLevel,
    group_levels: tuple[LevelSpecKey, ...],
    plan: JobSpecV1,
    task_info: dict,
    jobs: Mapping[FullSpecKey, RichJob],
) -> list[Signature]:
    entries = []
    for level_key in level.fields:
        own_levels = (*group_levels, level_key)
        key = level_keys_to_full_key(own_levels)

        if level_key not in level.child_groups:
            job_id = jobs[key].runtime.id
            entries.append(signature(RUN_JOB_TASK_NAME, kwargs=task_info | {"job_id": job_id}, immutable=True))
            continue

        group = plan.groups[key]
        group_entries = _level_entries(
            level=level.child_groups[level_key], group_levels=own_levels, plan=plan, task_info=task_info, jobs=jobs
        )

        match group.type:
            case ExecutionStyle.SEQUENTIAL:
                entries.append(_join_sequentially(group_entries))
            case ExecutionStyle.PARALLEL:
                # body does nothing meaningful yet, but it's required for correct flow:
                # errbacks on header failure and success callback of the last step are attached to it
                callback_sig = signature(
                    GROUP_FINISHED_TASK_NAME, kwargs=task_info | {"group_key": group.key}, immutable=True
                )
                entries.append(chord(group_entries, body=callback_sig))
            case _:
                message = f'Can\'t build celery canvas for group "{group.key}" of "{group.type.value}" execution style'
                raise NotImplementedError(message)

    return entries


def _join_sequentially(entries: list[Signature]) -> Signature:
    # joined with `|` starting from empty chain, so result is always a flat chain:
    # `chain(x)` with a single entry keeps nested chain as is
    return reduce(operator.or_, entries, chain())
