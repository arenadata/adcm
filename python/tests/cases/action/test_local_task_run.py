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

"""
Task executed by the local runner (`JobSequenceRunner`) from start to finish,
jobs' results are imitated by overriding their executors.
"""

from pathlib import Path
from typing import Final

from cm.models import Action, JobLog, TaskLog
from cm.tests.mocks.task_runner import JobImitator
from core.action import ExecutionStatus
from core.legacy.job.executors import Executor
from core.legacy.job.runners import TaskRunner
from core.types import TaskID
from rest_framework.status import HTTP_200_OK
import dishka

from tests.dependencies import MockWithEnvProvider, make_overridden_container
from tests.suites import ADCMDjangoAPISuite

BUNDLES_DIR: Final = Path(__file__).parent / "bundles" / "task_result"

RUN_ACTION_PAYLOAD: Final = {"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False}

PREPARE: Final = "/0"
WITH_ON_FAIL: Final = "/branches/0"
WITHOUT_ON_FAIL: Final = "/branches/1"

# positions of jobs in plan order, as `MockWithEnvProvider` expects them
PREPARE_POSITION: Final = 0
WITH_ON_FAIL_POSITION: Final = 1
WITHOUT_ON_FAIL_POSITION: Final = 2

SUCCESS: Final = ExecutionStatus.SUCCESS
FAILED: Final = ExecutionStatus.FAILED
CREATED: Final = ExecutionStatus.CREATED
REVOKED: Final = ExecutionStatus.REVOKED
ABORTED: Final = ExecutionStatus.ABORTED

INITIAL_STATE: Final = "created"

TERMINATED_CODE: Final = -15

FAILING: Final = JobImitator(return_code=1)
TERMINATED: Final = JobImitator(call=lambda _: TERMINATED_CODE, use_call_return_code=True)


class TestLocalTaskRun(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.bundle = cls.uc.upload_bundle(BUNDLES_DIR / "cluster")
        cls.cluster = cls.uc.add_cluster(bundle=cls.bundle, name="Task Result")
        cls.action = Action.objects.get(prototype=cls.cluster.prototype, name="with_parallel_tail")

    def run_action(self) -> TaskID:
        response = self.client.v2[self.cluster, "actions", self.action, "run"].post(data=RUN_ACTION_PAYLOAD)
        self.assertEqual(response.status_code, HTTP_200_OK, response.json())

        return response.json()["id"]

    def execute_locally(self, task_id: TaskID, container: dishka.Container) -> None:
        self.task_runner(container).launch_task(task_id=task_id)

    def assert_task_status(self, task_id: TaskID, expected: ExecutionStatus) -> None:
        self.assertEqual(TaskLog.objects.values_list("status", flat=True).get(id=task_id), expected.value)

    def assert_jobs(self, task_id: TaskID, expected: dict[str, tuple[ExecutionStatus, bool]]) -> None:
        """`expected` maps job's key to its status and whether it was started"""

        actual = {
            job.spec_key: (ExecutionStatus(job.status), job.start_date is not None)
            for job in JobLog.objects.filter(task_id=task_id)
        }
        self.assertDictEqual(actual, expected)

    def assert_owner_state(self, state: str, multi_state: list[str]) -> None:
        self.cluster.refresh_from_db()
        self.assertEqual(self.cluster.state, state)
        self.assertEqual(self.cluster.multi_state, sorted(multi_state))

    def test_all_succeeded_success(self) -> None:
        task_id = self.run_action()

        self.execute_locally(task_id, make_overridden_container(MockWithEnvProvider()))

        self.assert_task_status(task_id, SUCCESS)
        self.assert_jobs(
            task_id, {PREPARE: (SUCCESS, True), WITH_ON_FAIL: (SUCCESS, True), WITHOUT_ON_FAIL: (SUCCESS, True)}
        )
        self.assert_owner_state("done", ["succeeded"])

    def test_first_job_failed_stops_plan_applies_task_on_fail(self) -> None:
        task_id = self.run_action()

        container = make_overridden_container(MockWithEnvProvider(change_jobs={PREPARE_POSITION: FAILING}))
        self.execute_locally(task_id, container)

        self.assert_task_status(task_id, FAILED)
        self.assert_jobs(
            task_id, {PREPARE: (FAILED, True), WITH_ON_FAIL: (CREATED, False), WITHOUT_ON_FAIL: (CREATED, False)}
        )
        self.assert_owner_state("task_failed", ["failed"])

    def test_job_with_on_fail_failed_stops_plan_applies_its_on_fail(self) -> None:
        task_id = self.run_action()

        container = make_overridden_container(MockWithEnvProvider(change_jobs={WITH_ON_FAIL_POSITION: FAILING}))
        self.execute_locally(task_id, container)

        self.assert_task_status(task_id, FAILED)
        self.assert_jobs(
            task_id, {PREPARE: (SUCCESS, True), WITH_ON_FAIL: (FAILED, True), WITHOUT_ON_FAIL: (CREATED, False)}
        )
        self.assert_owner_state("branch_failed", ["branch_failed_flag"])

    def test_last_job_aborted_success(self) -> None:
        task_id = self.run_action()

        container = make_overridden_container(MockWithEnvProvider(change_jobs={WITHOUT_ON_FAIL_POSITION: TERMINATED}))
        self.execute_locally(task_id, container)

        self.assert_task_status(task_id, SUCCESS)
        self.assert_jobs(
            task_id, {PREPARE: (SUCCESS, True), WITH_ON_FAIL: (SUCCESS, True), WITHOUT_ON_FAIL: (ABORTED, True)}
        )
        self.assert_owner_state("done", ["succeeded"])

    def test_every_job_aborted_aborted_owner_unchanged(self) -> None:
        task_id = self.run_action()

        container = make_overridden_container(
            MockWithEnvProvider(
                change_jobs={
                    PREPARE_POSITION: TERMINATED,
                    WITH_ON_FAIL_POSITION: TERMINATED,
                    WITHOUT_ON_FAIL_POSITION: TERMINATED,
                }
            )
        )
        self.execute_locally(task_id, container)

        self.assert_task_status(task_id, ABORTED)
        self.assert_jobs(
            task_id, {PREPARE: (ABORTED, True), WITH_ON_FAIL: (ABORTED, True), WITHOUT_ON_FAIL: (ABORTED, True)}
        )
        self.assert_owner_state(INITIAL_STATE, [])

    def test_termination_requested_stops_plan_aborted_owner_unchanged(self) -> None:
        task_id = self.run_action()

        def terminate_task(_: Executor) -> int:
            # runner is APP-scoped, so it's the one executing the task
            container.get(TaskRunner).terminate()
            return TERMINATED_CODE

        container = make_overridden_container(
            MockWithEnvProvider(
                change_jobs={PREPARE_POSITION: JobImitator(call=terminate_task, use_call_return_code=True)}
            )
        )
        self.execute_locally(task_id, container)

        self.assert_task_status(task_id, ABORTED)
        self.assert_jobs(
            task_id, {PREPARE: (ABORTED, True), WITH_ON_FAIL: (CREATED, False), WITHOUT_ON_FAIL: (CREATED, False)}
        )
        self.assert_owner_state(INITIAL_STATE, [])

    def test_revoked_job_is_skipped_next_job_runs_success(self) -> None:
        task_id = self.run_action()

        def revoke_next_job(_: Executor) -> int:
            # job is revoked while the task is already running, so the runner has its stale status
            JobLog.objects.filter(task_id=task_id, spec_key=WITH_ON_FAIL).update(status=REVOKED)
            return 0

        container = make_overridden_container(
            MockWithEnvProvider(
                change_jobs={
                    PREPARE_POSITION: JobImitator(call=revoke_next_job, use_call_return_code=True),
                    # would fail the task if executed
                    WITH_ON_FAIL_POSITION: FAILING,
                }
            )
        )
        self.execute_locally(task_id, container)

        self.assert_task_status(task_id, SUCCESS)
        self.assert_jobs(
            task_id, {PREPARE: (SUCCESS, True), WITH_ON_FAIL: (REVOKED, False), WITHOUT_ON_FAIL: (SUCCESS, True)}
        )
        self.assert_owner_state("done", ["succeeded"])
