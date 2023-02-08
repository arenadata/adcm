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
    check_jobs_status,
    check_object_multi_state,
    check_object_state,
    wait_for_job_status,
)
from tests.library.predicates import display_name_is
from tests.library.utils import get_or_raise

# pylint: disable=redefined-outer-name

TIMEOUT_SUCCEED = 5
PERIOD_SUCCEED = 0.5
OBJECT_STATE_CREATED = "created"
SET_MULTI_SET_ACTION = "set_multistate"


class JobStep:
    FIRST = "first_step"
    SECOND = "second_step"
    THIRD = "third_step"


class Status:
    ABORTED = "aborted"
    SUCCESS = "success"
    FAILED = "failed"


class MultiState:
    UNSET = "unset_this"
    FAILED = "multi_fail_on_last"
    SUCCESS = "multi_ok"


@pytest.fixture()
def cluster(sdk_client_fs) -> Cluster:
    """Create cluster and add service"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
    cluster = bundle.cluster_create("test_cluster")
    cluster.service_add(name="test_service")
    return cluster


@pytest.fixture()
def cluster_multi_state(sdk_client_fs) -> Cluster:
    """Create cluster with multi state tasks and add service"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_multi_state"))
    cluster = bundle.cluster_create("multi_fail_on_last")
    cluster.service_add(name="first_srv")
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
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.FIRST)))
        with allure.step(f"Try to stop {JobStep.SECOND} when it not in running status"):
            check_failed(self._cancel_job(get_or_raise(task.job_list(), display_name_is(JobStep.SECOND))), 409)
            wait_for_task_and_assert_result(task=task, status=Status.SUCCESS)
            check_object_state(adcm_object=cluster, expected_state=expected_state)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.SUCCESS, JobStep.SECOND: Status.SUCCESS})

        with allure.step("Run task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.FIRST)))
        with allure.step(f"Try to stop {JobStep.SECOND} when it not in running status"):
            check_failed(self._cancel_job(get_or_raise(task.job_list(), display_name_is(JobStep.SECOND))), 409)
            wait_for_task_and_assert_result(task=task, status=Status.SUCCESS)
            check_object_state(adcm_object=service, expected_state=expected_state)
            check_jobs_status(
                task,
                expected_job_status={JobStep.FIRST: Status.SUCCESS, JobStep.SECOND: Status.SUCCESS},
            )

        with allure.step("Run task on component"):
            component = service.component(name="first_component")
            action = component.action(name=action_name)
            task = action.run()
            wait_for_job_status(get_or_raise(task.job_list(), display_name_is(JobStep.FIRST)))
        with allure.step(f"Try to stop {JobStep.SECOND} when it not in running status"):
            check_failed(self._cancel_job(get_or_raise(task.job_list(), display_name_is(JobStep.SECOND))), 409)
            wait_for_task_and_assert_result(task=task, status=Status.SUCCESS)
            check_object_state(adcm_object=component, expected_state=expected_state)
            check_jobs_status(
                task,
                expected_job_status={JobStep.FIRST: Status.SUCCESS, JobStep.SECOND: Status.SUCCESS},
            )

    @pytest.mark.parametrize("action_name", ["one_job_success", "one_job_fail"])
    def test_aborted_one_job_action(self, cluster, action_name):
        """Test to check that canceled last sub-task change task status correctly"""
        with allure.step("Run task on cluster"):
            action = cluster.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
            wait_for_task_and_assert_result(task=task, status=Status.ABORTED)
            check_object_state(adcm_object=cluster, expected_state=OBJECT_STATE_CREATED)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.ABORTED})

        with allure.step("Run task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
            wait_for_task_and_assert_result(task=task, status=Status.ABORTED)
            check_object_state(adcm_object=service, expected_state=OBJECT_STATE_CREATED)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.ABORTED})

        with allure.step("Run task on component"):
            component = service.component(name="first_component")
            action = component.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
            wait_for_task_and_assert_result(task=task, status=Status.ABORTED)
            check_object_state(adcm_object=component, expected_state=OBJECT_STATE_CREATED)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.ABORTED})

    @pytest.mark.parametrize("action_name", ["multi_job_success", "multi_job_fail"])
    def test_aborted_multi_job_action(self, cluster, action_name):
        """Test to check that canceled last sub-task change task status correctly"""
        with allure.step("Run task on cluster"):
            action = cluster.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.SECOND, job_abort=JobStep.SECOND)
            wait_for_task_and_assert_result(task=task, status=Status.ABORTED)
            check_object_state(adcm_object=cluster, expected_state=OBJECT_STATE_CREATED)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.SUCCESS, JobStep.SECOND: Status.ABORTED})

        with allure.step("Run task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.SECOND, job_abort=JobStep.SECOND)
            wait_for_task_and_assert_result(task=task, status=Status.ABORTED)
            check_object_state(adcm_object=service, expected_state=OBJECT_STATE_CREATED)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.SUCCESS, JobStep.SECOND: Status.ABORTED})

        with allure.step("Run task on component"):
            component = service.component(name="first_component")
            action = component.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.SECOND, job_abort=JobStep.SECOND)
            wait_for_task_and_assert_result(task=task, status=Status.ABORTED)
            check_object_state(adcm_object=component, expected_state=OBJECT_STATE_CREATED)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.SUCCESS, JobStep.SECOND: Status.ABORTED})

    @pytest.mark.parametrize("action_name", ["multi_job_success"])
    def test_success_task_status_not_changing(self, cluster, action_name):
        """
        Test to check that success task status is not changing when not last job is canceled
        """
        with allure.step("Run success task on cluster"):
            action = cluster.action(name=action_name)
            expected_state = action.state_on_success
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
            wait_for_task_and_assert_result(task=task, status=Status.SUCCESS)
            check_object_state(adcm_object=cluster, expected_state=expected_state)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.ABORTED, JobStep.SECOND: Status.SUCCESS})

        with allure.step("Run success task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
            wait_for_task_and_assert_result(task=task, status=Status.SUCCESS)
            check_object_state(adcm_object=service, expected_state=expected_state)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.ABORTED, JobStep.SECOND: Status.SUCCESS})

        with allure.step("Run success task on component"):
            component = service.component(name="first_component")
            action = component.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
            wait_for_task_and_assert_result(task=task, status=Status.SUCCESS)
            check_object_state(adcm_object=component, expected_state=expected_state)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.ABORTED, JobStep.SECOND: Status.SUCCESS})

    @pytest.mark.parametrize("action_name", ["multi_job_fail_first_job"])
    def test_cancel_failed_job_in_success_task(self, cluster, action_name):
        """
        Test to check that task with canceled failed job has success status
        """
        with allure.step("Check that config 'allow_to_terminate' does not change task behaviour"):
            action = cluster.action(name=action_name)
            expected_state = action.state_on_fail
            task = action.run()
            wait_for_task_and_assert_result(task=task, status=Status.FAILED)
            check_object_state(adcm_object=cluster, expected_state=expected_state)
            check_jobs_status(
                task, expected_job_status={JobStep.FIRST: Status.FAILED, JobStep.SECOND: OBJECT_STATE_CREATED}
            )

        with allure.step("Check that task with aborted failed job has success result"):
            action = cluster.action(name=action_name)
            expected_state = action.state_on_success
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
            wait_for_task_and_assert_result(task=task, status=Status.SUCCESS)
            check_object_state(adcm_object=cluster, expected_state=expected_state)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.ABORTED, JobStep.SECOND: Status.SUCCESS})

        with allure.step("Run success task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
            wait_for_task_and_assert_result(task=task, status=Status.SUCCESS)
            check_object_state(adcm_object=service, expected_state=expected_state)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.ABORTED, JobStep.SECOND: Status.SUCCESS})

        with allure.step("Run success task on component"):
            component = service.component(name="first_component")
            action = component.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
            wait_for_task_and_assert_result(task=task, status=Status.SUCCESS)
            check_object_state(adcm_object=component, expected_state=expected_state)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.ABORTED, JobStep.SECOND: Status.SUCCESS})

    @pytest.mark.parametrize("action_name", ["multi_job_fail"])
    def test_failed_task_status_not_changing(self, cluster, action_name):
        """
        Test to check that failed task status is not changing when not last job is canceled
        """
        with allure.step("Run failed task on cluster"):
            action = cluster.action(name=action_name)
            expected_state = action.state_on_fail
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
            wait_for_task_and_assert_result(task=task, status=Status.FAILED)
            check_object_state(adcm_object=cluster, expected_state=expected_state)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.ABORTED, JobStep.SECOND: Status.FAILED})

        with allure.step("Run failed task on service"):
            service = cluster.service()
            action = service.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
            wait_for_task_and_assert_result(task=task, status=Status.FAILED)
            check_object_state(adcm_object=service, expected_state=expected_state)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.ABORTED, JobStep.SECOND: Status.FAILED})

        with allure.step("Run failed task on component"):
            component = service.component(name="first_component")
            action = component.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
            wait_for_task_and_assert_result(task=task, status=Status.FAILED)
            check_object_state(adcm_object=component, expected_state=expected_state)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.ABORTED, JobStep.SECOND: Status.FAILED})

    @pytest.mark.parametrize("action_name", ["state_changing_fail"])
    def test_abort_multi_state(self, cluster_multi_state, action_name):
        """
        Test to check that failed task status is not changing when not last job is canceled
        """
        cluster = cluster_multi_state
        service = cluster.service()
        component = service.component(name="first_component")
        expected_object_state = cluster.state
        expected_object_multi_state = [MultiState.UNSET]
        run_cluster_action_and_assert_result(cluster, SET_MULTI_SET_ACTION)

        with allure.step("Run failed action on cluster and abort last task"):
            action = cluster.action(name=action_name)
            task = action.run()
            self.wait_job_and_abort(task=task, job_wait=JobStep.SECOND, job_abort=JobStep.SECOND)
            wait_for_task_and_assert_result(task=task, status=Status.ABORTED)
            check_object_state(adcm_object=cluster, expected_state=expected_object_state)
            check_object_multi_state(adcm_object=cluster, expected_state=expected_object_multi_state)
            check_jobs_status(task, expected_job_status={JobStep.FIRST: Status.SUCCESS, JobStep.SECOND: Status.ABORTED})

        with allure.step("Run failed action and abort last task"):
            for obj in [service, component]:
                action = obj.action(name=action_name)
                task = action.run()
                self.wait_job_and_abort(task=task, job_wait=JobStep.SECOND, job_abort=JobStep.SECOND)
                wait_for_task_and_assert_result(task=task, status=Status.ABORTED)
                check_object_state(adcm_object=obj, expected_state=expected_object_state)
                self._check_not_multi_state(adcm_object=obj)
                check_jobs_status(
                    task, expected_job_status={JobStep.FIRST: Status.SUCCESS, JobStep.SECOND: Status.ABORTED}
                )

    @pytest.mark.parametrize("action_name", ["state_changing_fail"])
    def test_fail_multi_state(self, cluster_multi_state, action_name):
        """
        Test to check that failed task status is not changing when not last job is canceled
        object state and multi state must be different
        """
        cluster = cluster_multi_state
        service = cluster.service()
        component = service.component(name="first_component")
        run_cluster_action_and_assert_result(cluster, SET_MULTI_SET_ACTION)
        expected_object_state = "not_multi_state"
        expected_object_multi_state = [MultiState.FAILED]
        with allure.step("Run failed action and abort first task"):
            for obj in [cluster, service, component]:
                action = obj.action(name=action_name)
                task = action.run()
                self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
                wait_for_task_and_assert_result(task=task, status=Status.FAILED)
                check_object_state(adcm_object=obj, expected_state=expected_object_state)
                check_object_multi_state(adcm_object=obj, expected_state=expected_object_multi_state)
                check_jobs_status(
                    task, expected_job_status={JobStep.FIRST: Status.ABORTED, JobStep.SECOND: Status.FAILED}
                )

    @pytest.mark.parametrize("action_name", ["state_changing_success"])
    def test_success_multi_state(self, cluster_multi_state, action_name):
        """
        Test to check that failed task state is not changing when not last job is canceled
        Present state of object with multi state and object state must be the same
        """
        cluster = cluster_multi_state
        service = cluster.service()
        component = service.component(name="first_component")
        run_cluster_action_and_assert_result(cluster, SET_MULTI_SET_ACTION)
        expected_object_multi_state = [MultiState.SUCCESS]
        expected_object_state = MultiState.SUCCESS

        with allure.step("Run failed action on cluster and abort first task"):
            for adcm_object in [cluster, service, component]:
                action = adcm_object.action(name=action_name)
                task = action.run()
                self.wait_job_and_abort(task=task, job_wait=JobStep.FIRST, job_abort=JobStep.FIRST)
                wait_for_task_and_assert_result(task=task, status=Status.SUCCESS)
                check_object_state(adcm_object=adcm_object, expected_state=expected_object_state)
                check_object_multi_state(adcm_object=adcm_object, expected_state=expected_object_multi_state)
                check_jobs_status(
                    task, expected_job_status={JobStep.FIRST: Status.ABORTED, JobStep.SECOND: Status.SUCCESS}
                )

    def wait_job_and_abort(self, task: Task, job_wait: str, job_abort: str) -> None:
        task.reread()
        wait_for_job_status(get_or_raise(task.job_list(), display_name_is(job_wait)))
        stop_job = get_or_raise(task.job_list(), display_name_is(job_abort))
        with allure.step(f"Cancel {job_abort} job in task"):
            check_succeed(self._cancel_job(stop_job))

    def _cancel_job(self, job: Job):
        url = f"{self.client.url}/api/v1/job/{job.id}/cancel/"
        with allure.step(f"Cancel job via PUT {url}"):
            return requests.put(url, headers=self.admin_creds)

    @staticmethod
    def _check_not_multi_state(adcm_object: Service | Component):
        adcm_object.reread()
        assert len(adcm_object.multi_state) == 0, "Expected object have multi state while multi state is unexpected"
