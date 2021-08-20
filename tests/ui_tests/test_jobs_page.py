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
from dataclasses import asdict
from typing import Union, List

import os
import pytest
import allure

from adcm_pytest_plugin import utils
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
)
from adcm_client.objects import (
    ADCMClient,
    Cluster,
    Bundle,
    Provider,
    Service,
    Host,
    Component,
    Action,
)

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.job.page import JobPage
from tests.ui_tests.app.page.job_list.page import (
    JobListPage,
    JobStatus,
    TableTaskInfo,
)
from tests.ui_tests.utils import (
    wait_and_assert_ui_info,
    is_not_empty,
    is_empty,
    wait_file_is_presented,
)

LONG_ACTION_DISPLAY_NAME = 'Long action'
SUCCESS_ACTION_DISPLAY_NAME = 'Success action'
FAIL_ACTION_DISPLAY_NAME = 'Fail action'
ON_HOST_ACTION_DISPLAY_NAME = 'Component host action'
COMPONENT_ACTION_DISPLAY_NAME = 'Component action'
MULTIJOB_ACTION_DISPLAY_NAME = 'Multijob'

CLUSTER_NAME = 'test_cluster'
SERVICE_NAME = 'test_service'
COMPONENT_NAME = 'test_component'

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


@pytest.fixture()
def created_hosts(provider: Provider) -> List[Host]:
    """Create 11 hosts for "parallel" actions execution"""
    return [provider.host_create(f'host-{i}') for i in range(11)]


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
def test_finished_job_has_correct_info(job_info: dict, cluster: Cluster, page: JobListPage):
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


def test_run_multijob(cluster: Cluster, page: JobListPage):
    """Run action with many jobs"""
    with allure.step('Run action with multiple job'):
        action = cluster.action(display_name=MULTIJOB_ACTION_DISPLAY_NAME)
        task = run_cluster_action_and_assert_result(cluster, action.name)
    page.expand_task_in_row(0)
    with allure.step('Check jobs info'):
        expected_jobs = [{'name': job['name'], 'status': JobStatus.SUCCESS} for job in action.subs]
        jobs_info = page.get_all_jobs_info()
        assert (expected_amount := len(expected_jobs)) == (actual_amount := len(jobs_info)), (
            'Amount of jobs is not correct: '
            f'should be {expected_amount}, but {actual_amount} was found'
        )
        for i in range(actual_amount):
            assert (actual_info := asdict(jobs_info[i])) == (
                expected_info := expected_jobs[i]
            ), f'Job at position #{i} should be {expected_info}, not {actual_info}'
    with allure.step("Open first job's page"):
        page.click_on_job()
        detail_page = JobPage(page.driver, page.base_url, task.jobs[0]['id'])
        detail_page.wait_page_is_opened()


def test_filtering_and_pagination(created_hosts: List[Host], page: JobListPage):
    """Check filtering and pagination"""
    params = {'success': 6, 'failed': 5, 'second_page': 1}
    _run_actions_on_hosts(created_hosts)
    with allure.step('Check status filtering'):
        with page.table.wait_rows_change():
            page.select_filter_failed_tab()
        assert (row_count := page.table.row_count) == params['failed'], (
            f'Tab "Failed" should have {params["failed"]} rows, '
            f'but {row_count} rows are presented'
        )
        with page.table.wait_rows_change():
            page.select_filter_success_tab()
        assert (row_count := page.table.row_count) == params['success'], (
            f'Tab "Success" should have {params["success"]}, ' f'but {row_count} rows are presented'
        )
    with allure.step('Check pagination'):
        with page.table.wait_rows_change():
            page.select_filter_all_tab()
        page.table.check_pagination(params['second_page'])


def test_open_task_by_click_on_name(cluster: Cluster, page: JobListPage):
    """Click on task name and task page should be opened"""
    with allure.step('Run "Long" action'), page.table.wait_rows_change():
        task = cluster.action(display_name=LONG_ACTION_DISPLAY_NAME).run()
    with allure.step('Click on task name'):
        page.click_on_action_name_in_row(page.table.get_row())
    with allure.step('Check Task detailed page is opened'):
        job_page = JobPage(page.driver, page.base_url, task.id)
        job_page.wait_page_is_opened()


@pytest.mark.parametrize('log_type', ['stdout', 'stderr'], ids=['stdout_menu', 'stderr_menu'])
@pytest.mark.usefixtures('login_to_adcm_over_api')
def test_open_log_menu(log_type: str, cluster: Cluster, app_fs: ADCMTest):
    """Open stdout/stderr log menu and check info"""
    action = cluster.action(display_name=SUCCESS_ACTION_DISPLAY_NAME)
    task = run_cluster_action_and_assert_result(cluster, action.name)
    job_page = _open_detailed_job_page(task.jobs[0]['id'], app_fs)
    with allure.step(f'Open menu with {log_type} logs and check all info is presented'):
        getattr(job_page, f'open_{log_type}_menu')()
        wait_and_assert_ui_info(
            {
                'name': SUCCESS_ACTION_DISPLAY_NAME,
                'invoker_objects': cluster.name,
                'start_date': is_not_empty,
                'finish_date': is_not_empty,
                'execution_time': is_not_empty,
            },
            job_page.get_job_info,
        )


