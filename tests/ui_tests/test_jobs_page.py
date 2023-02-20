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

"""UI tests for /jobs page"""

import os
from dataclasses import asdict

import allure
import pytest
import requests
from adcm_client.objects import (
    Action,
    ADCMClient,
    Bundle,
    Cluster,
    Component,
    Host,
    Job,
    ObjectNotFound,
    Provider,
    Service,
)
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result
from adcm_pytest_plugin.utils import (
    catch_failed,
    get_data_dir,
    wait_until_step_succeeds,
)

from tests.functional.audit.conftest import check_succeed, make_auth_header
from tests.functional.tools import wait_all_jobs_are_finished, wait_for_job_status
from tests.library.predicates import display_name_is
from tests.library.utils import build_full_archive_name, get_or_raise
from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.cluster.page import ClusterServicesPage
from tests.ui_tests.app.page.cluster_list.page import ClusterListPage
from tests.ui_tests.app.page.job.page import JobPageStdout
from tests.ui_tests.app.page.job_list.page import JobListPage, JobStatus
from tests.ui_tests.app.page.login.page import LoginPage
from tests.ui_tests.app.page.service.page import ServiceMainPage
from tests.ui_tests.core.checks import check_pagination
from tests.ui_tests.utils import (
    is_empty,
    is_not_empty,
    wait_and_assert_ui_info,
    wait_file_is_presented,
)

LONG_ACTION_DISPLAY_NAME = "Long action"
SUCCESS_ACTION_DISPLAY_NAME = "Success action"
SUCCESS_ACTION_NAME = "success_action"
CHECK_ACTION_NAME = "with_check"
FAIL_ACTION_DISPLAY_NAME = "Fail action"
ON_HOST_ACTION_DISPLAY_NAME = "Component host action"
COMPONENT_ACTION_DISPLAY_NAME = "Component action"
MULTIJOB_ACTION_DISPLAY_NAME = "Multijob"
ONE_JOB_ACTION = "one_job_action"

CLUSTER_NAME = "test cluster"
SERVICE_NAME = "test_service"
COMPONENT_NAME = "test_component"

FIRST_STEP_TASK = "first_step"
THIRD_STEP_TASK = "third_step"

# pylint: disable=redefined-outer-name


@pytest.fixture()
@allure.title("Open /task page")
def page(app_fs: ADCMTest, _login_to_adcm_over_api) -> JobListPage:
    """Open /task page"""
    return JobListPage(app_fs.driver, app_fs.adcm.url).open()


@allure.title("Upload cluster bundle")
@pytest.fixture()
def cluster_bundle(sdk_client_fs: ADCMClient) -> Bundle:
    """Upload cluster bundle"""
    return sdk_client_fs.upload_from_fs(os.path.join(get_data_dir(__file__), "cluster"))


@allure.title("Upload provider bundle")
@pytest.fixture()
def provider_bundle(sdk_client_fs: ADCMClient) -> Bundle:
    """Upload provider bundle"""
    return sdk_client_fs.upload_from_fs(os.path.join(get_data_dir(__file__), "provider"))


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
    """Create provider"""
    return provider_bundle.provider_create("Awesome Provider")


@pytest.fixture()
@allure.title("Create 11 hosts for 'parallel' actions execution")
def created_hosts(provider: Provider) -> list[Host]:
    """Create 11 hosts for "parallel" actions execution"""
    return [provider.host_create(f"host-{i}") for i in range(11)]


