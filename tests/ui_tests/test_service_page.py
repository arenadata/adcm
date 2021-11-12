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

"""UI tests for /service page"""
import os

import allure
import pytest
from _pytest.fixtures import SubRequest
from adcm_client.objects import (
    ADCMClient,
    Bundle,
    Provider,
)
from adcm_pytest_plugin import params
from adcm_pytest_plugin import utils

from tests.library.status import ADCMObjectStatusChanger
from tests.ui_tests.app.page.admin.page import AdminIntroPage
from tests.ui_tests.app.page.cluster.page import (
    ClusterServicesPage,
)
from tests.ui_tests.app.page.common.import_page.page import (
    ImportItemInfo,
    SUCCESS_COLOR,
    NEGATIVE_COLOR,
)
from tests.ui_tests.app.page.common.status.page import StatusRowInfo
from tests.ui_tests.app.page.service.page import (
    ServiceComponentPage,
    ServiceStatusPage,
)
from tests.ui_tests.app.page.service.page import (
    ServiceMainPage,
    ServiceConfigPage,
    ServiceImportPage,
)

BUNDLE_COMMUNITY = "cluster_community"
CLUSTER_NAME = "Test cluster"
SERVICE_NAME = "test_service"
PROVIDER_NAME = 'test_provider'
HOST_NAME = 'test-host'
PROVIDER_WITH_ISSUE_NAME = 'provider_with_issue'
COMPONENT_NAME = "first"
BUNDLE_REQUIRED_FIELDS = "cluster_and_service_with_required_string"
BUNDLE_IMPORT = "cluster_to_import"

# pylint: disable=redefined-outer-name,no-self-use,unused-argument
pytestmark = pytest.mark.usefixtures("login_to_adcm_over_api")


@pytest.fixture()
def create_community_cluster(sdk_client_fs: ADCMClient):
    """Create community edition cluster"""
    bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
    return bundle.cluster_create(name=CLUSTER_NAME)


@pytest.fixture()
def create_community_cluster_with_service(sdk_client_fs: ADCMClient):
    """Create community edition cluster and add service"""
    bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
    cluster = bundle.cluster_create(name=CLUSTER_NAME)
    return cluster, cluster.service_add(name=SERVICE_NAME)


@allure.step("Upload cluster bundle")
def cluster_bundle(sdk_client_fs: ADCMClient, data_dir_name: str) -> Bundle:
    """Upload cluster bundle"""
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), data_dir_name))


@pytest.fixture(params=["provider"])
@allure.title("Upload provider bundle")
def provider_bundle(request: SubRequest, sdk_client_fs: ADCMClient) -> Bundle:
    """Upload provider bundle"""
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), request.param))


@pytest.fixture()
@allure.title("Create provider")
def upload_and_create_provider(provider_bundle) -> Provider:
    """Create provider from uploaded bundle"""
    return provider_bundle.provider_create(PROVIDER_NAME)


@pytest.fixture()
@allure.title("Create community cluster and add host")
def create_community_cluster_with_host(app_fs, sdk_client_fs: ADCMClient, upload_and_create_provider, create_host):
    """Create community cluster and add host"""
    bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
    cluster = bundle.cluster_create(name=CLUSTER_NAME)
    host = cluster.host_add(create_host)
    return cluster, host


@pytest.fixture()
@allure.title("Create community cluster with service and add host")
def create_community_cluster_with_host_and_service(sdk_client_fs: ADCMClient, create_host):
    """Create community cluster with service and add host"""
    bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
    cluster = bundle.cluster_create(name=CLUSTER_NAME)
    return cluster, cluster.service_add(name=SERVICE_NAME), cluster.host_add(create_host)


@pytest.fixture()
@allure.title("Create host")
def create_host(upload_and_create_provider):
    """Create default host using API"""
    provider = upload_and_create_provider
    return provider.host_create(HOST_NAME)


