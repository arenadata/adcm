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

"""Tests on known bugs that can't be categorised by any other attribute"""

from typing import Type

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Component, Provider, Service, Task
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_provider_action_and_assert_result,
)
from adcm_pytest_plugin.utils import get_data_dir, wait_until_step_succeeds
from coreapi.exceptions import ErrorMessage
from tests.conftest import TEST_USER_CREDENTIALS
from tests.functional.tools import AnyADCMObject, get_object_represent
from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.cluster.page import ClusterMainPage
from tests.ui_tests.app.page.common.base_page import BaseDetailedPage
from tests.ui_tests.app.page.component.page import ComponentMainPage
from tests.ui_tests.app.page.host.page import HostMainPage
from tests.ui_tests.app.page.job_list.page import JobListPage, JobStatus
from tests.ui_tests.app.page.provider.page import ProviderMainPage
from tests.ui_tests.app.page.service.page import ServiceMainPage
from tests.ui_tests.conftest import login_over_api

pytestmark = [pytest.mark.regression()]


class TestMainInfo:
    """Tests on __main_info effects on UI"""

    _DESCRIPTION_BEFORE = "Paragraph One\nOf chapter III"
    _DESCRIPTION_AFTER = "Paragraph I\nOf chapter Three"

    @pytest.fixture()
    def cluster(self, sdk_client_fs) -> Cluster:
        """Get cluster with added service"""
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'main_info', 'cluster'))
        cluster = bundle.cluster_create('Test Cluster')
        cluster.service_add(name='change_main_info')
        return cluster

    @pytest.fixture()
    def provider(self, sdk_client_fs) -> Provider:
        """Get provider with at least one created host"""
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'main_info', 'provider'))
        provider = bundle.provider_create('Test Provider')
        provider.host_create('very-cool-name')
        return provider

    @pytest.fixture()
    def _login_as_custom_user(self, app_fs, user_sdk):  # pylint: disable=unused-argument
        """Login as test user"""
        username, password = TEST_USER_CREDENTIALS
        login_over_api(app_fs, {'username': username, 'password': password})

    @pytest.fixture()
    def _view_import_on_cluster(self, sdk_client_fs, cluster, user):
        """Grant permission to view import on cluster to new user"""
        role = sdk_client_fs.role_create(
            name='Wrapper role', display_name='Wrapper', child=[{'id': sdk_client_fs.role(name='View imports').id}]
        )
        sdk_client_fs.policy_create(name='Policy for cluster', role=role, objects=[cluster], user=[user])

    @allure.issue(url='https://arenadata.atlassian.net/browse/ADCM-2563')
    @pytest.mark.usefixtures('_login_as_custom_user', '_view_import_on_cluster')
    def test_access_to_detailed_page(self, app_fs, cluster):
        """
        Test that user has access to detailed object page when there's __main_info in config,
        but user isn't allowed to view config
        """
        expected_main_info = 'Paragraph One\nOf chapter III'
        cluster_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, cluster_id=cluster.id).open()
        cluster_page.check_all_elements()
        assert (
            description := cluster_page.get_description()
        ) == expected_main_info, (
            f'Description on cluster main page is expected to be {expected_main_info}, not {description}'
        )

    @allure.issue(url='https://arenadata.atlassian.net/browse/ADCM-2676')
    @pytest.mark.usefixtures('_login_to_adcm_over_api')
    def test_main_info_update(self, app_fs, cluster, provider):
        """Test that update of __main_info config field is displayed correctly on object detailed page"""
        change_main_info_action = 'change_main_info'
        service = cluster.service(name='change_main_info')
        component = service.component()
        host = provider.host()

        pages = (ClusterMainPage, ServiceMainPage, ComponentMainPage, ProviderMainPage, HostMainPage)
        adcm_objects = (cluster, service, component, provider, host)

        with allure.step(
            'Check initial __main_info is correctly displayed in the description of detailed object pages'
        ):
            for page_type, adcm_object in zip(pages, adcm_objects):
                self._check_detailed_page_main_info(app_fs, page_type, adcm_object, self._DESCRIPTION_BEFORE)

        with allure.step('Change __main_info and check detailed object pages again'):
            run_cluster_action_and_assert_result(cluster, change_main_info_action)
            run_provider_action_and_assert_result(provider, change_main_info_action, config={'host_id': host.id})
            for page_type, adcm_object in zip(pages, adcm_objects):
                self._check_detailed_page_main_info(app_fs, page_type, adcm_object, self._DESCRIPTION_AFTER)

        with allure.step('Save config via UI and check that description is the same'):
            for page_type, adcm_object in zip(pages, adcm_objects):
                self._check_main_info_after_config_save(app_fs, page_type, adcm_object)

    def _check_detailed_page_main_info(
        self, app: ADCMTest, page_type: Type[BaseDetailedPage], adcm_object: AnyADCMObject, expected_text: str
    ):
        """Check that detailed page contains the expected text from __main_info in description"""
        object_represent = get_object_represent(adcm_object)
        with allure.step(f'Check description on detailed page of {object_represent}'):
            page = self._init_page(app, page_type, adcm_object)
            page.open()
            actual_text = page.get_description()
            assert actual_text == expected_text, (
                f'Description on detailed page of {object_represent} '
                f'should be "{expected_text}", but "{actual_text}" was found'
            )

    def _check_main_info_after_config_save(
        self, app: ADCMTest, page_type: Type[BaseDetailedPage], adcm_object: AnyADCMObject
    ):
        """
        Check that detailed page contains the expected text from __main_info in description
        after the config was saved via UI
        """
        object_represent = get_object_represent(adcm_object)
        with allure.step(f"Change config of {object_represent} and check that __main_info didn't change"):
            page = self._init_page(app, page_type, adcm_object)
            page.open()
            text_before = page.get_description()
            config_page = page.open_config_tab()
            config_page.config.set_description('New Awesome Description')
            config_page.config.type_in_field_with_few_inputs(row="just_line", values=[" "])
            config_page.config.save_config()
            page.open()
            text_after = page.get_description()
            assert text_after == text_before, (
                f'Description on detailed page of {object_represent} '
                f'should be "{text_before}", but "{text_after}" was found'
            )

    def _init_page(self, app: ADCMTest, page_type, adcm_object):
        if isinstance(adcm_object, Service):
            ids = (adcm_object.cluster_id, adcm_object.id)
        elif isinstance(adcm_object, Component):
            ids = (adcm_object.cluster_id, adcm_object.service_id, adcm_object.id)
        else:
            ids = (adcm_object.id,)
        return page_type(app.driver, app.adcm.url, *ids)


