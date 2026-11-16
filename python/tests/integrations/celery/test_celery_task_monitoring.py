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

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal
from unittest import TestCase
from unittest.mock import Mock, patch

from core.action import (
    ActionShortInfo,
    ExecutionStatus,
    JobShortInfo,
    RuntimeDates,
    TaskRunnerEnvironment,
    TaskShortInfo,
    WorkerInfo,
)
from core.action.job import JobRepoI
from core.action.scheduler import TaskLivenessStatus
from core.spec.types import FullSpecKey
from core.types import JobID
from integrations.celery import scheduler
from integrations.celery.pg.kombu import TaskMessageSnapshot

from celery import Celery

# Fixed time origin: each monitoring pass and expected job timer uses an offset from this instant.
MONITOR_STARTED = datetime(2026, 1, 1, tzinfo=timezone.utc)
# Single task shared by all scenarios; its jobs and tracking sources vary between monitoring passes.
MONITOR_TASK = TaskShortInfo(
    id=42,
    worker=WorkerInfo(environment=TaskRunnerEnvironment.CELERY, worker_id="task-42"),
    status=ExecutionStatus.RUNNING,
    lock_id=None,
    action=ActionShortInfo(id=1, name="parallel_jobs", venv="default"),
)


def monitor_job(job_id: JobID, status: ExecutionStatus, worker_id: str | None) -> JobShortInfo:
    """Build a job for the single task used in analyze_liveness scenarios."""
    return JobShortInfo(
        id=job_id,
        task_id=MONITOR_TASK.id,
        spec_key=FullSpecKey(f"/job-{job_id}"),
        dates=RuntimeDates(),
        worker=WorkerInfo(environment=TaskRunnerEnvironment.CELERY, worker_id=worker_id),
        status=status,
    )


InterruptionMode = Literal["any_job_lost", "all_jobs_lost"]


def untracked_job(job_id: JobID, since_seconds: int, status: ExecutionStatus) -> scheduler.UntrackedJob:
    """Describe an expected timer using seconds from the fixed scenario start."""
    return scheduler.UntrackedJob(id=job_id, since=MONITOR_STARTED + timedelta(seconds=since_seconds), status=status)


@dataclass(frozen=True)
class LivenessPass:
    seconds: int
    jobs: tuple[JobShortInfo, ...]
    # A single expectation applies to both modes; a mapping makes mode-specific differences explicit.
    expected: TaskLivenessStatus | dict[InterruptionMode, TaskLivenessStatus]
    # Empty by default: ALIVE tasks must have no saved UNKNOWN state.
    expected_unknown: (
        tuple[scheduler.UntrackedJob, ...] | dict[InterruptionMode, tuple[scheduler.UntrackedJob, ...]]
    ) = ()
    messages: tuple[TaskMessageSnapshot, ...] = ()
    active: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    def list_messages(self) -> list[TaskMessageSnapshot]:
        """Replace the Kombu database read while keeping real MessageIndex construction."""
        return list(self.messages)


@dataclass(frozen=True)
class LivenessCase:
    description: str
    passes: tuple[LivenessPass, ...]


