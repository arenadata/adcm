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

import re
import pytest
import allure

from coreapi.exceptions import ErrorMessage

from adcm_client.objects import ADCMClient, Cluster
from adcm_pytest_plugin import utils as plugin_utils
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result

# pylint: disable=redefined-outer-name


@pytest.fixture()
def cluster(sdk_client_fs: ADCMClient) -> Cluster:
    """Get cluster"""
    uploaded_bundle = sdk_client_fs.upload_from_fs(plugin_utils.get_data_dir(__file__, "cluster"))
    return uploaded_bundle.cluster_create('test_cluster')


def test_config_not_presented(cluster: Cluster):
    """
    Action's configuration not presented
    Run action with config
    """
    expected_message = (
        "The task includes an option with an undefined variable. "
        "The error was: 'dict object' has no attribute 'config'"
    )
    with allure.step('Run action without config and expect it to fail with ansible error'):
        task = run_cluster_action_and_assert_result(cluster, 'no_config', 'failed', config={'some_param': 1})
    with allure.step('Check that stdout log contains error message'):
        assert expected_message in (
            log := task.job().log(type='stdout').content
        ), f'stdout expected to contain message: {expected_message}\nBut log was: {log}'


def test_incorrect_config(cluster: Cluster, sdk_client_fs: ADCMClient):
    """
    Action's configuration not presented
    Run action with "incorrect" config
    """
    job_count = len(sdk_client_fs.job_list())
    with allure.step('Run action with "incorrect" config and expect ADCM response with non 500 status code'):
        try:
            run_cluster_action_and_assert_result(cluster, 'with_config', 'failed', config={'no_such_param': 1})
        except ErrorMessage as e:
            _check_error_message(e)
        else:
            raise AssertionError("Action should've failed")
    with allure.step("Check that job wasn't launched"):
        _check_job_count_equal_to(job_count, sdk_client_fs)


def test_pass_no_config(cluster: Cluster, sdk_client_fs: ADCMClient):
    """
    Action has config
    Run action without config
    """
    job_count = len(sdk_client_fs.job_list())
    with allure.step(
        'Run action that required config without config and expect ADCM to response with non 500 status code'
    ):
        try:
            run_cluster_action_and_assert_result(cluster, 'with_config', 'failed')
        except ErrorMessage as e:
            _check_error_message(e)
        else:
            raise AssertionError("Action run should've failed")
    with allure.step("Check that job wasn't launched"):
        _check_job_count_equal_to(job_count, sdk_client_fs)


def _check_error_message(error: ErrorMessage):
    """Check status code in error message is less than 500"""
    status_code = _extract_status_code(error)
    assert 400 <= status_code < 500, f"Response expected to have less than 500 status code, but {status_code} was found"


def _check_job_count_equal_to(count: int, adcm_client: ADCMClient):
    """Check that job count is equal to expected"""
    assert (
        job_count := len(adcm_client.job_list())
    ) == count, f'Amount of jobs expected is {count}, but {job_count} was found'


def _extract_status_code(error: ErrorMessage) -> int:
    """Get status code as integer from error message"""
    err_message = error.error.title
    err_code_pattern = re.compile(r"\d{3}")
    match = re.search(err_code_pattern, err_message)
    if not match:
        raise ValueError(f"Status code wasn't found in client response error text: {err_message}")
    return int(match[0])
