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

"""Test "allow_to_terminate" action directive"""

import allure
import pytest
from adcm_client.objects import Cluster, Component
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from tests.library.assertions import expect_api_error, expect_no_api_error

# pylint: disable=redefined-outer-name

CANCELLED_STATUS = 'aborted'

pytestmark = [pytest.mark.parametrize('generic_bundle', ['action_termination_allowed'], indirect=True)]


@pytest.fixture()
def cluster(generic_bundle) -> Cluster:
    """Create cluster from newly uploaded bundle"""
    return generic_bundle.cluster_create('Test Cluster')


@pytest.mark.parametrize('action_name', ['multi', 'simple'])
def test_allow_to_terminate(action_name: str, cluster):
    """Test that tasks that are allowed to be terminated are cancelled correctly"""
    with allure.step(f'Run action {action_name} and terminate it right away'):
        task = cluster.action(name=action_name).run()
        # action need time to "actually" launch
        wait_until_step_succeeds(
            expect_no_api_error,
            timeout=5,
            period=0.5,
            operation_name=f'cancel task from action "{action_name}"',
            operation=task.cancel,
        )

    with allure.step('Check that action execution is cancelled correctly'):
        _wait_state_is_aborted(task)
        assert any(
            j.status == CANCELLED_STATUS for j in task.job_list()
        ), f'At least one job of the cancelled task should have status "{CANCELLED_STATUS}"'
        assert (
            len(cluster.concerns()) == 0
        ), 'There should not be any concerns on the cluster object after task termination'
        assert cluster.action_list() != [], 'Actions should be available on cluster'


def test_disallow_to_terminate(cluster):
    """Test that actions that are disallowed to be terminated actually can't be cancelled"""
    action_name = 'unstoppable'

    with allure.step('Run action that cannot be terminated and try to cancel it'):
        task = cluster.action(name=action_name).run()
        expect_api_error('cancel task that cannot be stopped', task.cancel)
    with allure.step('Check that action execution is continued'):
        task.reread()
        assert task.status != CANCELLED_STATUS, 'Wrong status: task should not be cancelled'
        assert all(j.status != CANCELLED_STATUS for j in task.job_list()), 'None of jobs in task should be cancelled'
        task.wait()
        assert (
            len(cluster.concerns()) == 0
        ), 'There should not be any concerns on the cluster object after the task is finished'
        assert cluster.action_list() != [], 'Actions should be available on cluster'


def test_terminate_action_with_hc_acl(cluster, generic_provider):
    """Test that termination of action with hc_acl leads to "restore" of previous HC map"""
    original_hc = ()
    host = cluster.host_add(generic_provider.host_create('something'))
    component: Component = cluster.service_add(name='test_service').component()

    with allure.step('Run action with hc_acl and terminate it right away'):
        task = cluster.action(name='with_hc_acl').run(
            hc=[
                {
                    'host_id': host.id,
                    'service_id': component.service_id,
                    'component_id': component.id,
                }
            ]
        )
        # action need time to "actually" launch
        wait_until_step_succeeds(
            expect_no_api_error,
            timeout=5,
            period=0.5,
            operation_name='cancel task with hc_acl',
            operation=task.cancel,
        )

    with allure.step('Check that HC is the same as the original one after task is cancelled'):
        _wait_state_is_aborted(task)
        cluster.reread()
        new_hc = tuple(cluster.hostcomponent())
        assert new_hc == original_hc, 'Hostcomponent is incorrect after cancellation of action with hc_acl'


def _wait_state_is_aborted(task):
    # cancellation can take a moment
    def _wait_cancel():
        task.reread()
        assert (
            actual_status := task.status
        ) == CANCELLED_STATUS, f'Task should be of status "{CANCELLED_STATUS}", not "{actual_status}"'

    wait_until_step_succeeds(_wait_cancel, timeout=5, period=0.5)
