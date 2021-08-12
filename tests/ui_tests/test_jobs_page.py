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
from typing import Union

import os
import pytest
import allure

from adcm_client.objects import ADCMClient, Cluster, Bundle, Provider, Service, Host
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.job_list.page import (
    JobListPage,
    JobStatus,
    TableTaskInfo,
    TaskInfo,
)


LONG_ACTION_DISPLAY_NAME = 'Long action'
SUCCESS_ACTION_DISPLAY_NAME = 'Success action'
FAIL_ACTION_DISPLAY_NAME = 'Fail action'

CLUSTER_NAME = 'Great Cluster'
SERVICE_NAME = 'Serviceno'

# pylint: disable=redefined-outer-name


@pytest.fixture()
def page(app_fs: ADCMTest, login_to_adcm_over_api) -> JobListPage:
    return JobListPage(app_fs.driver, app_fs.adcm.url).open()


@allure.title("Upload cluster bundle")
@pytest.fixture()
def cluster_bundle(sdk_client_fs: ADCMClient) -> Bundle:
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), "cluster"))


@allure.title("Upload provider bundle")
@pytest.fixture()
def provider_bundle(sdk_client_fs: ADCMClient) -> Bundle:
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), "provider"))


@allure.title("Create cluster")
@pytest.fixture()
def cluster(cluster_bundle: Bundle) -> Cluster:
    """Creates cluster and adds service"""
    cluster = cluster_bundle.cluster_create(CLUSTER_NAME)
    cluster.service_add(name=SERVICE_NAME)
    return cluster


@allure.title("Create provider")
@pytest.fixture()
def provider(provider_bundle: Bundle) -> Provider:
    return provider_bundle.provider_create('Awesome Provider')


def test_cluster_action_job(cluster: Cluster, page: JobListPage):
    """Run action on cluster and validate job in table and popup"""
    _test_run_action(page, cluster)


def test_service_action_job(cluster: Cluster, page: JobListPage):
    """Run action on service and validate job in table and popup"""
    _test_run_action(page, cluster.service_list()[0])


def test_provider_action_job(provider: Provider, page: JobListPage):
    """Run action on host provider and validate job in table and popup"""
    _test_run_action(page, provider)


def test_host_action_job(provider: Provider, page: JobListPage):
    """Run action on host and validate job in table and popup"""
    _test_run_action(page, provider.host_create('some-fqdn'))


def test_run_successful_job(cluster: Cluster, page: JobListPage):
    """Run action that finishes successfully and check it is displayed correctly"""
    expected_info = {
        'status': JobStatus.SUCCESS,
        'action_name': SUCCESS_ACTION_DISPLAY_NAME,
        'object': cluster.name,
    }
    with allure.step('Run action and wait it succeeded'):
        action = cluster.action(display_name=SUCCESS_ACTION_DISPLAY_NAME)
        run_cluster_action_and_assert_result(cluster, action.name)
    _check_finished_job_info_in_table(page, expected_info)
    page.select_filter_success_tab()
    _check_finished_job_info_in_table(page, expected_info)
    _check_job_info_in_popup(
        page, {'status': expected_info['status'], 'action_name': expected_info['action_name']}
    )


def test_run_fail_job(cluster: Cluster, page: JobListPage):
    """Run action that fails and check it is displayed correctly"""
    expected_info = {
        'status': JobStatus.FAILED,
        'action_name': FAIL_ACTION_DISPLAY_NAME,
        'object': cluster.name,
    }
    with allure.step('Run action and wait it succeeded'):
        action = cluster.action(display_name=FAIL_ACTION_DISPLAY_NAME)
        run_cluster_action_and_assert_result(cluster, action.name, status='failed')
    _check_finished_job_info_in_table(page, expected_info)
    page.select_filter_failed_tab()
    _check_finished_job_info_in_table(page, expected_info)
    _check_job_info_in_popup(
        page, {'status': expected_info['status'], 'action_name': expected_info['action_name']}
    )


def _test_run_action(page: JobListPage, action_owner: Union[Cluster, Service, Provider, Host]):
    """
    Run the "Long" action
    Check popup info
    Check table info without filter (All)
    Activate filter "Running"
    Check table info
    """
    owner_name = action_owner.name if action_owner.__class__ != Host else action_owner.fqdn
    expected_info = {
        'status': JobStatus.RUNNING,
        'action_name': LONG_ACTION_DISPLAY_NAME,
        'object': owner_name,
    }
    with allure.step(
        f'Run action "{LONG_ACTION_DISPLAY_NAME}" on {action_owner.__class__}'
    ), page.table.wait_rows_change():
        long_action = action_owner.action(display_name=LONG_ACTION_DISPLAY_NAME)
        long_action.run()
    _check_job_info_in_popup(
        page, {'status': expected_info['status'], 'action_name': expected_info['action_name']}
    )
    _check_running_job_info_in_table(page, expected_info)
    page.select_filter_running_tab()
    _check_running_job_info_in_table(page, expected_info)


@allure.step('Check running job information in table')
def _check_running_job_info_in_table(page: JobListPage, expected_info: dict):
    """Get info about job from table and check it"""
    job_info = page.get_task_info_from_table()
    __check_basic_job_info(job_info, expected_info)
    __check_only_finish_date_is_empty(job_info)


@allure.step('Check finished job information in table')
def _check_finished_job_info_in_table(page: JobListPage, expected_info: dict):
    """Get and check info about successfully finished job from table"""
    job_info = page.get_task_info_from_table()
    __check_basic_job_info(job_info, expected_info)
    __check_both_dates_not_empty(job_info)


@allure.step('Check job information in popup')
def _check_job_info_in_popup(page: JobListPage, expected_info: dict):
    """Get job info from popup and check it"""
    with page.header.open_jobs_popup():
        job_info = page.get_task_info_from_popup()
        __check_basic_job_info(job_info, expected_info)


def __check_basic_job_info(job_info: TaskInfo, expected_info: dict):
    """Check job info is same as expected (excluding start/finish date check)"""
    for key in expected_info.keys():
        assert (
            job_info[key] == expected_info[key]
        ), f'Field "{key}" should be {expected_info[key]}, not {job_info[key]}'


def __check_only_finish_date_is_empty(job_info: TableTaskInfo):
    """Check finish date is empty, start date is not"""
    assert job_info['finish_date'] == '', 'Finish date should be empty'
    assert job_info['start_date'] != '', 'Start date should not be empty'


def __check_both_dates_not_empty(job_info: TableTaskInfo):
    """Check both start and finish dates are not empty"""
    assert job_info['finish_date'] != '', 'Finish date should not be empty'
    assert job_info['start_date'] != '', 'Start date should not be empty'
