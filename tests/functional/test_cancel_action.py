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
Tests designed to check task status with param 'allow_to_terminate' and behaviour cancel sun-actions on task status
"""
import allure
import pytest
import requests
from adcm_client.objects import ADCMClient, Cluster, Component, Job, Service, Task
from adcm_pytest_plugin.utils import get_data_dir
from tests.functional.audit.conftest import (
    check_failed,
    check_succeed,
    make_auth_header,
)
from tests.functional.tools import wait_all_jobs_are_finished, wait_for_job_status
from tests.library.predicates import display_name_is
from tests.library.utils import get_or_raise

# pylint: disable=redefined-outer-name

TIMEOUT_SUCCEED = 5
PERIOD_SUCCEED = 0.5
OBJECT_STATE_CREATED = "created"


class JobStep:
    FIRST = "first_step"
    SECOND = "second_step"
    THIRD = "third_step"


class Status:
    ABORTED = "aborted"
    SUCCESS = "success"
    FAILED = "failed"


@pytest.fixture()
def cluster(sdk_client_fs) -> Cluster:
    """Create cluster and add service"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
    cluster = bundle.cluster_create("test_cluster")
    cluster.service_add(name="test_service")
    return cluster


class TestTaskCancelRestart:
    """Test to check cancelling tasks with one/multi jobs"""

    client: ADCMClient
    admin_creds: dict
    pytestmark = [pytest.mark.usefixtures("_init")]

    @pytest.fixture()
    def _init(self, sdk_client_fs):
        self.client = sdk_client_fs
        self.admin_creds = make_auth_header(sdk_client_fs)

    @pytest.mark.parametrize("action_name", ["multi_job_success"])
    def test_aborted_not_running_job(self, cluster, action_name):
        """Test to check that only job with status running can be aborted"""
        with allure.step("Run task on cluster"):
            action = cluster.action(name=action_name)
            expected_state = action.state_on_success
            task = action.run()
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.SECOND)))
        with allure.step(f"Try to stop {JobStep.THIRD} when it not in running status"):
            check_failed(self._cancel_job(get_or_raise(task.job_list(), display_name_is(JobStep.THIRD))), 409)
            self._check_task_status(task=task, expected_status=Status.SUCCESS)
            self._check_object_status(adcm_object=cluster, expected_state=expected_state)
            self._check_jobs_status(task, expected_job_status=[Status.SUCCESS, Status.SUCCESS, Status.SUCCESS])

        with allure.step("Run task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.SECOND)))
        with allure.step(f"Try to stop {JobStep.THIRD} when it not in running status"):
            check_failed(self._cancel_job(get_or_raise(task.job_list(), display_name_is(JobStep.THIRD))), 409)
            self._check_task_status(task=task, expected_status=Status.SUCCESS)
            self._check_object_status(adcm_object=service, expected_state=expected_state)
            self._check_jobs_status(task, expected_job_status=[Status.SUCCESS, Status.SUCCESS, Status.SUCCESS])

        with allure.step("Run task on component"):
            component = service.component()
            action = component.action(name=action_name)
            task = action.run()
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.SECOND)))
        with allure.step(f"Try to stop {JobStep.THIRD} when it not in running status"):
            check_failed(self._cancel_job(get_or_raise(task.job_list(), display_name_is(JobStep.THIRD))), 409)
            self._check_task_status(task=task, expected_status=Status.SUCCESS)
            self._check_object_status(adcm_object=component, expected_state=expected_state)
            self._check_jobs_status(task, expected_job_status=[Status.SUCCESS, Status.SUCCESS, Status.SUCCESS])

    @pytest.mark.parametrize("action_name", ["one_job_success", "one_job_fail"])
    def test_aborted_one_job_action(self, cluster, action_name):
        """Test to check that canceled last sub-task change task status correctly"""
        with allure.step("Run task on cluster"):
            action = cluster.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
            self._check_task_status(task=task, expected_status=Status.ABORTED)
            self._check_object_status(adcm_object=cluster, expected_state=OBJECT_STATE_CREATED)
            self._check_jobs_status(task, expected_job_status=[Status.ABORTED])

        with allure.step("Run task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
            self._check_task_status(task=task, expected_status=Status.ABORTED)
            self._check_object_status(adcm_object=service, expected_state=OBJECT_STATE_CREATED)
            self._check_jobs_status(task, expected_job_status=[Status.ABORTED])

        with allure.step("Run task on component"):
            component = service.component()
            action = component.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
            self._check_task_status(task=task, expected_status=Status.ABORTED)
            self._check_object_status(adcm_object=component, expected_state=OBJECT_STATE_CREATED)
            self._check_jobs_status(task, expected_job_status=[Status.ABORTED])

    @pytest.mark.parametrize("action_name", ["multi_job_success", "multi_job_fail"])
    def test_aborted_multi_job_action(self, cluster, action_name):
        """Test to check that canceled last sub-task change task status correctly"""
        with allure.step("Run task on cluster"):
            action = cluster.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.THIRD, job_abort=JobStep.THIRD)
            self._check_task_status(task=task, expected_status=Status.ABORTED)
            self._check_object_status(adcm_object=cluster, expected_state=OBJECT_STATE_CREATED)
            self._check_jobs_status(task, expected_job_status=[Status.SUCCESS, Status.SUCCESS, Status.ABORTED])

        with allure.step("Run task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.THIRD, job_abort=JobStep.THIRD)
            self._check_task_status(task=task, expected_status=Status.ABORTED)
            self._check_object_status(adcm_object=service, expected_state=OBJECT_STATE_CREATED)
            self._check_jobs_status(task, expected_job_status=[Status.SUCCESS, Status.SUCCESS, Status.ABORTED])

        with allure.step("Run task on component"):
            component = service.component()
            action = component.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.THIRD, job_abort=JobStep.THIRD)
            self._check_task_status(task=task, expected_status=Status.ABORTED)
            self._check_object_status(adcm_object=component, expected_state=OBJECT_STATE_CREATED)
            self._check_jobs_status(task, expected_job_status=[Status.SUCCESS, Status.SUCCESS, Status.ABORTED])

    @pytest.mark.parametrize("action_name", ["multi_job_success"])
    def test_success_task_status_not_changing(self, cluster, action_name):
        """
        Test to check that success task status is not changing when not last job is canceled
        """
        with allure.step("Run success task on cluster"):
            action = cluster.action(name=action_name)
            expected_state = action.state_on_success
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.SECOND, job_abort=JobStep.SECOND)
            self._check_task_status(task=task, expected_status=Status.SUCCESS)
            self._check_object_status(adcm_object=cluster, expected_state=expected_state)
            self._check_jobs_status(task, expected_job_status=[Status.SUCCESS, Status.ABORTED, Status.SUCCESS])

        with allure.step("Run success task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.SECOND, job_abort=JobStep.SECOND)
            self._check_task_status(task=task, expected_status=Status.SUCCESS)
            self._check_object_status(adcm_object=service, expected_state=expected_state)
            self._check_jobs_status(task, expected_job_status=[Status.SUCCESS, Status.ABORTED, Status.SUCCESS])

        with allure.step("Run success task on component"):
            component = service.component()
            action = component.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.SECOND, job_abort=JobStep.SECOND)
            self._check_task_status(task=task, expected_status=Status.SUCCESS)
            self._check_object_status(adcm_object=component, expected_state=expected_state)
            self._check_jobs_status(task, expected_job_status=[Status.SUCCESS, Status.ABORTED, Status.SUCCESS])

    @pytest.mark.parametrize("action_name", ["multi_job_fail_second_job"])
    def test_cancel_failed_job_in_success_task(self, cluster, action_name):
        """
        Test to check that task with canceled failed job has success status
        """
        with allure.step("Check that task with aborted failed job has success result"):
            action = cluster.action(name=action_name)
            expected_state = action.state_on_success
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.SECOND, job_abort=JobStep.SECOND)
            self._check_task_status(task=task, expected_status=Status.SUCCESS)
            self._check_object_status(adcm_object=cluster, expected_state=expected_state)
            self._check_jobs_status(task, expected_job_status=[Status.SUCCESS, Status.ABORTED, Status.SUCCESS])

        with allure.step("Run success task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.SECOND, job_abort=JobStep.SECOND)
            self._check_task_status(task=task, expected_status=Status.SUCCESS)
            self._check_object_status(adcm_object=service, expected_state=expected_state)
            self._check_jobs_status(task, expected_job_status=[Status.SUCCESS, Status.ABORTED, Status.SUCCESS])

        with allure.step("Run success task on component"):
            component = service.component()
            action = component.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.SECOND, job_abort=JobStep.SECOND)
            self._check_task_status(task=task, expected_status=Status.SUCCESS)
            self._check_object_status(adcm_object=component, expected_state=expected_state)
            self._check_jobs_status(task, expected_job_status=[Status.SUCCESS, Status.ABORTED, Status.SUCCESS])

    @pytest.mark.parametrize("action_name", ["multi_job_fail"])
    def test_failed_task_status_not_changing(self, cluster, action_name):
        """
        Test to check that failed task status is not changing when not last job is canceled
        """
        with allure.step("Run failed task on cluster"):
            action = cluster.action(name=action_name)
            expected_state = action.state_on_fail
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.SECOND, job_abort=JobStep.SECOND)
            self._check_task_status(task=task, expected_status=Status.FAILED)
            self._check_object_status(adcm_object=cluster, expected_state=expected_state)
            self._check_jobs_status(task, expected_job_status=[Status.SUCCESS, Status.ABORTED, Status.FAILED])

        with allure.step("Run failed task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.SECOND, job_abort=JobStep.SECOND)
            self._check_task_status(task=task, expected_status=Status.FAILED)
            self._check_object_status(adcm_object=service, expected_state=expected_state)
            self._check_jobs_status(task, expected_job_status=[Status.SUCCESS, Status.ABORTED, Status.FAILED])

        with allure.step("Run failed task on component"):
            component = service.component()
            action = component.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.SECOND, job_abort=JobStep.SECOND)
            self._check_task_status(task=task, expected_status=Status.FAILED)
            self._check_object_status(adcm_object=component, expected_state=expected_state)
            self._check_jobs_status(task, expected_job_status=[Status.SUCCESS, Status.ABORTED, Status.FAILED])

    def _cancel_job(self, job: Job):
        url = f"{self.client.url}/api/v1/job/{job.id}/cancel/"
        with allure.step(f"Cancel job via PUT {url}"):
            return requests.put(url, headers=self.admin_creds)

    @allure.step("Check task status")
    def _check_task_status(self, task: Task, expected_status: str) -> None:
        wait_all_jobs_are_finished(self.client)
        task.reread()
        assert task.status == expected_status, f"Expected task status {expected_status} Actual status {task.status}"

    @staticmethod
    @allure.step("Check object state")
    def _check_object_status(adcm_object: Cluster | Service | Component, expected_state: str) -> None:
        adcm_object.reread()
        assert adcm_object.state == expected_state, f"Expected object state {expected_state} Actual {adcm_object.state}"

    @staticmethod
    @allure.step("Check jobs status")
    def _check_jobs_status(task: Task, expected_job_status: list[str]) -> None:
        task.reread()
        actual_jobs_status = [job["status"] for job in task.jobs]
        for index, job in enumerate(actual_jobs_status):
            assert (actual_info := job) == (
                expected_info := expected_job_status[index]
            ), f'Job at position #{index} should be {expected_info}, not {actual_info}'

    def wait_job_and_abort(self, task: Task, job_wait: str, job_abort: str) -> None:
        task.reread()
        wait_for_job_status(get_or_raise(task.job_list(), display_name_is(job_wait)))
        stop_job = get_or_raise(task.job_list(), display_name_is(job_abort))
        with allure.step(f"Cancel {job_abort} job in task"):
            check_succeed(self._cancel_job(stop_job))
