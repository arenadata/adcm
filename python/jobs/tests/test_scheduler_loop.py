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

from contextlib import contextmanager, nullcontext
from unittest import TestCase
from unittest.mock import Mock, patch
import logging

from core.action import ExecutionStatus
from core.action.scheduler import BusyAwareLimiter, FixedRateLimiter
from core.result import Fail, Success
from unittest_parametrize import ParametrizedTestCase, param, parametrize
from use_cases.job import scheduler
from use_cases.job.scheduler import Killer, Launcher, Monitor

from jobs.scheduler.run import SchedulerLoop


class StopLoop(BaseException):
    """Ends the endless loop in tests: it is not an Exception, so the loop does not catch it"""


class FakeClock:
    def __init__(self) -> None:
        self.ticks = 0

    def sleep_until_next_tick(self) -> None:
        self.ticks += 1


class Recorder:
    """Limiter and iteration in one: both write what happens into one list"""

    def __init__(self, results: list) -> None:
        self.events = []
        self._results = list(results)

    def tick(self, outcome: Success | Fail) -> None:
        self.events.append(f"tick after {type(outcome).__name__}")

    def do(self) -> Success | Fail:
        if not self._results:
            raise StopLoop

        result = self._results.pop(0)
        self.events.append("do")
        if isinstance(result, Exception):
            raise result

        return result


class TestLimiters(ParametrizedTestCase, TestCase):
    @parametrize(
        ("limiter_class", "outcome", "expected_ticks"),
        [
            param(BusyAwareLimiter, Success(1), 0, id="busy_aware_goes_on_after_work"),
            param(BusyAwareLimiter, Fail("No task to launch"), 1, id="busy_aware_waits_without_work"),
            param(FixedRateLimiter, Success(1), 1, id="fixed_rate_waits_after_work"),
            param(FixedRateLimiter, Fail("No task to launch"), 1, id="fixed_rate_waits_without_work"),
        ],
    )
    def test_tick_sleeps_until_next_tick(
        self, limiter_class: type, outcome: Success | Fail, expected_ticks: int
    ) -> None:
        clock = FakeClock()

        limiter_class(clock=clock).tick(outcome)

        self.assertEqual(clock.ticks, expected_ticks)


class TestSchedulerLoop(TestCase):
    def test_limiter_gets_outcome_of_previous_pass(self) -> None:
        recorder = Recorder(results=[Success(1), Fail("No task to launch"), RuntimeError("DB is gone"), Success(2)])
        loop = SchedulerLoop(
            iteration=recorder,
            limiter=recorder,
            component_name="Test",
            logger=logging.getLogger("test"),
        )

        with self.assertRaises(StopLoop):
            loop.run_in_loop()

        self.assertEqual(
            recorder.events,
            [
                # first pass starts on the first tick
                "tick after Fail",
                "do",
                "tick after Success",
                "do",
                "tick after Fail",
                # failed pass is a pass without work
                "do",
                "tick after Fail",
                "do",
                "tick after Success",
            ],
        )


class TestLauncher(ParametrizedTestCase, TestCase):
    @parametrize(
        ("claimed", "expected_outcome", "expected_step"),
        [
            param(None, Fail("No task to launch"), None, id="nothing_to_launch"),
            param((1, ExecutionStatus.CREATED), Success(1), "schedule_task", id="task_scheduled"),
            param((2, ExecutionStatus.SCHEDULED), Success(2), "queue_task", id="task_queued"),
        ],
    )
    def test_outcome_tells_which_task_was_handled(
        self, claimed: tuple | None, expected_outcome: Success | Fail, expected_step: str | None
    ) -> None:
        @contextmanager
        def claim():
            yield claimed

        launcher = Launcher(
            queuer=Mock(),
            retrieve_start_impossible_reason=Mock(),
            job_repo=Mock(),
            claimer=Mock(claim_first_scheduled_or_created_task=claim),
            scheduler_repo=Mock(),
        )

        with (
            patch.object(scheduler, "atomic", nullcontext),
            patch.object(scheduler, "schedule_task") as schedule_task,
            patch.object(scheduler, "queue_task") as queue_task,
        ):
            outcome = launcher.do()

        self.assertEqual(outcome, expected_outcome)
        steps = {"schedule_task": schedule_task.call_count, "queue_task": queue_task.call_count}
        self.assertEqual(steps, {step: int(step == expected_step) for step in steps})


class TestPeriodicIterations(TestCase):
    def test_killer_without_work_reports_zero(self) -> None:
        job_repo = Mock(find_jobs_short=Mock(return_value=[]), find_tasks_short=Mock(return_value=[]))
        killer = Killer(job_repo=job_repo, claimer=Mock(), registry={})

        self.assertEqual(killer.do(), Success(0))

    def test_monitor_without_work_reports_zero(self) -> None:
        monitor = Monitor(
            set_broken=Mock(),
            running_environment=Mock(),
            registry={},
            job_repo=Mock(find_tasks_short=Mock(return_value=[])),
        )

        self.assertEqual(monitor.do(), Success(0))
