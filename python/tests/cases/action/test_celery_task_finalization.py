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
Steps of celery task runner (`use_cases.job.run`) called directly, without celery:
jobs' statuses are set as if they were executed, then the step is performed.
"""

from pathlib import Path
from typing import Final

from cm.models import Action, JobLog, TaskLog
from core.action import ExecutionStatus
from core.legacy.job.runners import RunnerEnvironment
from core.types import TaskID
from rest_framework.status import HTTP_200_OK
from use_cases.job.run import FinalizeTask, RunJob

from tests.suites import ADCMDjangoAPISuite

BUNDLES_DIR: Final = Path(__file__).parent / "bundles" / "task_result"

RUN_ACTION_PAYLOAD: Final = {"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False}

PREPARE: Final = "/0"
WITH_ON_FAIL: Final = "/branches/0"
WITHOUT_ON_FAIL: Final = "/branches/1"

SUCCESS: Final = ExecutionStatus.SUCCESS
FAILED: Final = ExecutionStatus.FAILED
CREATED: Final = ExecutionStatus.CREATED
REVOKED: Final = ExecutionStatus.REVOKED
ABORTED: Final = ExecutionStatus.ABORTED

INITIAL_STATE: Final = "created"


class TestCeleryTaskFinalization(ADCMDjangoAPISuite):
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

    def execute_as(
        self, task_id: TaskID, jobs: dict[str, ExecutionStatus], task_status: ExecutionStatus = ExecutionStatus.RUNNING
    ) -> None:
        """Set statuses of task and its jobs as they would be after jobs are executed"""

        TaskLog.objects.filter(id=task_id).update(status=task_status)
        for key, status in jobs.items():
            JobLog.objects.filter(task_id=task_id, spec_key=key).update(status=status)

    def finalize(self, task_id: TaskID) -> None:
        self.container.get(FinalizeTask).do(task_id=task_id, environment=self.container.get(RunnerEnvironment))

    def assert_task_status(self, task_id: TaskID, expected: ExecutionStatus) -> None:
        self.assertEqual(TaskLog.objects.values_list("status", flat=True).get(id=task_id), expected.value)

    def assert_owner_state(self, state: str, multi_state: list[str]) -> None:
        self.cluster.refresh_from_db()
        self.assertEqual(self.cluster.state, state)
        self.assertEqual(self.cluster.multi_state, sorted(multi_state))

    def test_jobs_are_named_after_plan_positions(self) -> None:
        task_id = self.run_action()

        self.assertCountEqual(
            JobLog.objects.filter(task_id=task_id).values_list("spec_key", flat=True),
            [PREPARE, WITH_ON_FAIL, WITHOUT_ON_FAIL],
        )

    def test_all_succeeded_success(self) -> None:
        task_id = self.run_action()
        self.execute_as(task_id, {PREPARE: SUCCESS, WITH_ON_FAIL: SUCCESS, WITHOUT_ON_FAIL: SUCCESS})

        self.finalize(task_id)

        self.assert_task_status(task_id, SUCCESS)
        self.assert_owner_state("done", ["succeeded"])

    def test_first_job_failed_applies_task_on_fail(self) -> None:
        task_id = self.run_action()
        self.execute_as(task_id, {PREPARE: FAILED})

        self.finalize(task_id)

        self.assert_task_status(task_id, FAILED)
        self.assert_owner_state("task_failed", ["failed"])

    def test_last_job_failed_without_on_fail_applies_task_on_fail(self) -> None:
        task_id = self.run_action()
        self.execute_as(task_id, {PREPARE: SUCCESS, WITH_ON_FAIL: SUCCESS, WITHOUT_ON_FAIL: FAILED})

        self.finalize(task_id)

        self.assert_task_status(task_id, FAILED)
        self.assert_owner_state("task_failed", ["failed"])

    def test_non_last_branch_failed_applies_its_on_fail(self) -> None:
        task_id = self.run_action()
        self.execute_as(task_id, {PREPARE: SUCCESS, WITH_ON_FAIL: FAILED, WITHOUT_ON_FAIL: SUCCESS})

        self.finalize(task_id)

        self.assert_task_status(task_id, FAILED)
        self.assert_owner_state("branch_failed", ["branch_failed_flag"])

    def test_both_branches_failed_applies_on_fail_of_the_one_having_it(self) -> None:
        task_id = self.run_action()
        self.execute_as(task_id, {PREPARE: SUCCESS, WITH_ON_FAIL: FAILED, WITHOUT_ON_FAIL: FAILED})

        self.finalize(task_id)

        self.assert_task_status(task_id, FAILED)
        self.assert_owner_state("branch_failed", ["branch_failed_flag"])

    def test_terminated_task_aborted_owner_unchanged(self) -> None:
        task_id = self.run_action()
        self.execute_as(
            task_id,
            {PREPARE: SUCCESS, WITH_ON_FAIL: FAILED, WITHOUT_ON_FAIL: REVOKED},
            task_status=ExecutionStatus.TERMINATING,
        )

        self.finalize(task_id)

        self.assert_task_status(task_id, ABORTED)
        self.assert_owner_state(INITIAL_STATE, [])

    def test_no_job_finished_finalization_fails(self) -> None:
        task_id = self.run_action()
        self.execute_as(task_id, {PREPARE: CREATED, WITH_ON_FAIL: CREATED, WITHOUT_ON_FAIL: CREATED})

        with self.assertRaisesRegex(RuntimeError, "no jobs in a final status"):
            self.finalize(task_id)

        # broken status is set by errback of finalization (`MarkTaskBroken`), not by finalization itself
        self.assert_task_status(task_id, ExecutionStatus.RUNNING)
        self.assert_owner_state(INITIAL_STATE, [])

    def test_revoked_job_is_not_executed(self) -> None:
        task_id = self.run_action()
        self.execute_as(task_id, {PREPARE: SUCCESS, WITH_ON_FAIL: REVOKED})
        job = JobLog.objects.get(task_id=task_id, spec_key=WITH_ON_FAIL)

        result = self.container.get(RunJob).do(
            task_id=task_id, job_id=job.id, environment=self.container.get(RunnerEnvironment)
        )

        self.assertEqual(result, REVOKED)
        job.refresh_from_db()
        self.assertEqual(job.status, REVOKED.value)
        self.assertIsNone(job.start_date)