# !===== TESTS =====!
class TestTaskPage:
    """Tests for Task page"""

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_cluster_action_job(self, cluster: Cluster, page: JobListPage):
        """Run action on cluster and validate job in table and popup"""
        _test_run_action(page, cluster, cluster.name)

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_service_action_job(self, cluster: Cluster, page: JobListPage):
        """Run action on service and validate job in table and popup"""
        service = cluster.service_list()[0]
        _test_run_action(page, service, f"{cluster.name}/{service.name}")

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_component_action_job(self, cluster: Cluster, page: JobListPage):
        """Run action on component and validate job in table and popup"""
        service = cluster.service_list()[0]
        component = service.component()
        _test_run_action(page, component, f"{cluster.name}/{service.name}/{component.name}")

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_provider_action_job(self, provider: Provider, page: JobListPage):
        """Run action on host provider and validate job in table and popup"""
        _test_run_action(page, provider, provider.name)

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_host_action_job(self, provider: Provider, page: JobListPage):
        """Run action on host and validate job in table and popup"""
        host = provider.host_create("some-fqdn")
        _test_run_action(page, host, f"{provider.name}/{host.fqdn}")

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.parametrize(
        "job_info",
        [
            {
                "status": JobStatus.SUCCESS,
                "action_name": SUCCESS_ACTION_DISPLAY_NAME,
            },
            {
                "status": JobStatus.FAILED,
                "action_name": FAIL_ACTION_DISPLAY_NAME,
            },
        ],
        ids=["success_job", "failed_job"],
    )
    def test_finished_job_has_correct_info(self, job_info: dict, cluster: Cluster, page: JobListPage):
        """Run action that finishes (success/failed) and check it is displayed correctly"""
        expected_info_in_popup = {**job_info}
        expected_status = expected_info_in_popup.get("status").value
        expected_info_in_table = {**expected_info_in_popup, "invoker_objects": cluster.name}
        with allure.step(f'Run action and wait for "{expected_status}" status'):
            action = cluster.action(display_name=expected_info_in_popup["action_name"])
            run_cluster_action_and_assert_result(cluster, action.name, status=expected_status)
        _check_finished_job_info_in_table(page, expected_info_in_table)
        open_filter_on_page = getattr(page, f"select_filter_{expected_status}_tab")
        open_filter_on_page()
        _check_finished_job_info_in_table(page, expected_info_in_table)
        _check_job_info_in_popup(page, expected_info_in_popup)

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_run_multijob(self, cluster: Cluster, page: JobListPage):
        """Run action with many jobs"""
        with allure.step("Run action with multiple job"):
            action = cluster.action(display_name=MULTIJOB_ACTION_DISPLAY_NAME)
            task = run_cluster_action_and_assert_result(cluster, action.name)
        page.expand_task_in_row(0)
        with allure.step("Check jobs info"):
            expected_jobs = [{"name": job["name"], "status": JobStatus.SUCCESS} for job in action.subs]
            jobs_info = page.get_all_jobs_info()
            assert (expected_amount := len(expected_jobs)) == (actual_amount := len(jobs_info)), (
                "Amount of jobs is not correct: " f"should be {expected_amount}, but {actual_amount} was found"
            )
            for i in range(actual_amount):
                assert (actual_info := asdict(jobs_info[i])) == (
                    expected_info := expected_jobs[i]
                ), f"Job at position #{i} should be {expected_info}, not {actual_info}"
        with allure.step("Open first job's page"):
            page.click_on_job()
            detail_page = JobPageStdout(page.driver, page.base_url, task.jobs[0]["id"])
            detail_page.wait_page_is_opened()

    def test_cancel_multijob_cluster(self, app_fs, sdk_client_fs, cluster: Cluster, page: JobListPage):
        """Run action on cluster with many jobs and cancel last job. Expect task status aborted"""
        with allure.step("Run action with multiple job"):
            expected_cluster_state = cluster.state
            action = cluster.action(display_name=MULTIJOB_ACTION_DISPLAY_NAME)
            task = action.run()
            last_job = get_or_raise(task.job_list(), display_name_is(THIRD_STEP_TASK))
            wait_for_job_status(job=last_job, timeout=30, period=2)

        _cancel_job(sdk_client_fs, job=last_job)
        wait_all_jobs_are_finished(sdk_client_fs)

        with allure.step("Check jobs info"):
            page.expand_task_in_row(0)
            expected_jobs = [
                {
                    "name": job["name"],
                    "status": JobStatus.SUCCESS if job["name"] != THIRD_STEP_TASK else JobStatus.ABORTED,
                }
                for job in action.subs
            ]
            jobs_info = [asdict(i) for i in page.get_all_jobs_info()]
            assert jobs_info == expected_jobs, f"Actual jobs: {jobs_info} not found in expected jobs {expected_jobs}"

        with allure.step("Check object state"):
            cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
            row = cluster_page.get_row_by_cluster_name(cluster.name)
            assert (
                cluster_page.get_cluster_state_from_row(row) == expected_cluster_state
            ), f"State of {cluster.name} should be {expected_cluster_state}"

    def test_cancel_multijob_service(self, app_fs, sdk_client_fs, cluster: Cluster, page: JobListPage):
        """Run action with many jobs on service and cancel last job. Expect task status aborted"""
        with allure.step("Run action with one job"):
            service = cluster.service(name=SERVICE_NAME)
            expected_service_state = service.state
            action = service.action(display_name=MULTIJOB_ACTION_DISPLAY_NAME)
            task = action.run()
            last_job = get_or_raise(task.job_list(), display_name_is(THIRD_STEP_TASK))
            wait_for_job_status(job=last_job, timeout=30, period=2)

        _cancel_job(sdk_client_fs, job=last_job)
        wait_all_jobs_are_finished(sdk_client_fs)

        with allure.step("Check jobs info"):
            page.expand_task_in_row(0)
            expected_jobs = [
                {
                    "name": job["name"],
                    "status": JobStatus.SUCCESS if job["name"] != THIRD_STEP_TASK else JobStatus.ABORTED,
                }
                for job in action.subs
            ]
            jobs_info = [asdict(i) for i in page.get_all_jobs_info()]
            assert jobs_info == expected_jobs, f"Actual jobs: {jobs_info} not found in expected jobs {expected_jobs}"

        with allure.step("Check object state"):
            cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
            row = cluster_service_page.table.get_all_rows()[0]
            assert (
                cluster_service_page.get_service_state_from_row(row) == expected_service_state
            ), f"State of {service.name}  should be {expected_service_state}"

    def test_cancel_multijob_component(self, app_fs, sdk_client_fs, cluster: Cluster, page: JobListPage):
        """Run action with many jobs on component and cancel last job. Expect task status aborted"""
        with allure.step("Run action with one job"):
            service = cluster.service(name=SERVICE_NAME)
            component = service.component(name=COMPONENT_NAME)
            expected_component_state = component.state
            action = component.action(display_name="component_cancel_multijob")
            task = action.run()
            last_job = get_or_raise(task.job_list(), display_name_is(THIRD_STEP_TASK))
            wait_for_job_status(job=last_job, timeout=30, period=2)

        _cancel_job(sdk_client_fs, job=last_job)
        wait_all_jobs_are_finished(sdk_client_fs)

        with allure.step("Check jobs info"):
            page.expand_task_in_row(0)
            expected_jobs = [
                {
                    "name": job["name"],
                    "status": JobStatus.SUCCESS if job["name"] != THIRD_STEP_TASK else JobStatus.ABORTED,
                }
                for job in action.subs
            ]
            jobs_info = [asdict(i) for i in page.get_all_jobs_info()]
            assert jobs_info == expected_jobs, f"Actual jobs: {jobs_info} not found in expected jobs {expected_jobs}"

        with allure.step("Check object state"):
            service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_components_page = service_main_page.open_components_tab()
            assert (
                service_components_page.get_component_state_from_row(service_components_page.table.get_all_rows()[0])
                == expected_component_state
            ), f"State of {component.name}  should be {expected_component_state}"

    def test_cancel_one_job_action_cluster(self, app_fs, sdk_client_fs, cluster: Cluster, page: JobListPage):
        """Run action with one job and cancel job. Expect task status aborted"""
        expected_cluster_state = cluster.state
        with allure.step("Run action with one job"):
            action = cluster.action(display_name=ONE_JOB_ACTION)
            task = action.run()
            last_job = get_or_raise(task.job_list(), display_name_is(FIRST_STEP_TASK))
            wait_for_job_status(job=last_job)

        _cancel_job(sdk_client_fs, job=last_job)
        wait_all_jobs_are_finished(sdk_client_fs)

        with allure.step("Check job info"):
            expected_job = {"name": action.name, "status": JobStatus.ABORTED}
            job_info = asdict(page.get_task_info())
            assert expected_job == job_info, f"Expected job: {expected_job} is not equal actual job: {job_info}"

        with allure.step("Check object state"):
            cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
            row = cluster_page.get_row_by_cluster_name(cluster.name)
            assert (
                cluster_page.get_cluster_state_from_row(row) == expected_cluster_state
            ), f"State of {cluster.name}  should be {expected_cluster_state}"

    def test_cancel_one_job_action_service(self, app_fs, sdk_client_fs, cluster: Cluster, page: JobListPage):
        """Run action with one job and cancel job. Expect task status aborted"""
        with allure.step("Run action with one job"):
            service = cluster.service(name=SERVICE_NAME)
            expected_service_state = service.state
            action = service.action(display_name=ONE_JOB_ACTION)
            task = action.run()
            last_job = get_or_raise(task.job_list(), display_name_is(FIRST_STEP_TASK))
            wait_for_job_status(job=last_job)

        _cancel_job(sdk_client_fs, job=last_job)
        wait_all_jobs_are_finished(sdk_client_fs)

        with allure.step("Check job info"):
            expected_job = {"name": action.name, "status": JobStatus.ABORTED}
            page.open()
            job_info = asdict(page.get_task_info())
            assert expected_job == job_info, f"Expected job: {expected_job} is not equal actual job: {job_info}"

        with allure.step("Check object state"):
            cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
            row = cluster_service_page.table.get_all_rows()[0]
            assert (
                cluster_service_page.get_service_state_from_row(row) == expected_service_state
            ), f"State of {service.name} should be {expected_service_state}"

    def test_cancel_one_job_action_component(self, app_fs, sdk_client_fs, cluster: Cluster, page: JobListPage):
        """Run action with one job and cancel job. Expect task status aborted"""
        with allure.step("Run action with one job on component"):
            service = cluster.service(name=SERVICE_NAME)
            component = service.component(name=COMPONENT_NAME)
            expected_component_state = component.state
            action = component.action(display_name="component_cancel")
            task = action.run()
            last_job = get_or_raise(task.job_list(), display_name_is(FIRST_STEP_TASK))
            wait_for_job_status(job=last_job)

        _cancel_job(sdk_client_fs, job=last_job)
        wait_all_jobs_are_finished(sdk_client_fs)

        with allure.step("Check job info"):
            expected_job = {"name": action.name, "status": JobStatus.ABORTED}
            page.open()
            job_info = asdict(page.get_task_info())
            assert expected_job == job_info, f"Expected job: {expected_job} is not equal actual job: {job_info}"

        with allure.step("Check object state"):
            service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
            service_components_page = service_main_page.open_components_tab()
            assert (
                service_components_page.get_component_state_from_row(service_components_page.table.get_all_rows()[0])
                == expected_component_state
            ), f"State of {component.name}  should be {expected_component_state}"

    def test_filtering_and_pagination(self, created_hosts: list[Host], page: JobListPage):
        """Check filtering and pagination"""
        params = {"success": 6, "failed": 5, "second_page": 1}
        _run_actions_on_hosts(created_hosts, params["success"], params["failed"])
        with allure.step("Check status filtering"):
            with page.table.wait_rows_change():
                page.select_filter_failed_tab()
            assert (row_count := page.table.row_count) == params["failed"], (
                f'Tab "Failed" should have {params["failed"]} rows, ' f"but {row_count} rows are presented"
            )
            with page.table.wait_rows_change():
                page.select_filter_success_tab()
            assert (row_count := page.table.row_count) == params["success"], (
                f'Tab "Success" should have {params["success"]}, ' f"but {row_count} rows are presented"
            )
        with allure.step("Check pagination"):
            with page.table.wait_rows_change():
                page.select_filter_all_tab()
            check_pagination(page.table, expected_on_second=params["second_page"])

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_open_task_by_click_on_name(self, cluster: Cluster, page: JobListPage):
        """Click on task name and task page should be opened"""
        with allure.step('Run "Long" action'), page.table.wait_rows_change():
            task = cluster.action(display_name=LONG_ACTION_DISPLAY_NAME).run()
        with allure.step("Click on task name"):
            page.click_on_action_name_in_row(page.table.get_row())
        with allure.step("Check Task detailed page is opened"):
            job_page = JobPageStdout(page.driver, page.base_url, task.id)
            job_page.wait_page_is_opened()
            job_page.check_jobs_toolbar(LONG_ACTION_DISPLAY_NAME.upper())

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.parametrize("log_type", ["stdout", "stderr"], ids=["stdout_menu", "stderr_menu"])
    @pytest.mark.usefixtures("_login_to_adcm_over_api")
    def test_open_log_menu(self, log_type: str, cluster: Cluster, app_fs: ADCMTest):
        """Open stdout/stderr log menu and check info"""
        action = cluster.action(display_name=SUCCESS_ACTION_DISPLAY_NAME)
        task = run_cluster_action_and_assert_result(cluster, action.name)
        job_page = _open_detailed_job_page(task.jobs[0]["id"], app_fs)
        with allure.step(f"Open menu with {log_type} logs and check all info is presented"):
            getattr(job_page, f"open_{log_type}_menu")()
            wait_and_assert_ui_info(
                {
                    "name": SUCCESS_ACTION_DISPLAY_NAME,
                    "invoker_objects": cluster.name,
                    "start_date": is_not_empty,
                    "finish_date": is_not_empty,
                    "execution_time": is_not_empty,
                },
                job_page.get_job_info,
            )
            job_page.check_jobs_toolbar(SUCCESS_ACTION_DISPLAY_NAME.upper())

    @pytest.mark.usefixtures("_login_to_adcm_over_ui", "_clean_downloads_fs")
    def test_download_log(self, cluster: Cluster, app_fs: ADCMTest, downloads_directory):
        """Download log file from detailed page menu"""
        downloaded_file_template = "{job_id}-ansible-{log_type}.txt"
        action = cluster.action(display_name=SUCCESS_ACTION_DISPLAY_NAME)
        task = run_cluster_action_and_assert_result(cluster, action.name)
        job_id = task.jobs[0]["id"]
        job_page = _open_detailed_job_page(job_id, app_fs)
        with allure.step("Download logfiles"):
            job_page.click_on_log_download("stdout")
            wait_file_is_presented(
                downloaded_file_template.format(job_id=job_id, log_type="stdout"),
                app_fs,
                dirname=downloads_directory,
            )
            job_page.click_on_log_download("stderr")
            wait_file_is_presented(
                downloaded_file_template.format(job_id=job_id, log_type="stderr"),
                app_fs,
                dirname=downloads_directory,
            )

    @pytest.mark.usefixtures("_login_to_adcm_over_ui", "_clean_downloads_fs")
    def test_download_bulk_log(self, cluster: Cluster, app_fs: ADCMTest, downloads_directory):
        task = run_cluster_action_and_assert_result(cluster, CHECK_ACTION_NAME)
        jobs_page = JobListPage(driver=app_fs.driver, base_url=app_fs.adcm.url).open()
        with allure.step("Bulk download logfiles"):
            jobs_page.click_on_log_download(row=jobs_page.table.get_row(0))
            wait_file_is_presented(
                app_fs=app_fs,
                filename=f"{build_full_archive_name(cluster, task, CHECK_ACTION_NAME.replace('_', '-'))}.tar.gz",
                dirname=downloads_directory,
            )

    def test_invoker_object_url(self, cluster: Cluster, provider: Provider, page: JobListPage):
        """Check link to object that invoked action is correct"""
        host_fqdn = "run-on-me"
        host_job_link = f"{provider.name}/{host_fqdn}"
        component_link = f"{CLUSTER_NAME}/{SERVICE_NAME}/{COMPONENT_NAME}"
        host_component_link = f"{component_link}/{host_fqdn}"
        with allure.step("Run action on component and check job link to it"):
            service: Service = cluster.service(name=SERVICE_NAME)
            component: Component = service.component(name=COMPONENT_NAME)
            component_action = component.action(display_name=COMPONENT_ACTION_DISPLAY_NAME)
            _check_link_to_invoker_object(component_link, page, component_action)
        with allure.step("Create host, run action on host and check job link to it"):
            host = provider.host_create(host_fqdn)
            host_action = host.action(display_name=FAIL_ACTION_DISPLAY_NAME)
            _check_link_to_invoker_object(host_job_link, page, host_action)
        with allure.step("Add host to the cluster, assign component on it"):
            cluster.host_add(host)
            cluster.hostcomponent_set((host, component))
        with allure.step("Run component host action on host and check job link to it"):
            host_action = _wait_and_get_action_on_host(host, ON_HOST_ACTION_DISPLAY_NAME)
            _check_link_to_invoker_object(host_component_link, page, host_action)