class TestAllowToTerminate:
    """
    Test cases related to task termination
    """

    CLUSTER_NAME = 'Terminator'
    client: ADCMClient

    pytestmark = [
        pytest.mark.parametrize('generic_bundle', ['action_termination_allowed'], indirect=True),
        pytest.mark.usefixtures('_login_to_adcm_over_api', '_bind_client', 'cluster'),
    ]

    @pytest.fixture()
    def _bind_client(self, sdk_client_fs):
        self.client = sdk_client_fs

    @pytest.fixture()
    def cluster(self, generic_bundle) -> Cluster:
        """Create a cluster from the generic bundle with allow_to_terminate actions"""
        return generic_bundle.cluster_create(self.CLUSTER_NAME)

    @pytest.fixture()
    def page(self, app_fs) -> JobListPage:
        """Get page with list of jobs"""
        return JobListPage(app_fs.driver, app_fs.adcm.url).open()

    @pytest.mark.parametrize('action_name', ['simple', 'multi'])
    def test_cancel_job(self, action_name: str, page: JobListPage):
        """Test cancelling task (job and multijob)"""
        task = self._run_cluster_action(action_name)
        with allure.step('Check that job is running'):
            wait_until_step_succeeds(self._check_job_status, timeout=5, period=1, page=page, status=JobStatus.RUNNING)
        with allure.step('Cancel task and check it is cancelled without page refresh'):
            self._cancel_task(task)
            wait_until_step_succeeds(self._check_job_status, timeout=5, period=1, page=page, status=JobStatus.ABORTED)

    def _run_cluster_action(self, name: str) -> Task:
        with allure.step(f'Run action "{name}" on cluster'):
            return self.client.cluster(name=self.CLUSTER_NAME).action(name=name).run()

    def _cancel_task(self, task: Task):
        def _cancel():
            try:
                task.cancel()
            except ErrorMessage as e:
                raise AssertionError('Failed to cancel task') from e

        wait_until_step_succeeds(_cancel, timeout=5, period=0.5)

    def _check_job_status(self, page: JobListPage, status: JobStatus, row_id: int = 0):
        row_info = page.get_task_info_from_table(row_id)
        assert row_info.status == status, f'Job should be {status.value}'