@pytest.fixture()
def create_import_cluster_with_service(sdk_client_fs: ADCMClient):
    """Create clusters and services for further import"""
    params = {
        "import_cluster_name": "Import cluster",
        "import_service_name": "Pre-uploaded Dummy service to import",
    }
    with allure.step("Create main cluster"):
        bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
        cluster_main = bundle.cluster_create(name=CLUSTER_NAME)
        service_main = cluster_main.service_add(name=SERVICE_NAME)
    with allure.step("Create cluster to import"):
        bundle = cluster_bundle(sdk_client_fs, BUNDLE_IMPORT)
        cluster_import = bundle.cluster_create(name=params["import_cluster_name"])
        service_import = cluster_import.service_add(name=params["import_service_name"])
        return cluster_main, service_main, cluster_import, service_import


class TestServiceMainPage:
    """Tests for the /cluster/{}/service/{}/main page"""

    @pytest.mark.smoke()
    def test_open_service_main_page_by_tab(self, app_fs, create_community_cluster_with_service):
        """Test open /cluster/{}/service/{}/main page from left menu"""

        cluster, service = create_community_cluster_with_service
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_main_page = service_config_page.open_main_tab()
        service_main_page.wait_page_is_opened()
        service_main_page.check_all_elements()

    def test_open_admin_page_by_toolbar_in_service(self, app_fs, create_community_cluster_with_service):
        """Test open admin/intro page from service toolbar"""

        cluster, service = create_community_cluster_with_service
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_main_page.toolbar.click_admin_link()
        AdminIntroPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()

    def test_open_service_main_page_by_toolbar(self, app_fs, create_community_cluster_with_service):
        """Test open /cluster/{}/service/{}/main page from service toolbar"""

        params = {"service_list_name": "SERVICES"}

        cluster, service = create_community_cluster_with_service
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_main_page.toolbar.click_link_by_name(params["service_list_name"])
        ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id).wait_page_is_opened()

    def test_run_action_on_service_page_by_toolbar(self, app_fs, create_community_cluster_with_service):
        """Test run action from the /cluster/{}/service/{}/main page toolbar"""

        params = {"action_name": "test_action"}

        cluster, service = create_community_cluster_with_service
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_main_page.toolbar.run_action(CLUSTER_NAME, params["action_name"])
        with allure.step("Check success job"):
            assert (
                service_main_page.header.get_in_progress_job_amount_from_header() == "1"
            ), "There should be 1 in progress job in header"


class TestServiceComponentPage:
    """Tests for the /cluster/{}/service/{}/component page"""

    @pytest.mark.smoke()
    def test_open_service_component_page_by_tab(self, app_fs, create_community_cluster_with_service):
        """Test open /cluster/{}/service/{}/component page from left menu"""

        cluster, service = create_community_cluster_with_service
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_component_page = service_main_page.open_components_tab()
        service_component_page.wait_page_is_opened()
        service_component_page.check_all_elements()

    @params.including_https
    @pytest.mark.smoke()
    def test_run_action_from_service_component_page(self, app_fs, create_community_cluster_with_service):
        """Test run action from the row on /cluster/{}/service/{}/component page"""

        params = {"action_name": "switch_component_state", "expected_state": "installed"}

        cluster, service = create_community_cluster_with_service
        service_component_page = ServiceComponentPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        row = service_component_page.table.get_all_rows()[0]
        with service_component_page.wait_component_state_change(row):
            service_component_page.run_action_in_component_row(row, params["action_name"])
        with allure.step("Check service state has changed"):
            assert (
                service_component_page.get_component_state_from_row(row) == params["expected_state"]
            ), f"Cluster state should be {params['expected_state']}"
        with allure.step("Check success service job"):
            assert (
                service_component_page.header.get_success_job_amount_from_header() == "1"
            ), "There should be 1 success service job in header"