class TestTaskHeaderPopup:
    """Tests for Task page header popup"""

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.parametrize(
        ("job_link", "job_filter"),
        [
            ("click_all_link_in_job_popup", "All"),
            ("click_in_progress_in_job_popup", "In progress"),
            ("click_success_jobs_in_job_popup", "Success"),
            ("click_failed_jobs_in_job_popup", "Failed"),
        ],
        ids=["all_jobs", "in_progress_jobs", "success_jobs", "failed_jobs"],
    )
    @pytest.mark.usefixtures("_login_to_adcm_over_api")
    def test_link_to_jobs_in_header_popup(self, app_fs, job_link, job_filter):
        """Link to /task from popup with filter"""

        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        cluster_page.header.click_job_block()
        open_filter = getattr(cluster_page.header, job_link)
        open_filter()
        job_page = JobListPage(app_fs.driver, app_fs.adcm.url)
        job_page.wait_page_is_opened()
        assert job_page.get_selected_filter() == job_filter, f"Jobs should be filtered by {job_filter}"

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_acknowledge_jobs_in_header_popup(self, cluster: Cluster, page: JobListPage):
        """Run action and click acknowledge in header popup"""
        with allure.step("Run action in cluster"):
            action = cluster.action(display_name=SUCCESS_ACTION_DISPLAY_NAME)
            run_cluster_action_and_assert_result(cluster, action.name, status="success")
        page.header.click_job_block()
        page.header.click_acknowledge_btn_in_job_popup()
        page.header.check_no_jobs_presented()
        assert page.header.get_success_job_amount() == 0, "Success job amount should be 0"
        assert page.header.get_in_progress_job_amount() == 0, "In progress job amount should be 0"
        assert page.header.get_failed_job_amount() == 0, "Failed job amount should be 0"
        assert "background: transparent" in page.header.get_jobs_circle_color(), "Bell circle should be without color"
        page.header.check_acknowledge_btn_not_displayed()

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.parametrize(
        "job_info",
        [
            {
                "status": JobStatus.SUCCESS,
                "action_name": {SUCCESS_ACTION_DISPLAY_NAME: "success"},
                "success_jobs": 1,
                "in_progress_job_jobs": 0,
                "failed_jobs": 0,
                "background": "conic-gradient(rgb(255, 234, 0) 0deg, rgb(255, 234, 0) 0deg, "
                "rgb(30, 229, 100) 0deg, rgb(30, 229, 100) 360deg, "
                "rgb(255, 138, 128) 360deg, rgb(255, 138, 128) 360deg)",
            },
            {
                "status": JobStatus.FAILED,
                "action_name": {FAIL_ACTION_DISPLAY_NAME: "failed"},
                "success_jobs": 0,
                "in_progress_job_jobs": 0,
                "failed_jobs": 1,
                "background": "conic-gradient(rgb(255, 234, 0) 0deg, rgb(255, 234, 0) 0deg, "
                "rgb(30, 229, 100) 0deg, rgb(30, 229, 100) 0deg, "
                "rgb(255, 138, 128) 0deg, rgb(255, 138, 128) 360deg)",
            },
            {
                "status": JobStatus.RUNNING,
                "action_name": {LONG_ACTION_DISPLAY_NAME: ""},
                "success_jobs": 0,
                "in_progress_job_jobs": 1,
                "failed_jobs": 0,
                "background": "conic-gradient(rgb(255, 234, 0) 0deg, rgb(255, 234, 0) 360deg, "
                "rgb(30, 229, 100) 360deg, rgb(30, 229, 100) 360deg, "
                "rgb(255, 138, 128) 360deg, rgb(255, 138, 128) 360deg)",
            },
            {
                "status": JobStatus.RUNNING,
                "action_name": {
                    # Fail action after success will broke UI action run
                    FAIL_ACTION_DISPLAY_NAME: "failed",
                    SUCCESS_ACTION_DISPLAY_NAME: "success",
                    LONG_ACTION_DISPLAY_NAME: "",
                },
                "success_jobs": 1,
                "in_progress_job_jobs": 1,
                "failed_jobs": 1,
                "background": "conic-gradient(rgb(255, 234, 0) 0deg, rgb(255, 234, 0) 120deg, "
                "rgb(30, 229, 100) 120deg, rgb(30, 229, 100) 240deg, "
                "rgb(255, 138, 128) 240deg, rgb(255, 138, 128) 360deg)",
            },
        ],
        ids=["success_job", "failed_job", "in_progress_job", "three_job"],
    )
    @pytest.mark.usefixtures("_login_to_adcm_over_api")
    def test_job_has_correct_info_in_header_popup(self, job_info: dict, cluster: Cluster, app_fs):
        """Run action that finishes (success/failed) and check it in header popup"""

        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        cluster_page.wait_config_loaded()

        for action_name, expected_status in job_info["action_name"].items():
            if action_name == LONG_ACTION_DISPLAY_NAME:
                cluster.action(display_name=action_name).run()
            else:
                run_cluster_action_and_assert_result(
                    cluster,
                    cluster.action(display_name=action_name).name,
                    status=expected_status,
                )
        cluster_page.header.click_job_block()
        assert (
            cluster_page.header.get_success_job_amount() == job_info["success_jobs"]
        ), f"Success job amount should be {job_info['success_jobs']}"
        assert (
            cluster_page.header.get_in_progress_job_amount() == job_info["in_progress_job_jobs"]
        ), f"In progress job amount should be {job_info['in_progress_job_jobs']}"
        assert (
            cluster_page.header.get_failed_job_amount() == job_info["failed_jobs"]
        ), f"Failed job amount should be {job_info['failed_jobs']}"

        def _wait_for_background():
            assert job_info["background"] in (
                circle_color := cluster_page.header.get_jobs_circle_color()
            ), f"Bell circle should be colored, but actual color was: {circle_color}"

        with allure.step('Check that "bell" color is correct'):
            wait_until_step_succeeds(_wait_for_background, period=0.3, timeout=10)

    def test_on_tasks_in_header_popup(self, cluster: Cluster, page: JobListPage, app_fs):
        """Run action and click on it in header popup"""
        actions = {SUCCESS_ACTION_DISPLAY_NAME: "success", FAIL_ACTION_DISPLAY_NAME: "failed"}
        with allure.step("Run actions in cluster"):
            for action_name, status in actions.items():
                action = cluster.action(display_name=action_name)
                run_cluster_action_and_assert_result(cluster, action.name, status=status)
        page.header.click_job_block()
        for action_name, _ in actions.items():
            page.header.click_on_task_row_by_name(task_name=action_name)
            job_page = JobPageStdout(app_fs.driver, app_fs.adcm.url, job_id=1)
            job_page.check_title(action_name)
            job_page.check_text(success_task=action_name == SUCCESS_ACTION_DISPLAY_NAME)

    @pytest.mark.usefixtures("_login_to_adcm_over_api")
    def test_six_tasks_in_header_popup(self, cluster: Cluster, app_fs):
        """Check list of tasks in header popup"""
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        with allure.step("Run actions in cluster"):
            for _ in range(6):
                run_cluster_action_and_assert_result(
                    cluster,
                    cluster.action(display_name=SUCCESS_ACTION_DISPLAY_NAME).name,
                    status="success",
                )
        cluster_page.header.click_job_block()
        with allure.step("Check that in popup 5 tasks"):
            assert len(cluster_page.header.get_job_rows_from_popup()) == 5, "Popup should contain 5 tasks"
        cluster_page.header.click_all_link_in_job_popup()

        job_page = JobListPage(app_fs.driver, app_fs.adcm.url)
        job_page.wait_page_is_opened()
        with allure.step("Check that in job list page 6 tasks"):
            assert job_page.table.row_count == 6, "Job list page should contain 6 tasks"

    @pytest.mark.usefixtures("_login_to_adcm_over_api", "cluster")
    def test_acknowledge_running_job_in_header_popup(self, app_fs):
        """Run action and click acknowledge in header popup while it runs"""
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        with allure.step("Run action in cluster"):
            row = cluster_page.table.get_all_rows()[0]
            cluster_page.run_action_in_cluster_row(row, LONG_ACTION_DISPLAY_NAME)
        cluster_page.header.click_job_block()
        cluster_page.header.click_acknowledge_btn_in_job_popup()

        cluster_page.header.wait_success_job_amount(1)
        assert cluster_page.header.get_in_progress_job_amount() == 0, "In progress job amount should be 0"
        assert cluster_page.header.get_failed_job_amount() == 0, "Failed job amount should be 0"

    @pytest.mark.skip(reason="Test is only for https://arenadata.atlassian.net/browse/ADCM-2660")
    @pytest.mark.usefixtures("cluster_bundle")
    def test_lots_of_tasks_on_jobs_page(self, app_fs, adcm_credentials, provider):
        """Check query execution time and amount of jobs when the page starts to lag."""

        page_timeout = 30
        with allure.step("Create objects and run actions"):
            _ = [provider.host_create(f"host-{i}").action(name=SUCCESS_ACTION_NAME).run() for i in range(5000)]
        login = LoginPage(app_fs.driver, app_fs.adcm.url).open()
        login.login_user(**adcm_credentials)
        with catch_failed(TimeoutError, f"Page did not load for {page_timeout} seconds"):
            job_page = JobListPage(app_fs.driver, app_fs.adcm.url).open()
            job_page.wait_page_is_opened(timeout=page_timeout)