@pytest.mark.usefixtures("login_to_adcm_over_api", "clean_downloads_fs")
def test_download_log(cluster: Cluster, app_fs: ADCMTest, downloads_directory):
    """Download log file from detailed page menu"""
    downloaded_file_template = '{job_id}-ansible-{log_type}.txt'
    action = cluster.action(display_name=SUCCESS_ACTION_DISPLAY_NAME)
    task = run_cluster_action_and_assert_result(cluster, action.name)
    job_id = task.jobs[0]['id']
    job_page = _open_detailed_job_page(task.jobs[0]['id'], app_fs)
    with allure.step('Download logfiles'):
        job_page.click_on_log_download('stdout')
        wait_file_is_presented(
            downloaded_file_template.format(job_id=job_id, log_type='stdout'), downloads_directory
        )
        job_page.click_on_log_download('stderr')
        wait_file_is_presented(
            downloaded_file_template.format(job_id=job_id, log_type='stderr'), downloads_directory
        )


def test_invoker_object_url(cluster: Cluster, provider: Provider, page: JobListPage):
    """Check link to object that invoked action is correct"""
    host_fqdn = 'run-on-me'
    host_job_link = f'{host_fqdn}/{provider.name}'
    component_link = f'{COMPONENT_NAME}/{SERVICE_NAME}/{CLUSTER_NAME}'
    host_component_link = f'{host_fqdn}/{component_link}'
    with allure.step('Run action on component and check job link to it'):
        service: Service = cluster.service(name=SERVICE_NAME)
        component: Component = service.component(name=COMPONENT_NAME)
        component_action = component.action(display_name=COMPONENT_ACTION_DISPLAY_NAME)
        _check_link_to_invoker_object_in_table('component', component_link, page, component_action)
    with allure.step('Create host, run action on host and check job link to it'):
        host = provider.host_create(host_fqdn)
        host_action = host.action(display_name=FAIL_ACTION_DISPLAY_NAME)
        _check_link_to_invoker_object_in_table('host', host_job_link, page, host_action)
    with allure.step('Add host to the cluster, assign component on it'):
        cluster.host_add(host)
        cluster.hostcomponent_set((host, component))
    with allure.step('Run component host action on host and check job link to it'):
        host_action = host.action(display_name=ON_HOST_ACTION_DISPLAY_NAME)
        _check_link_to_invoker_object_in_table('host', host_component_link, page, host_action)


# !==== HELPERS =====!


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
    _check_job_info_in_popup(
        page, {'status': expected_info['status'], 'action_name': expected_info['action_name']}
    )
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


@allure.step('Run 6 success and 5 failed actions on 11 hosts')
def _run_actions_on_hosts(hosts: List[Host]):
    """
    Run 6 success and 5 failed actions
    and then wait for all of them to be finished
    """
    actions_distribution = [SUCCESS_ACTION_DISPLAY_NAME] * 6 + [FAIL_ACTION_DISPLAY_NAME] * 5
    task_list = [
        host.action(display_name=actions_distribution[i]).run() for i, host in enumerate(hosts)
    ]
    for task in task_list:
        task.wait(timeout=60)


@allure.step('Open detailed job page')
def _open_detailed_job_page(job_id: int, app_fs: ADCMTest) -> JobPage:
    """Open detailed job page"""
    return JobPage(app_fs.driver, app_fs.adcm.url, job_id).open()


def _check_link_to_invoker_object_in_table(
    link_object_name: str, expected_link: str, page: JobListPage, action: Action
):
    """
    Check that link to object invoked action is correct
    :param link_object_name: Name of object to add in assertion message like 'host', 'component'
    :param expected_link: "Link" to invoker objects
    :param page: Page with jobs table
    :param action: Action to run
    """
    with page.table.wait_rows_change():
        action.run()
    task_info: TableTaskInfo = page.get_task_info_from_table(full_invoker_objects_link=True)
    assert (actual_link := task_info.invoker_objects) == expected_link, (
        f'Link to {link_object_name} object in jobs table '
        f'should be "{expected_link}", not "{actual_link}"'
    )
    detail_page = JobPage(page.driver, page.base_url, action.task_list()[0].id).open()
    actual_link = detail_page.get_job_info().invoker_objects
    assert actual_link == expected_link, (
        f'Link to {link_object_name} object on detailed job page '
        f'should be "{expected_link}", not "{actual_link}"'
    )
    page.open()