class TestServiceConfigPage:
    """Tests for the /cluster/{}/service/{}/config page"""

    def test_open_service_config_page_by_tab(self, app_fs, create_community_cluster_with_service):
        """Test open /cluster/{}/service/{}/config from left menu"""

        cluster, service = create_community_cluster_with_service
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_config_page = service_main_page.open_config_tab()
        service_config_page.wait_page_is_opened()
        service_config_page.check_all_elements()

    def test_filter_config_on_service_config_page(self, app_fs, create_community_cluster_with_service):
        """Test config filtration on /cluster/{}/service/{}/config page"""

        params = {"search_param": "param1", "group_name": "core-site"}

        cluster, service = create_community_cluster_with_service
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        with service_config_page.config.wait_rows_change():
            service_config_page.config.search(params["search_param"])
        with allure.step(f"Check that rows are filtered by {params['search_param']}"):
            config_rows = service_config_page.config.get_all_config_rows()
            assert len(config_rows) == 1, "Rows are not filtered: there should be 1 row"
            assert (
                service_config_page.config.get_config_row_info(config_rows[0]).name == f"{params['search_param']}:"
            ), f"Name should be {params['search_param']}"
        with service_config_page.config.wait_rows_change():
            service_config_page.config.clear_search_input()
        with allure.step("Check that rows are not filtered"):
            config_rows = service_config_page.config.get_all_config_rows()
            assert len(config_rows) == 2, "Rows are filtered: there should be 4 row"
        with service_config_page.config.wait_rows_change(expected_rows_amount=0):
            service_config_page.config.click_on_group(params["group_name"])

    def test_save_custom_config_on_service_config_page(self, app_fs, create_community_cluster_with_service):
        """Test config save on /cluster/{}/service/{}/config page"""

        params = {
            "row_value_new": "test",
            "row_value_old": "null",
            "config_name_new": "test_name",
            "config_name_old": "init",
        }

        cluster, service = create_community_cluster_with_service
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        config_row = service_config_page.config.get_all_config_rows()[0]
        service_config_page.config.type_in_config_field(row=config_row, value=params["row_value_new"], clear=True)

        service_config_page.config.set_description(params["config_name_new"])
        service_config_page.config.save_config()
        service_config_page.config.compare_versions(params["config_name_old"])
        with allure.step("Check row history"):
            row_with_history = service_config_page.config.get_all_config_rows()[0]
            service_config_page.config.wait_history_row_with_value(row_with_history, params["row_value_old"])

    def test_reset_config_in_row_on_service_config_page(self, app_fs, create_community_cluster_with_service):
        """Test config reset on /cluster/{}/service/{}/config page"""

        params = {"row_name": "param1", "row_value_new": "test", "row_value_old": "", "config_name": "test_name"}

        cluster, service = create_community_cluster_with_service
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        config_row = service_config_page.config.get_all_config_rows()[0]
        service_config_page.config.type_in_config_field(row=config_row, value=params["row_value_new"], clear=True)
        service_config_page.config.set_description(params["config_name"])
        service_config_page.config.save_config()

        config_row = service_config_page.config.get_all_config_rows()[0]
        service_config_page.config.reset_to_default(row=config_row)
        service_config_page.config.assert_input_value_is(
            expected_value=params["row_value_old"], display_name=params["row_name"]
        )

    def test_field_validation_on_service_config_page(self, app_fs, sdk_client_fs):
        """Test config fields validation on /cluster/{}/service/{}/config page"""

        params = {
            'pass_name': 'Important password',
            'req_name': 'Required item',
            'not_req_name': 'Just item',
            'wrong_value': 'test',
        }

        with allure.step("Create cluster and service"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_REQUIRED_FIELDS)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            service = cluster.service_add(name=SERVICE_NAME)
        service_config_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_config_page.config.check_password_confirm_required(params['pass_name'])
        service_config_page.config.check_field_is_required(params['req_name'])
        config_row = service_config_page.config.get_all_config_rows()[0]
        service_config_page.config.type_in_config_field(params['wrong_value'], row=config_row)
        service_config_page.config.check_field_is_invalid(params['not_req_name'])