# !==== HELPERS =====!


def _test_run_action(page: JobListPage, action_owner: Cluster | Service | Provider | Host, expected_link: str):
    """
    Run the "Long" action
    Check popup info
    Check table info without filter (All)
    Activate filter "Running"
    Check table info
    """
    expected_info = {
        "status": JobStatus.RUNNING,
        "action_name": LONG_ACTION_DISPLAY_NAME,
        "invoker_objects": expected_link,
    }
    with allure.step(
        f'Run action "{LONG_ACTION_DISPLAY_NAME}" on {action_owner.__class__}',
    ), page.table.wait_rows_change():
        long_action = action_owner.action(display_name=LONG_ACTION_DISPLAY_NAME)
        long_action.run()
    _check_job_info_in_popup(page, {"status": expected_info["status"], "action_name": expected_info["action_name"]})
    _check_running_job_info_in_table(page, expected_info)
    page.select_filter_running_tab()
    _check_running_job_info_in_table(page, expected_info)


@allure.step("Check running job information in table")
def _check_running_job_info_in_table(page: JobListPage, expected_info: dict):
    """Get info about job from table and check it"""
    wait_and_assert_ui_info(
        {**expected_info, "start_date": is_not_empty, "finish_date": is_empty},
        page.get_task_info_from_table,
        get_info_kwargs={"full_invoker_objects_link": True},
    )


