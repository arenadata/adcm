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

"""Tests designed to check restart method for task"""
import allure
import pytest
import requests
from adcm_client.objects import ADCMClient, Cluster, Job, Task
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    wait_for_task_and_assert_result,
)
from adcm_pytest_plugin.utils import get_data_dir

from tests.functional.audit.conftest import (
    check_failed,
    check_succeed,
    make_auth_header,
)
from tests.functional.tools import (
    compare_object_multi_state,
    compare_object_state,
    wait_for_job_status,
)
from tests.library.predicates import display_name_is
from tests.library.utils import get_or_raise

# pylint: disable=redefined-outer-name

SET_MULTI_SET_ACTION = "set_multistate"


class MultiState:
    UNSET = "unset_this"
    FAILED = "multi_fail"
    SUCCESS = "multi_ok"


class JobStep:
    FIRST = "first_step"
    SECOND = "second_step"
    THIRD = "third_step"


class Status:
    RUNNING = "running"
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


@pytest.fixture()
def cluster_multi_state(sdk_client_fs) -> Cluster:
    """Create cluster and add service"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_multi_state"))
    cluster = bundle.cluster_create("multi_state")
    cluster.service_add(name="first_srv")
    return cluster


@pytest.fixture()
def cluster_masking_1(sdk_client_fs) -> Cluster:
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "masking_scenario_1"))
    cluster = bundle.cluster_create("multi_state")
    return cluster


@pytest.fixture()
def cluster_masking_2(sdk_client_fs) -> Cluster:
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "masking_scenario_2"))
    cluster = bundle.cluster_create("multi_state")
    return cluster


class TestTaskCancelRestart:
    """Test to check restart tasks"""

    client: ADCMClient
    admin_creds: dict
    pytestmark = [pytest.mark.usefixtures("_init")]

    @pytest.fixture()
    def _init(self, sdk_client_fs):
        self.client = sdk_client_fs
        self.admin_creds = make_auth_header(sdk_client_fs)

    @pytest.mark.parametrize("action_name", ["one_job_success", "one_job_fail"])
    def test_restart_one_job_task(self, cluster, action_name):
        """
        Test to check that one job:
         - task with state 'created' can not be restarted
         - finished task can be restarted
         - task after restart have status running
        """
        expected_task_status = Status.SUCCESS if "success" in action_name else Status.FAILED
        with allure.step("Run task on cluster"):
            action = cluster.action(name=action_name)
            task = action.run()
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.FIRST)))
            check_failed(self._restart_task(task=task), 409)
            wait_for_task_and_assert_result(task=task, status=expected_task_status)

        with allure.step("Restart finished task on cluster"):
            check_succeed(self._restart_task(task=task))
            self._check_task_status_is_running(task=task)
            wait_for_task_and_assert_result(task=task, status=expected_task_status)

        with allure.step("Run task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.FIRST)))
            check_failed(self._restart_task(task=task), 409)
            wait_for_task_and_assert_result(task=task, status=expected_task_status)

        with allure.step("Restart finished task on service"):
            check_succeed(self._restart_task(task=task))
            self._check_task_status_is_running(task=task)
            wait_for_task_and_assert_result(task=task, status=expected_task_status)

        with allure.step("Run task on component"):
            component = service.component()
            action = component.action(name=action_name)
            task = action.run()
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.FIRST)))
            check_failed(self._restart_task(task=task), 409)
            wait_for_task_and_assert_result(task=task, status=expected_task_status)

        with allure.step("Restart finished task on component"):
            check_succeed(self._restart_task(task=task))
            self._check_task_status_is_running(task=task)
            wait_for_task_and_assert_result(task=task, status=expected_task_status)

    @pytest.mark.parametrize("action_name", ["multi_job_success", "multi_job_fail"])
    def test_restart_multi_job_task(self, cluster, action_name):
        """
        Test to check that
         - task with state 'created' can not be restarted
         - finished task can be restarted
         - after restart finished task have status running
        """
        expected_task_status = Status.SUCCESS if "success" in action_name else Status.FAILED
        with allure.step("Run task on cluster"):
            action = cluster.action(name=action_name)
            task = action.run()
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.FIRST)))
            check_failed(self._restart_task(task=task), 409)
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.SECOND)))
            check_failed(self._restart_task(task=task), 409)
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.THIRD)))
            check_failed(self._restart_task(task=task), 409)
            wait_for_task_and_assert_result(task=task, status=expected_task_status)

        with allure.step("Restart finished task on cluster"):
            check_succeed(self._restart_task(task=task))
            self._check_task_status_is_running(task=task)
            wait_for_task_and_assert_result(task=task, status=expected_task_status)

        with allure.step("Run task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.FIRST)))
            check_failed(self._restart_task(task=task), 409)
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.SECOND)))
            check_failed(self._restart_task(task=task), 409)
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.THIRD)))
            check_failed(self._restart_task(task=task), 409)
            wait_for_task_and_assert_result(task=task, status=expected_task_status)

        with allure.step("Restart finished task on service"):
            check_succeed(self._restart_task(task=task))
            self._check_task_status_is_running(task=task)
            wait_for_task_and_assert_result(task=task, status=expected_task_status)

        with allure.step("Run task on component"):
            component = service.component()
            action = component.action(name=action_name)
            task = action.run()
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.FIRST)))
            check_failed(self._restart_task(task=task), 409)
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.SECOND)))
            check_failed(self._restart_task(task=task), 409)
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.THIRD)))
            check_failed(self._restart_task(task=task), 409)
            wait_for_task_and_assert_result(task=task, status=expected_task_status)

        with allure.step("Restart finished task on component"):
            check_succeed(self._restart_task(task=task))
            self._check_task_status_is_running(task=task)
            wait_for_task_and_assert_result(task=task, status=expected_task_status)

    @pytest.mark.parametrize("action_name", ["multi_job_fail_second_job"])
    def test_restart_task_with_aborted_job(self, cluster, action_name):
        """
        Test to check that task where second job is failed and aborted have status success,
        but after restart task without abort failed job task status is changed to failed
        """
        with allure.step("Run task on cluster"):
            action = cluster.action(name=action_name)
            task = action.run()
            failed_job = get_or_raise(task.job_list(), display_name_is(JobStep.SECOND))
            wait_for_job_status(failed_job)
            check_succeed(self._cancel_job(failed_job))
            wait_for_task_and_assert_result(task=task, status=Status.SUCCESS)

        with allure.step("Restart finished task on cluster"):
            check_succeed(self._restart_task(task=task))
            self._check_task_status_is_running(task=task)
            wait_for_task_and_assert_result(task=task, status=Status.FAILED)

        with allure.step("Run task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            failed_job = get_or_raise(task.job_list(), display_name_is(JobStep.SECOND))
            wait_for_job_status(failed_job)
            check_succeed(self._cancel_job(failed_job))
            wait_for_task_and_assert_result(task=task, status=Status.SUCCESS)

        with allure.step("Restart finished task on service"):
            check_succeed(self._restart_task(task=task))
            self._check_task_status_is_running(task=task)
            wait_for_task_and_assert_result(task=task, status=Status.FAILED)

        with allure.step("Run task on component"):
            component = service.component()
            action = component.action(name=action_name)
            task = action.run()
            failed_job = get_or_raise(task.job_list(), display_name_is(JobStep.SECOND))
            wait_for_job_status(failed_job)
            check_succeed(self._cancel_job(failed_job))
            wait_for_task_and_assert_result(task=task, status=Status.SUCCESS)

        with allure.step("Restart finished task on component"):
            check_succeed(self._restart_task(task=task))
            self._check_task_status_is_running(task=task)
            wait_for_task_and_assert_result(task=task, status=Status.FAILED)

    @pytest.mark.parametrize("action_name", ["one_job_success", "one_job_fail"])
    def test_restart_aborted_task(self, cluster, action_name):
        """
        Test to check that task with aborted status can be restarted and switch status to success
        """
        expected_task_status = Status.SUCCESS if "success" in action_name else Status.FAILED
        with allure.step("Run task on cluster"):
            action = cluster.action(name=action_name)
            task = action.run()
            job = get_or_raise(task.job_list(), display_name_is(JobStep.FIRST))
            wait_for_job_status(job)
            check_succeed(self._cancel_job(job))
            wait_for_task_and_assert_result(task=task, status=Status.ABORTED)

        with allure.step("Restart finished task on cluster"):
            check_succeed(self._restart_task(task=task))
            self._check_task_status_is_running(task=task)
            wait_for_task_and_assert_result(task=task, status=expected_task_status)

        with allure.step("Run task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            job = get_or_raise(task.job_list(), display_name_is(JobStep.FIRST))
            wait_for_job_status(job)
            check_succeed(self._cancel_job(job))
            wait_for_task_and_assert_result(task=task, status=Status.ABORTED)

        with allure.step("Restart finished task on service"):
            check_succeed(self._restart_task(task=task))
            self._check_task_status_is_running(task=task)
            wait_for_task_and_assert_result(task=task, status=expected_task_status)

        with allure.step("Run task on component"):
            component = service.component()
            action = component.action(name=action_name)
            task = action.run()
            job = get_or_raise(task.job_list(), display_name_is(JobStep.FIRST))
            wait_for_job_status(job)
            check_succeed(self._cancel_job(job))
            wait_for_task_and_assert_result(task=task, status=Status.ABORTED)

        with allure.step("Restart finished task on component"):
            check_succeed(self._restart_task(task=task))
            self._check_task_status_is_running(task=task)
            wait_for_task_and_assert_result(task=task, status=expected_task_status)

    @pytest.mark.parametrize("action_name", ["state_changing_fail"])
    def test_restart_multi_state_task(self, cluster_multi_state, action_name):
        """
        Test to check that task with multi state can be restarted
        """
        with allure.step("Run multi state action"):
            cluster = cluster_multi_state
            run_cluster_action_and_assert_result(cluster, SET_MULTI_SET_ACTION)

        with allure.step("Run task on cluster"):
            action = cluster.action(name=action_name)
            task = action.run()
            wait_for_task_and_assert_result(task=task, status=Status.FAILED)
            compare_object_state(adcm_object=cluster, expected_state=MultiState.FAILED)
            compare_object_multi_state(adcm_object=cluster, expected_state=[MultiState.FAILED])

        with allure.step("Restart finished task on cluster"):
            check_succeed(self._restart_task(task=task))
            self._check_task_status_is_running(task=task)

        with allure.step("Abort failed job and check states"):
            job = get_or_raise(task.job_list(), display_name_is(JobStep.FIRST))
            wait_for_job_status(job)
            check_succeed(self._cancel_job(job))
            wait_for_task_and_assert_result(task=task, status=Status.SUCCESS)
            compare_object_state(adcm_object=cluster, expected_state=MultiState.SUCCESS)
            compare_object_multi_state(adcm_object=cluster, expected_state=[MultiState.FAILED])

    @pytest.mark.parametrize(
        ("cluster", "expected"),
        [
            (pytest.lazy_fixture("cluster_masking_1"), [MultiState.FAILED, MultiState.SUCCESS]),
            (pytest.lazy_fixture("cluster_masking_2"), [MultiState.SUCCESS]),
        ],
    )
    def test_cancel_failed(self, cluster, expected):
        """
        Test to check multi states after job cancel
        """
        with allure.step("Run action and check states"):
            run_cluster_action_and_assert_result(cluster=cluster, action="state_changing_fail", status=Status.FAILED)
            compare_object_state(adcm_object=cluster, expected_state=MultiState.FAILED)
            compare_object_multi_state(adcm_object=cluster, expected_state=[MultiState.FAILED])

        with allure.step("Run same action again and cancel job"):
            action = cluster.action(name="state_changing_fail")
            task = action.run()
            job = get_or_raise(task.job_list(), display_name_is(JobStep.FIRST))
            wait_for_job_status(job)
            check_succeed(self._cancel_job(job))
            wait_for_task_and_assert_result(task=task, status=Status.SUCCESS)

        with allure.step("Check state and multi state"):
            compare_object_state(adcm_object=cluster, expected_state=MultiState.SUCCESS)
            compare_object_multi_state(adcm_object=cluster, expected_state=expected)

    @allure.step("Restarting task")
    def _restart_task(self, task: Task):
        url = f"{self.client.url}/api/v1/task/{task.id}/restart/"
        with allure.step(f"Restart task via PUT {url}"):
            return requests.put(url, headers=self.admin_creds)

    @allure.step("Cancel job")
    def _cancel_job(self, job: Job):
        url = f"{self.client.url}/api/v1/job/{job.id}/cancel/"
        with allure.step(f"Cancel job via PUT {url}"):
            return requests.put(url, headers=self.admin_creds)

    @allure.step("Check task status")
    def _check_task_status_is_running(self, task: Task) -> None:
        task.reread()
        assert task.status == Status.RUNNING, f"Expected task status {Status.RUNNING} Actual status {task.status}"