LIVENESS_CASES = (
    LivenessCase(
        description="ALIVE: finished jobs and an unsubmitted CREATED job are ignored",
        passes=(
            LivenessPass(
                seconds=0,
                jobs=(
                    monitor_job(10, ExecutionStatus.SUCCESS, "job-10"),
                    monitor_job(11, ExecutionStatus.FAILED, "job-11"),
                    monitor_job(12, ExecutionStatus.CREATED, None),
                ),
                expected=TaskLivenessStatus.ALIVE,
            ),
        ),
    ),
    LivenessCase(
        description="ALIVE: all unfinished jobs are present in active inspect replies",
        passes=(
            LivenessPass(
                seconds=0,
                jobs=(
                    monitor_job(10, ExecutionStatus.RUNNING, "job-10"),
                    monitor_job(11, ExecutionStatus.REVOKING, "job-11"),
                ),
                active={"worker-1": [{"id": "job-10"}, {"id": "job-11"}]},
                expected=TaskLivenessStatus.ALIVE,
            ),
        ),
    ),
    LivenessCase(
        description="ALIVE: ADCM job IDs match messages even with absent or different worker IDs",
        passes=(
            LivenessPass(
                seconds=0,
                jobs=(
                    monitor_job(10, ExecutionStatus.QUEUED, None),
                    monitor_job(11, ExecutionStatus.SCHEDULED, "job-11"),
                ),
                messages=(
                    TaskMessageSnapshot(visible=True, timestamp=None, adcm_job_id=10),
                    TaskMessageSnapshot(visible=False, timestamp=None, adcm_job_id=11, celery_task_id="other-id"),
                ),
                expected=TaskLivenessStatus.ALIVE,
            ),
        ),
    ),
    LivenessCase(
        description="ALIVE: Celery IDs match messages without matching ADCM job IDs",
        passes=(
            LivenessPass(
                seconds=0,
                jobs=(
                    monitor_job(10, ExecutionStatus.QUEUED, "job-10"),
                    monitor_job(11, ExecutionStatus.CREATED, "job-11"),
                ),
                messages=(
                    TaskMessageSnapshot(visible=True, timestamp=None, celery_task_id="job-10"),
                    TaskMessageSnapshot(visible=False, timestamp=None, celery_task_id="job-11", adcm_job_id=999),
                ),
                expected=TaskLivenessStatus.ALIVE,
            ),
        ),
    ),
    LivenessCase(
        description="ALIVE: active inspect, ADCM message ID and Celery message ID track different jobs",
        passes=(
            LivenessPass(
                seconds=0,
                jobs=(
                    monitor_job(10, ExecutionStatus.RUNNING, "job-10"),
                    monitor_job(11, ExecutionStatus.QUEUED, None),
                    monitor_job(12, ExecutionStatus.SCHEDULED, "job-12"),
                ),
                active={"worker-1": [{"id": "job-10"}]},
                messages=(
                    TaskMessageSnapshot(visible=True, timestamp=None, adcm_job_id=11),
                    TaskMessageSnapshot(visible=False, timestamp=None, celery_task_id="job-12"),
                ),
                expected=TaskLivenessStatus.ALIVE,
            ),
        ),
    ),
    LivenessCase(
        description="UNKNOWN: task-level and unrelated message IDs do not confirm jobs",
        passes=(
            LivenessPass(
                seconds=0,
                jobs=(
                    monitor_job(10, ExecutionStatus.QUEUED, None),
                    monitor_job(11, ExecutionStatus.RUNNING, "job-11"),
                ),
                active={"worker-1": [{"id": "task-42"}]},
                messages=(
                    TaskMessageSnapshot(visible=True, timestamp=None, adcm_task_id=42, celery_task_id="task-42"),
                    TaskMessageSnapshot(visible=False, timestamp=None, adcm_job_id=999, celery_task_id="unrelated"),
                    TaskMessageSnapshot(visible=True, timestamp=None),
                ),
                expected=TaskLivenessStatus.UNKNOWN,
                expected_unknown=(
                    untracked_job(10, 0, ExecutionStatus.QUEUED),
                    untracked_job(11, 0, ExecutionStatus.RUNNING),
                ),
            ),
        ),
    ),
    LivenessCase(
        description="UNKNOWN then DEAD: no jobs tracked; expiry occurs exactly at the 3-second trust gap",
        passes=(
            LivenessPass(
                seconds=0,
                jobs=(
                    monitor_job(10, ExecutionStatus.RUNNING, "job-10"),
                    monitor_job(11, ExecutionStatus.QUEUED, None),
                ),
                expected=TaskLivenessStatus.UNKNOWN,
                expected_unknown=(
                    untracked_job(10, 0, ExecutionStatus.RUNNING),
                    untracked_job(11, 0, ExecutionStatus.QUEUED),
                ),
            ),
            LivenessPass(
                seconds=2,
                jobs=(
                    monitor_job(10, ExecutionStatus.RUNNING, "job-10"),
                    monitor_job(11, ExecutionStatus.QUEUED, None),
                ),
                expected=TaskLivenessStatus.UNKNOWN,
                expected_unknown=(
                    untracked_job(10, 0, ExecutionStatus.RUNNING),
                    untracked_job(11, 0, ExecutionStatus.QUEUED),
                ),
            ),
            LivenessPass(
                seconds=3,
                jobs=(
                    monitor_job(10, ExecutionStatus.RUNNING, "job-10"),
                    monitor_job(11, ExecutionStatus.QUEUED, None),
                ),
                expected=TaskLivenessStatus.DEAD,
                expected_unknown=(
                    untracked_job(10, 0, ExecutionStatus.RUNNING),
                    untracked_job(11, 0, ExecutionStatus.QUEUED),
                ),
            ),
        ),
    ),
    LivenessCase(
        description="UNKNOWN: a status change restarts the timer even when the previous timer has expired",
        passes=(
            LivenessPass(
                seconds=0,
                jobs=(
                    monitor_job(10, ExecutionStatus.RUNNING, "job-10"),
                    monitor_job(11, ExecutionStatus.SUCCESS, "job-11"),
                ),
                expected=TaskLivenessStatus.UNKNOWN,
                expected_unknown=(untracked_job(10, 0, ExecutionStatus.RUNNING),),
            ),
            LivenessPass(
                seconds=3,
                jobs=(
                    monitor_job(10, ExecutionStatus.TERMINATING, "job-10"),
                    monitor_job(11, ExecutionStatus.SUCCESS, "job-11"),
                ),
                expected=TaskLivenessStatus.UNKNOWN,
                expected_unknown=(untracked_job(10, 3, ExecutionStatus.TERMINATING),),
            ),
            LivenessPass(
                seconds=5,
                jobs=(
                    monitor_job(10, ExecutionStatus.TERMINATING, "job-10"),
                    monitor_job(11, ExecutionStatus.SUCCESS, "job-11"),
                ),
                expected=TaskLivenessStatus.UNKNOWN,
                expected_unknown=(untracked_job(10, 3, ExecutionStatus.TERMINATING),),
            ),
            LivenessPass(
                seconds=6,
                jobs=(
                    monitor_job(10, ExecutionStatus.TERMINATING, "job-10"),
                    monitor_job(11, ExecutionStatus.SUCCESS, "job-11"),
                ),
                expected=TaskLivenessStatus.DEAD,
                expected_unknown=(untracked_job(10, 3, ExecutionStatus.TERMINATING),),
            ),
        ),
    ),
    LivenessCase(
        description="ALIVE: messages restore every missing job, clear timers and allow a fresh UNKNOWN period",
        passes=(
            LivenessPass(
                seconds=0,
                jobs=(
                    monitor_job(10, ExecutionStatus.RUNNING, "job-10"),
                    monitor_job(11, ExecutionStatus.QUEUED, None),
                ),
                expected=TaskLivenessStatus.UNKNOWN,
                expected_unknown=(
                    untracked_job(10, 0, ExecutionStatus.RUNNING),
                    untracked_job(11, 0, ExecutionStatus.QUEUED),
                ),
            ),
            LivenessPass(
                seconds=3,
                jobs=(
                    monitor_job(10, ExecutionStatus.RUNNING, "job-10"),
                    monitor_job(11, ExecutionStatus.QUEUED, None),
                ),
                messages=(
                    TaskMessageSnapshot(visible=False, timestamp=None, celery_task_id="job-10"),
                    TaskMessageSnapshot(visible=True, timestamp=None, adcm_job_id=11),
                ),
                expected=TaskLivenessStatus.ALIVE,
            ),
            LivenessPass(
                seconds=6,
                jobs=(
                    monitor_job(10, ExecutionStatus.RUNNING, "job-10"),
                    monitor_job(11, ExecutionStatus.QUEUED, None),
                ),
                expected=TaskLivenessStatus.UNKNOWN,
                expected_unknown=(
                    untracked_job(10, 6, ExecutionStatus.RUNNING),
                    untracked_job(11, 6, ExecutionStatus.QUEUED),
                ),
            ),
        ),
    ),
    LivenessCase(
        description="UNKNOWN: a finished job cannot keep a missing unfinished job alive",
        passes=(
            LivenessPass(
                seconds=0,
                jobs=(
                    monitor_job(10, ExecutionStatus.CREATED, "job-10"),
                    monitor_job(11, ExecutionStatus.SUCCESS, "job-11"),
                    monitor_job(12, ExecutionStatus.CREATED, None),
                ),
                active={"worker-1": [{"id": "job-11"}]},
                messages=(TaskMessageSnapshot(visible=True, timestamp=None, adcm_job_id=11),),
                expected=TaskLivenessStatus.UNKNOWN,
                expected_unknown=(untracked_job(10, 0, ExecutionStatus.CREATED),),
            ),
        ),
    ),
)