@allure.step("Check finished job information in table")
def _check_finished_job_info_in_table(page: JobListPage, expected_info: dict):
    """Get and check info about successfully finished job from table"""
    wait_and_assert_ui_info(
        {**expected_info, "start_date": is_not_empty, "finish_date": is_not_empty},
        page.get_task_info_from_table,
    )


@allure.step("Check job information in popup")
def _check_job_info_in_popup(page: JobListPage, expected_info: dict):
    """Get job info from popup and check it"""
    with page.header.open_jobs_popup():
        wait_and_assert_ui_info({**expected_info}, page.get_task_info_from_popup)


@allure.step("Run {success} success and {failed} failed actions on hosts")
def _run_actions_on_hosts(hosts: list[Host], success: int, failed: int):
    """
    Run success and failed actions
    and then wait for all of them to be finished
    """
    actions_distribution = [SUCCESS_ACTION_DISPLAY_NAME] * success + [FAIL_ACTION_DISPLAY_NAME] * failed
    task_list = [host.action(display_name=actions_distribution[i]).run() for i, host in enumerate(hosts)]
    for task in task_list:
        task.wait(timeout=60)


@allure.step("Open detailed job page")
def _open_detailed_job_page(job_id: int, app_fs: ADCMTest) -> JobPageStdout:
    """Open detailed job page (stdout page)"""
    return JobPageStdout(app_fs.driver, app_fs.adcm.url, job_id).open()


