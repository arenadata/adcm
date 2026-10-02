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

from datetime import datetime, timedelta, timezone
from unittest import TestCase

from core.action.job.operations import calculate_owner_state_changes, calculate_task_final_status
from core.action.types import (
    AnsibleScript,
    AnsibleScriptParams,
    ExecutionStatus,
    JobShortInfo,
    RichJob,
    RuntimeDates,
    ScriptSpec,
    ScriptType,
    StateChanges,
    WorkerInfo,
)
from core.result import Fail, Success
from core.spec.types import FullSpecKey
from core.types import Names

S = ExecutionStatus
ON_SUCCESS = StateChanges(state="done", multi_state_set=("s1",), multi_state_unset=("u1",))
ON_FAIL = StateChanges(state="task_failed", multi_state_set=("tf",), multi_state_unset=("tu",))
START = datetime(2026, 1, 1, tzinfo=timezone.utc)

JobEntry = (
    ExecutionStatus
    | tuple[ExecutionStatus, StateChanges | None]
    | tuple[ExecutionStatus, StateChanges | None, datetime | None]
)


def make_job(
    status: ExecutionStatus,
    on_fail: StateChanges | None = None,
    index: int = 0,
    finish: datetime | None = None,
) -> RichJob:
    key = FullSpecKey(f"/{index}-job{index}")
    spec = ScriptSpec(
        key=key,
        names=Names(internal=f"job{index}"),
        script=AnsibleScript(type=ScriptType.ANSIBLE, path="a.yaml", params=AnsibleScriptParams()),
        on_fail=on_fail or StateChanges(),
    )
    runtime = JobShortInfo(
        id=index + 1,
        task_id=1,
        spec_key=key,
        dates=RuntimeDates(finish=finish),
        worker=WorkerInfo(),
        status=status,
    )
    return RichJob(spec=spec, runtime=runtime)


def make_jobs(*entries: JobEntry) -> list[RichJob]:
    """Jobs finish in plan order unless finish date is given explicitly"""

    jobs = []
    for index, entry in enumerate(entries):
        match entry:
            case (status, on_fail, finish):
                pass
            case (status, on_fail):
                finish = START + timedelta(minutes=index)
            case status:
                on_fail, finish = None, START + timedelta(minutes=index)

        jobs.append(make_job(status=status, on_fail=on_fail, index=index, finish=finish))

    return jobs


class TestCalculateTaskFinalStatus(TestCase):
    def test_task_aborted_wins_over_everything(self):
        for statuses in ([S.SUCCESS], [S.FAILED], [S.CREATED], []):
            with self.subTest(statuses=statuses):
                self.assertEqual(calculate_task_final_status(statuses, task_is_aborted=True), Success(S.ABORTED))

    def test_nothing_final_is_fail(self):
        for statuses in (
            [],
            [S.CREATED, S.CREATED],
            [S.CREATED, S.RUNNING, S.SCHEDULED, S.QUEUED, S.REVOKING, S.TERMINATING, S.BROKEN],
        ):
            with self.subTest(statuses=statuses):
                result = calculate_task_final_status(statuses, task_is_aborted=False)

                self.assertIsInstance(result, Fail)
                self.assertIsInstance(result.value, str)
                self.assertTrue(result.value)

    def test_aborted_like_only_is_aborted(self):
        for statuses in ([S.ABORTED], [S.REVOKED], [S.ABORTED, S.REVOKED], [S.REVOKED, S.ABORTED, S.CREATED]):
            with self.subTest(statuses=statuses):
                self.assertEqual(calculate_task_final_status(statuses, task_is_aborted=False), Success(S.ABORTED))

    def test_failed_anywhere_is_failed(self):
        for statuses in (
            [S.FAILED],
            [S.FAILED, S.SUCCESS],
            [S.SUCCESS, S.FAILED, S.SUCCESS],
            [S.SUCCESS, S.ABORTED, S.FAILED],
            [S.REVOKED, S.FAILED, S.CREATED],
        ):
            with self.subTest(statuses=statuses):
                self.assertEqual(calculate_task_final_status(statuses, task_is_aborted=False), Success(S.FAILED))

    def test_success_combinations(self):
        for statuses in (
            [S.SUCCESS],
            [S.SUCCESS, S.SUCCESS],
            [S.SUCCESS, S.ABORTED],
            [S.ABORTED, S.SUCCESS],
            [S.SUCCESS, S.REVOKED],
            [S.REVOKED, S.SUCCESS, S.ABORTED],
            [S.SUCCESS, S.CREATED, S.RUNNING],
            [S.CREATED, S.SUCCESS, S.BROKEN],
        ):
            with self.subTest(statuses=statuses):
                self.assertEqual(calculate_task_final_status(statuses, task_is_aborted=False), Success(S.SUCCESS))

    def test_accepts_any_iterable(self):
        result = calculate_task_final_status((status for status in (S.SUCCESS, S.FAILED)), task_is_aborted=False)

        self.assertEqual(result, Success(S.FAILED))