class TestServiceStatusPage:
    """Tests for the /cluster/{}/service/{}/status page"""

    def test_open_by_tab_service_status_page(self, app_fs, create_community_cluster_with_service):
        """Test open /cluster/{}/service/{}/status from left menu"""

        cluster, service = create_community_cluster_with_service
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_status_page = service_main_page.open_status_tab()
        service_status_page.wait_page_is_opened()
        service_status_page.check_all_elements()

    def test_status_on_service_status_page(
        self, app_fs, adcm_fs, sdk_client_fs, create_community_cluster_with_host_and_service
    ):
        """Changes status on /cluster/{}/service/{}/status page"""

        successful = 'successful 1/1'
        negative = 'successful 0/1'
        success_status = [
            StatusRowInfo(
                icon=True, group_name='test_service', state=successful, state_color=SUCCESS_COLOR, link=None
            ),
            StatusRowInfo(icon=True, group_name='first', state=successful, state_color=SUCCESS_COLOR, link=None),
            StatusRowInfo(icon=True, group_name=None, state=None, state_color=None, link='test-host'),
        ]
        component_negative_status = [
            StatusRowInfo(
                icon=True, group_name='test_service', state=negative, state_color=NEGATIVE_COLOR, link=None
            ),
            StatusRowInfo(icon=True, group_name='first', state=negative, state_color=NEGATIVE_COLOR, link=None),
            StatusRowInfo(icon=True, group_name=None, state=None, state_color=None, link='test-host'),
        ]
        cluster, service, host = create_community_cluster_with_host_and_service
        cluster_component = cluster.service(name=SERVICE_NAME).component(name=COMPONENT_NAME)
        cluster.hostcomponent_set((host, cluster_component))

        service_status_page = ServiceStatusPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        status_changer = ADCMObjectStatusChanger(sdk_client_fs, adcm_fs)
        with allure.step("Check positive status"):
            status_changer.enable_cluster(cluster)
            service_status_page.driver.refresh()
            service_status_page.compare_current_and_expected_state(success_status)
        with allure.step("Check negative status on service"):
            status_changer.set_component_negative_status((host, cluster_component))
            service_status_page.driver.refresh()
            service_status_page.compare_current_and_expected_state(component_negative_status)
        with allure.step("Check collapse button"):
            with service_status_page.wait_rows_collapsed():
                service_status_page.click_collapse_all_btn()
            assert len(service_status_page.get_all_rows()) == 1, "Status rows should have been collapsed"


class TestServiceImportPage:
    """Tests for the /cluster/{}/service/{}/import page"""

    def test_open_by_tab_service_import_page(self, app_fs, create_community_cluster_with_service):
        """Test open /cluster/{}/service/{}/import from left menu"""

        cluster, service = create_community_cluster_with_service
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        service_import_page = service_main_page.open_import_tab()
        service_import_page.wait_page_is_opened()
        service_import_page.check_all_elements()

    def test_import_from_service_import_page(self, app_fs, create_import_cluster_with_service):
        """Test service import on /cluster/{}/service/{}/import page"""

        params = {"message": "Successfully saved"}

        cluster, service, _, _ = create_import_cluster_with_service
        service_import_page = ServiceImportPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id).open()
        import_item = service_import_page.get_import_items()[0]
        with allure.step("Check import on import page"):
            assert service_import_page.get_import_item_info(import_item) == ImportItemInfo(
                'Pre-uploaded Dummy service to import', 'Pre-uploaded Dummy service to import 2.5'
            ), "Text in import item changed"
        service_import_page.close_info_popup()
        service_import_page.click_checkbox_in_import_item(import_item)
        service_import_page.click_save_btn()
        with allure.step("Check that import is saved"):
            assert service_import_page.get_info_popup_text() == params["message"], "No message about success"
            assert service_import_page.is_chxb_in_item_checked(
                import_item
            ), "Checkbox with import should have been checked"