def _check_link_to_invoker_object(expected_link: str, page: JobListPage, action: Action):
    """
    Check that link to object invoked action is correct
    :param expected_link: "Link" to invoker objects
    :param page: Page with jobs table
    :param action: Action to run
    """
    expected_value = {"invoker_objects": expected_link}
    with page.table.wait_rows_change():
        action.run()
    wait_and_assert_ui_info(
        expected_value,
        page.get_task_info_from_table,
        get_info_kwargs={"full_invoker_objects_link": True},
    )
    detail_page = JobPageStdout(page.driver, page.base_url, action.task_list()[0].id).open()
    wait_and_assert_ui_info(expected_value, detail_page.get_job_info)
    page.open()


def _wait_and_get_action_on_host(host: Host, display_name: str) -> Action:
    """Wait until action is presented on host (wait for host action)"""

    def _wait_for_action_to_be_presented():
        try:
            host.action(display_name=display_name)
        except ObjectNotFound:
            assert (  # noqa: PT015
                False
            ), f'Action "{display_name}" is not presented on host {host.fqdn}. Actions: {host.action_list()}'

    wait_until_step_succeeds(_wait_for_action_to_be_presented, period=0.1, timeout=10)
    return host.action(display_name=display_name)


@allure.step("Cancel job in task")
def _cancel_job(sdk_client_fs: ADCMClient, job: Job) -> None:
    # Change when can be able to abort job from web
    url = f"{sdk_client_fs.url}/api/v1/job/{job.id}/cancel/"
    check_succeed(requests.put(url, headers=make_auth_header(sdk_client_fs)))