class TestCalculateOwnerStateChanges(TestCase):
    def calculate(self, result: ExecutionStatus, jobs: list[RichJob]) -> StateChanges:
        return calculate_owner_state_changes(result, jobs, on_success=ON_SUCCESS, on_fail=ON_FAIL)  # pyright: ignore[reportArgumentType]

    def test_success_uses_task_on_success(self):
        self.assertEqual(self.calculate(S.SUCCESS, make_jobs(S.SUCCESS, S.SUCCESS)), ON_SUCCESS)

    def test_success_ignores_job_on_fail(self):
        jobs = make_jobs((S.SUCCESS, StateChanges(state="x")))

        self.assertEqual(self.calculate(S.SUCCESS, jobs), ON_SUCCESS)

    def test_failed_takes_on_fail_of_latest_finished_failed_job(self):
        latest = StateChanges(state="x", multi_state_set=("a",), multi_state_unset=("p",))
        jobs = make_jobs(
            (S.FAILED, latest, START + timedelta(hours=1)),
            (S.FAILED, StateChanges(state="y", multi_state_set=("b",), multi_state_unset=("q",)), START),
        )

        self.assertEqual(self.calculate(S.FAILED, jobs), latest)

    def test_failed_same_finish_date_is_resolved_by_greater_id(self):
        jobs = [
            make_job(S.FAILED, on_fail=StateChanges(state="x"), index=1, finish=START),
            make_job(S.FAILED, on_fail=StateChanges(state="y"), index=0, finish=START),
        ]

        self.assertEqual(self.calculate(S.FAILED, jobs).state, "x")

    def test_failed_later_failed_job_with_empty_on_fail_is_skipped(self):
        jobs = make_jobs(
            (S.FAILED, StateChanges(state="x", multi_state_set=("a",)), START),
            (S.FAILED, StateChanges(), START + timedelta(hours=1)),
        )

        changes = self.calculate(S.FAILED, jobs)

        self.assertEqual(changes, StateChanges(state="x", multi_state_set=("a",), multi_state_unset=("tu",)))

    def test_failed_on_fail_of_other_failed_jobs_is_ignored(self):
        jobs = make_jobs(
            (S.FAILED, StateChanges(state="x", multi_state_set=("a",))),
            (S.FAILED, StateChanges(multi_state_set=("b",), multi_state_unset=("q",))),
        )

        changes = self.calculate(S.FAILED, jobs)

        self.assertEqual(changes, StateChanges(state="task_failed", multi_state_set=("b",), multi_state_unset=("q",)))

    def test_failed_on_fail_of_non_failed_job_is_ignored(self):
        jobs = make_jobs(
            (S.FAILED, StateChanges(state="x")),
            (S.SUCCESS, StateChanges(state="ok", multi_state_set=("skip",))),
        )

        self.assertEqual(
            self.calculate(S.FAILED, jobs), StateChanges(state="x", multi_state_set=("tf",), multi_state_unset=("tu",))
        )

    def test_failed_each_field_falls_back_to_task_on_fail_independently(self):
        for job_on_fail, expected in (
            (StateChanges(state="x"), StateChanges(state="x", multi_state_set=("tf",), multi_state_unset=("tu",))),
            (
                StateChanges(multi_state_set=("a",)),
                StateChanges(state="task_failed", multi_state_set=("a",), multi_state_unset=("tu",)),
            ),
            (
                StateChanges(multi_state_unset=("p",)),
                StateChanges(state="task_failed", multi_state_set=("tf",), multi_state_unset=("p",)),
            ),
        ):
            with self.subTest(job_on_fail=job_on_fail):
                self.assertEqual(self.calculate(S.FAILED, make_jobs((S.FAILED, job_on_fail))), expected)

    def test_failed_without_job_on_fail_falls_back_to_task_on_fail(self):
        self.assertEqual(self.calculate(S.FAILED, make_jobs(S.SUCCESS, S.FAILED)), ON_FAIL)

    def test_failed_candidate_without_finish_date_raises(self):
        jobs = [make_job(S.FAILED, on_fail=StateChanges(state="x"), finish=None)]

        with self.assertRaises(RuntimeError):
            self.calculate(S.FAILED, jobs)

    def test_failed_candidates_without_finish_date_lose_to_finished_one(self):
        jobs = make_jobs(
            (S.FAILED, StateChanges(state="x"), START),
            (S.FAILED, StateChanges(state="y"), None),
        )

        self.assertEqual(self.calculate(S.FAILED, jobs).state, "x")

    def test_failed_several_candidates_without_finish_date_raise(self):
        jobs = make_jobs(
            (S.FAILED, StateChanges(state="x"), None),
            (S.FAILED, StateChanges(state="y"), None),
        )

        with self.assertRaises(RuntimeError):
            self.calculate(S.FAILED, jobs)

    def test_failed_job_with_empty_on_fail_and_no_finish_date_is_ignored(self):
        jobs = [make_job(S.FAILED, finish=None)]

        self.assertEqual(self.calculate(S.FAILED, jobs), ON_FAIL)

    def test_aborted_is_no_change(self):
        self.assertEqual(self.calculate(S.ABORTED, make_jobs(S.SUCCESS, S.ABORTED)), StateChanges())


class TestStateChangesIsEmpty(TestCase):
    def test_nothing_set_is_empty(self):
        self.assertTrue(StateChanges().is_empty)

    def test_any_field_set_is_not_empty(self):
        for changes in (
            StateChanges(state="x"),
            StateChanges(multi_state_set=("a",)),
            StateChanges(multi_state_unset=("a",)),
        ):
            with self.subTest(changes=changes):
                self.assertFalse(changes.is_empty)