MODE_DEPENDENT_LIVENESS_CASES = (
    LivenessCase(
        description="One recovered job: clear expired timers in all_jobs_lost, remain DEAD in any_job_lost",
        passes=(
            LivenessPass(
                seconds=0,
                jobs=(
                    monitor_job(10, ExecutionStatus.RUNNING, "job-10"),
                    monitor_job(11, ExecutionStatus.RUNNING, "job-11"),
                ),
                expected=TaskLivenessStatus.UNKNOWN,
                expected_unknown=(
                    untracked_job(10, 0, ExecutionStatus.RUNNING),
                    untracked_job(11, 0, ExecutionStatus.RUNNING),
                ),
            ),
            LivenessPass(
                seconds=3,
                jobs=(
                    monitor_job(10, ExecutionStatus.RUNNING, "job-10"),
                    monitor_job(11, ExecutionStatus.RUNNING, "job-11"),
                ),
                active={"worker-1": [{"id": "job-11"}]},
                expected={
                    "all_jobs_lost": TaskLivenessStatus.ALIVE,
                    "any_job_lost": TaskLivenessStatus.DEAD,
                },
                expected_unknown={
                    "all_jobs_lost": (),
                    "any_job_lost": (untracked_job(10, 0, ExecutionStatus.RUNNING),),
                },
            ),
            LivenessPass(
                seconds=6,
                jobs=(
                    monitor_job(10, ExecutionStatus.RUNNING, "job-10"),
                    monitor_job(11, ExecutionStatus.RUNNING, "job-11"),
                ),
                messages=(TaskMessageSnapshot(visible=True, timestamp=None, adcm_job_id=11),),
                expected={
                    "all_jobs_lost": TaskLivenessStatus.ALIVE,
                    "any_job_lost": TaskLivenessStatus.DEAD,
                },
                expected_unknown={
                    "all_jobs_lost": (),
                    "any_job_lost": (untracked_job(10, 0, ExecutionStatus.RUNNING),),
                },
            ),
            LivenessPass(
                seconds=9,
                jobs=(
                    monitor_job(10, ExecutionStatus.RUNNING, "job-10"),
                    monitor_job(11, ExecutionStatus.RUNNING, "job-11"),
                ),
                messages=(TaskMessageSnapshot(visible=False, timestamp=None, celery_task_id="job-11"),),
                expected={
                    "all_jobs_lost": TaskLivenessStatus.ALIVE,
                    "any_job_lost": TaskLivenessStatus.DEAD,
                },
                expected_unknown={
                    "all_jobs_lost": (),
                    "any_job_lost": (untracked_job(10, 0, ExecutionStatus.RUNNING),),
                },
            ),
        ),
    ),
    LivenessCase(
        description="One missing parallel job: ALIVE in all_jobs_lost, UNKNOWN then DEAD in any_job_lost",
        passes=(
            LivenessPass(
                seconds=0,
                jobs=(
                    monitor_job(10, ExecutionStatus.RUNNING, "job-10"),
                    monitor_job(11, ExecutionStatus.RUNNING, "job-11"),
                ),
                active={"worker-1": [{"id": "job-11"}]},
                expected={
                    "all_jobs_lost": TaskLivenessStatus.ALIVE,
                    "any_job_lost": TaskLivenessStatus.UNKNOWN,
                },
                expected_unknown={
                    "all_jobs_lost": (),
                    "any_job_lost": (untracked_job(10, 0, ExecutionStatus.RUNNING),),
                },
            ),
            LivenessPass(
                seconds=3,
                jobs=(
                    monitor_job(10, ExecutionStatus.RUNNING, "job-10"),
                    monitor_job(11, ExecutionStatus.RUNNING, "job-11"),
                ),
                messages=(TaskMessageSnapshot(visible=True, timestamp=None, adcm_job_id=11),),
                expected={
                    "all_jobs_lost": TaskLivenessStatus.ALIVE,
                    "any_job_lost": TaskLivenessStatus.DEAD,
                },
                expected_unknown={
                    "all_jobs_lost": (),
                    "any_job_lost": (untracked_job(10, 0, ExecutionStatus.RUNNING),),
                },
            ),
        ),
    ),
)


