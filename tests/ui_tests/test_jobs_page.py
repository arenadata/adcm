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
import os
from typing import Union

import allure
import pytest
from adcm_client.objects import (
    ADCMClient,
    Cluster,
    Bundle,
    Provider,
    Service,
    Host,
)
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
)

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.cluster_list.page import ClusterListPage
from tests.ui_tests.app.page.job_list.page import (
    JobListPage,
    JobStatus,
)
from tests.ui_tests.utils import wait_and_assert_ui_info, is_not_empty, is_empty

LONG_ACTION_DISPLAY_NAME = 'Long action'
SUCCESS_ACTION_DISPLAY_NAME = 'Success action'
FAIL_ACTION_DISPLAY_NAME = 'Fail action'
ON_HOST_ACTION_DISPLAY_NAME = 'Component host action'
COMPONENT_ACTION_DISPLAY_NAME = 'Component action'

CLUSTER_NAME = 'test_cluster'
SERVICE_NAME = 'test_service'
COMPONENT_NAME = 'test_component'

# pylint: disable=redefined-outer-name


@pytest.fixture()
# pylint: disable-next=unused-argument
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
        'invoker_objects': owner_name,
    }
    with allure.step(
        f'Run action "{LONG_ACTION_DISPLAY_NAME}" on {action_owner.__class__}'
    ), page.table.wait_rows_change():
        long_action = action_owner.action(display_name=LONG_ACTION_DISPLAY_NAME)
        long_action.run()
    _check_job_info_in_popup(page, {'status': expected_info['status'], 'action_name': expected_info['action_name']})
    _check_running_job_info_in_table(page, expected_info)
    page.select_filter_running_tab()
    _check_running_job_info_in_table(page, expected_info)


@allure.step('Check running job information in table')
def _check_running_job_info_in_table(page: JobListPage, expected_info: dict):
    """Get info about job from table and check it"""
    wait_and_assert_ui_info(
        {**expected_info, 'start_date': is_not_empty, 'finish_date': is_empty},
        page.get_task_info_from_table,
    )


@allure.step('Check finished job information in table')
def _check_finished_job_info_in_table(page: JobListPage, expected_info: dict):
    """Get and check info about successfully finished job from table"""
    wait_and_assert_ui_info(
        {**expected_info, 'start_date': is_not_empty, 'finish_date': is_not_empty},
        page.get_task_info_from_table,
    )


@allure.step('Check job information in popup')
def _check_job_info_in_popup(page: JobListPage, expected_info: dict):
    """Get job info from popup and check it"""
    with page.header.open_jobs_popup():
        wait_and_assert_ui_info({**expected_info}, page.get_task_info_from_popup)


# !===== TESTS =====!

@pytest.mark.smoke()
class TestTaskPage:

    def test_cluster_action_job(self, cluster: Cluster, page: JobListPage):
        """Run action on cluster and validate job in table and popup"""
        _test_run_action(page, cluster)

    def test_service_action_job(self, cluster: Cluster, page: JobListPage):
        """Run action on service and validate job in table and popup"""
        _test_run_action(page, cluster.service_list()[0])

    def test_provider_action_job(self, provider: Provider, page: JobListPage):
        """Run action on host provider and validate job in table and popup"""
        _test_run_action(page, provider)

    def test_host_action_job(self, provider: Provider, page: JobListPage):
        """Run action on host and validate job in table and popup"""
        _test_run_action(page, provider.host_create('some-fqdn'))

    @pytest.mark.parametrize(
        'job_info',
        [
            {
                'expected_status': 'success',
                'status': JobStatus.SUCCESS,
                'action_name': SUCCESS_ACTION_DISPLAY_NAME,
            },
            {
                'expected_status': 'failed',
                'status': JobStatus.FAILED,
                'action_name': FAIL_ACTION_DISPLAY_NAME,
            },
        ],
        ids=['success_job', 'failed_job'],
    )
    def test_finished_job_has_correct_info(self, job_info: dict, cluster: Cluster, page: JobListPage):
        """Run action that finishes (success/failed) and check it is displayed correctly"""
        expected_info_in_popup = {**job_info}
        expected_status = expected_info_in_popup.pop('expected_status')
        expected_info_in_table = {**expected_info_in_popup, 'invoker_objects': cluster.name}
        with allure.step(f'Run action and wait for "{expected_status}" status'):
            action = cluster.action(display_name=expected_info_in_popup['action_name'])
            run_cluster_action_and_assert_result(cluster, action.name, status=expected_status)
        _check_finished_job_info_in_table(page, expected_info_in_table)
        open_filter_on_page = getattr(page, f'select_filter_{expected_status}_tab')
        open_filter_on_page()
        _check_finished_job_info_in_table(page, expected_info_in_table)
        _check_job_info_in_popup(page, expected_info_in_popup)


class TestTaskHeaderPopup:

    def test_link_to_all_jobs_on_task_page(self, login_to_adcm_over_api, app_fs):
        """Link to /task from popup with all filter"""

        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        cluster_page.header.click_job_block_in_header()
        cluster_page.header.click_all_link_in_job_popup()
        JobListPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()

    def test_link_to_in_progress_jobs_on_task_page(self, login_to_adcm_over_api, app_fs):
        """Link to /task from popup with in_progress filter"""

        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        cluster_page.header.click_job_block_in_header()
        cluster_page.header.click_in_progress_in_job_popup()
        JobListPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()

    def test_link_to_success_jobs_on_task_page(self, login_to_adcm_over_api, app_fs):
        """Link to /task from popup with success filter"""

        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        cluster_page.header.click_job_block_in_header()
        cluster_page.header.click_success_jobs_in_job_popup()
        JobListPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()

    def test_link_to_failed_jobs_on_task_page(self, login_to_adcm_over_api, app_fs):
        """Link to /task from popup with failed filter"""

        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        cluster_page.header.click_job_block_in_header()
        cluster_page.header.click_failed_jobs_in_job_popup()
        JobListPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()

    def test_acknowledge_jobs_in_header_popup(self, cluster: Cluster, page: JobListPage):
        """Run action and click acknowledge in header popup"""

        page.header.click_job_block_in_header()

    @pytest.mark.parametrize(
        'job_info',
        [
            {
                'expected_status': 'success',
                'status': JobStatus.SUCCESS,
                'action_name': SUCCESS_ACTION_DISPLAY_NAME,
            },
            {
                'expected_status': 'failed',
                'status': JobStatus.FAILED,
                'action_name': FAIL_ACTION_DISPLAY_NAME,
            },
        ],
        ids=['success_job', 'failed_job'],
    )
    def test_job_has_correct_info_in_header_popup(self, job_info: dict, cluster: Cluster, page: JobListPage):
        """Run action that finishes (success/failed) and check it in header popup"""
        expected_info_in_popup = {**job_info}
        expected_status = expected_info_in_popup.pop('expected_status')
        expected_info_in_table = {**expected_info_in_popup, 'invoker_objects': cluster.name}
        with allure.step(f'Run action and wait for "{expected_status}" status'):
            action = cluster.action(display_name=expected_info_in_popup['action_name'])
            run_cluster_action_and_assert_result(cluster, action.name, status=expected_status)
        _check_finished_job_info_in_table(page, expected_info_in_table)
        open_filter_on_page = getattr(page, f'select_filter_{expected_status}_tab')
        open_filter_on_page()
        _check_finished_job_info_in_table(page, expected_info_in_table)
        _check_job_info_in_popup(page, expected_info_in_popup)