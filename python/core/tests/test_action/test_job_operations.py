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

from unittest import TestCase

from core.action.job.operations import calculate_owner_state_changes, calculate_task_final_status
from core.action.types import (
    AnsibleScript,
    AnsibleScriptParams,
    ExecutionStatus,
    JobShortInfo,
    RichJob,
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


def make_job(status: ExecutionStatus, on_fail: StateChanges | None = None, index: int = 0) -> RichJob:
    key = FullSpecKey(f"/job{index}")
    spec = ScriptSpec(
        key=key,
        names=Names(internal=f"job{index}"),
        script=AnsibleScript(type=ScriptType.ANSIBLE, path="a.yaml", params=AnsibleScriptParams()),
        on_fail=on_fail or StateChanges(),
    )
    runtime = JobShortInfo(id=index + 1, task_id=1, spec_key=key, finish_date=None, worker=WorkerInfo(), status=status)
    return RichJob(spec=spec, runtime=runtime)


def make_jobs(*entries: tuple[ExecutionStatus, StateChanges | None] | ExecutionStatus) -> list[RichJob]:
    jobs = []
    for index, entry in enumerate(entries):
        status, on_fail = entry if isinstance(entry, tuple) else (entry, None)
        jobs.append(make_job(status=status, on_fail=on_fail, index=index))

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

    def test_failed_takes_state_of_first_failed_job_having_it(self):
        jobs = make_jobs(
            (S.FAILED, StateChanges()),
            (S.FAILED, StateChanges(state="x")),
            (S.FAILED, StateChanges(state="y")),
        )

        self.assertEqual(self.calculate(S.FAILED, jobs).state, "x")

    def test_failed_state_of_non_failed_job_is_ignored(self):
        jobs = make_jobs((S.SUCCESS, StateChanges(state="ok")), (S.FAILED, StateChanges(state="x")))

        self.assertEqual(self.calculate(S.FAILED, jobs).state, "x")

    def test_failed_multi_states_are_union_over_failed_jobs(self):
        jobs = make_jobs(
            (S.FAILED, StateChanges(multi_state_set=("a", "b"), multi_state_unset=("p",))),
            (S.SUCCESS, StateChanges(multi_state_set=("skip",), multi_state_unset=("skip",))),
            (S.FAILED, StateChanges(multi_state_set=("b", "c"), multi_state_unset=("q", "p"))),
        )

        changes = self.calculate(S.FAILED, jobs)

        self.assertEqual(sorted(changes.multi_state_set), ["a", "b", "c"])
        self.assertEqual(sorted(changes.multi_state_unset), ["p", "q"])

    def test_failed_set_and_unset_are_resolved_independently(self):
        jobs = make_jobs((S.FAILED, StateChanges(multi_state_set=("a",))))

        changes = self.calculate(S.FAILED, jobs)

        self.assertEqual(changes.multi_state_set, ("a",))
        self.assertEqual(changes.multi_state_unset, ON_FAIL.multi_state_unset)

    def test_failed_several_failed_first_has_no_state(self):
        jobs = make_jobs(
            (S.FAILED, StateChanges(multi_state_set=("a",))),
            (S.FAILED, StateChanges(state="x", multi_state_set=("b",))),
        )

        changes = self.calculate(S.FAILED, jobs)

        self.assertEqual(changes.state, "x")
        self.assertEqual(sorted(changes.multi_state_set), ["a", "b"])
        self.assertEqual(changes.multi_state_unset, ON_FAIL.multi_state_unset)

    def test_failed_without_job_on_fail_falls_back_to_task_on_fail(self):
        self.assertEqual(self.calculate(S.FAILED, make_jobs(S.SUCCESS, S.FAILED)), ON_FAIL)

    def test_aborted_is_no_change(self):
        self.assertEqual(self.calculate(S.ABORTED, make_jobs(S.SUCCESS, S.ABORTED)), StateChanges())