class TestCeleryTaskMonitorAnalyzeLiveness(TestCase):
    """Exercise the complete monitoring algorithm through analyze_liveness only."""

    def run_pass(
        self, monitor: scheduler.CeleryTaskMonitor, step: LivenessPass, *, celery: Mock, job_repo: Mock
    ) -> None:
        """Execute one monitoring pass using the scenario's data and simulated time.

        1. Configure inspect replies, repository jobs and Kombu messages for this step.
        2. Set the current time to MONITOR_STARTED + step.seconds without real waiting.
        3. Call analyze_liveness on the existing monitor, preserving state from earlier passes.
        4. Check the reported status and complete unknown_state_tasks against explicit expectations.

        Expected timers are only used for comparison; the monitor creates, updates and clears its own state.
        """
        inspect = celery.control.inspect.return_value
        inspect.reserved.return_value = {}
        inspect.scheduled.return_value = {}
        inspect.active.return_value = step.active

        job_repo.find_jobs_short.return_value = step.jobs
        with (
            patch("integrations.celery.scheduler.list_messages", side_effect=step.list_messages),
            patch("integrations.celery.scheduler.datetime", wraps=datetime) as clock,
        ):
            clock.now.return_value = MONITOR_STARTED + timedelta(seconds=step.seconds)
            report = monitor.analyze_liveness(iter((MONITOR_TASK,)))

        expectation = (
            step.expected[monitor.task_interruption_mode] if isinstance(step.expected, dict) else step.expected
        )
        self.assertEqual(report, {expectation: [MONITOR_TASK]})
        expected_unknown = (
            step.expected_unknown[monitor.task_interruption_mode]
            if isinstance(step.expected_unknown, dict)
            else step.expected_unknown
        )
        self.assertEqual(
            monitor.unknown_state_tasks,
            {MONITOR_TASK.id: list(expected_unknown)} if expected_unknown else {},
        )

    def run_cases(self, cases: tuple[LivenessCase, ...]) -> None:
        """Run each scenario through the public monitoring entry point.

        1. Select a scenario with explicit job data, tracking sources and expected statuses.
        2. Run it in both interruption modes, creating fresh mocks and a monitor for each mode.
        3. Execute its passes on the same monitor to preserve UNKNOWN timers between passes.
        4. Mock time for each pass and check the reported status and saved job timers without real waiting.
        5. Label subtests with the scenario, mode and time to identify failing passes.
        """
        for case in cases:
            for mode in ("any_job_lost", "all_jobs_lost"):
                with self.subTest(case=case.description, mode=mode):
                    celery = Mock(spec=Celery)
                    job_repo = Mock(spec=JobRepoI)
                    monitor = scheduler.CeleryTaskMonitor(
                        celery=celery,
                        job_repo=job_repo,
                        trust_gap=scheduler.CeleryMonitorTrustGap(timedelta(seconds=3)),
                        task_interruption_mode=mode,
                    )
                    for step in case.passes:
                        with self.subTest(seconds=step.seconds):
                            self.run_pass(monitor, step, celery=celery, job_repo=job_repo)

    def test_analyze_liveness_scenarios(self):
        self.run_cases(LIVENESS_CASES)

    def test_analyze_liveness_mode_differences(self):
        self.run_cases(MODE_DEPENDENT_LIVENESS_CASES)
