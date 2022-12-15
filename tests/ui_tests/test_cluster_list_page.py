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

"""UI tests for /cluster page"""

import allure
import pytest
from _pytest.fixtures import SubRequest
from adcm_client.objects import ADCMClient, Bundle, Cluster, Host, Provider
from adcm_pytest_plugin.params import including_https
from adcm_pytest_plugin.utils import get_data_dir, parametrize_by_data_subdirs
from selenium.common.exceptions import TimeoutException
from tests.library.status import ADCMObjectStatusChanger
from tests.ui_tests.app.page.admin.page import AdminIntroPage
from tests.ui_tests.app.page.cluster.page import (
    ClusterComponentsPage,
    ClusterConfigPage,
    ClusterGroupConfigConfig,
    ClusterGroupConfigHosts,
    ClusterGroupConfigPage,
    ClusterHostPage,
    ClusterImportPage,
    ClusterMainPage,
    ClusterServicesPage,
    ClusterStatusPage,
)
from tests.ui_tests.app.page.cluster_list.page import ClusterListPage
from tests.ui_tests.app.page.common.configuration.page import CONFIG_ITEMS
from tests.ui_tests.app.page.common.group_config_list.page import GroupConfigRowInfo
from tests.ui_tests.app.page.common.host_components.page import ComponentsHostRowInfo
from tests.ui_tests.app.page.common.import_page.page import ImportItemInfo
from tests.ui_tests.app.page.common.status.page import (
    NEGATIVE_COLOR,
    SUCCESS_COLOR,
    StatusRowInfo,
)
from tests.ui_tests.app.page.host.page import HostConfigPage, HostMainPage
from tests.ui_tests.app.page.service.page import (
    ServiceConfigPage,
    ServiceImportPage,
    ServiceMainPage,
)
from tests.ui_tests.core.checks import check_pagination
from tests.ui_tests.generator_helper import generate_configs, prepare_config
from tests.ui_tests.utils import (
    check_host_value,
    create_few_groups,
    prepare_cluster_and_open_config_page,
    wait_and_assert_ui_info,
    wrap_in_dict,
)

RANGE_VALUES = [
    ("float", 0.15),
    ("float", 0),
    ("float", -1.2),
    ("integer", 4),
    ("integer", 0),
    ("integer", -3),
]

BUNDLE_COMMUNITY = "cluster_community"
BUNDLE_ENTERPRISE = "cluster_enterprise"
BUNDLE_IMPORT = "cluster_to_import"
BUNDLE_UPGRADE = "upgradable_cluster"
BUNDLE_UPGRADE_V2 = "upgradable_cluster_v2"
BUNDLE_REQUIRED_FIELDS = "cluster_and_service_with_required_string"
BUNDLE_DEFAULT_FIELDS = "cluster_and_service_with_default_string"
BUNDLE_WITH_SERVICES = "cluster_with_services"
CLUSTER_NAME = "Test cluster"
SERVICE_NAME = "test_service"
PROVIDER_NAME = 'test_provider'
HOST_NAME = 'test-host'
PROVIDER_WITH_ISSUE_NAME = 'provider_with_issue'
COMPONENT_NAME = "first"
BUNDLE_WITH_REQUIRED_FIELDS = "cluster_required_fields"
BUNDLE_WITH_DESCRIPTION_FIELDS = "cluster_with_all_config_params"
BUNDLE_WITH_REQUIRED_IMPORT = "cluster_required_import"
BUNDLE_WITH_REQUIRED_COMPONENT = "cluster_required_hostcomponent"
DISCLAIMER_TEXT = "Are you really want to click me?"


# pylint: disable=redefined-outer-name,too-many-lines,too-many-public-methods
# pylint: disable=too-many-boolean-expressions
# pylint: disable=too-many-branches,too-many-nested-blocks,too-many-locals

pytestmark = pytest.mark.usefixtures("_login_to_adcm_over_api")


# !===== Fixtures =====!


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


@allure.step("Upload cluster bundle")
def cluster_bundle(sdk_client_fs: ADCMClient, data_dir_name: str) -> Bundle:
    """Upload cluster bundle"""
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, data_dir_name))


@pytest.fixture(params=["provider"])
@allure.title("Upload provider bundle")
def provider_bundle(request: SubRequest, sdk_client_fs: ADCMClient) -> Bundle:
    """Upload provider bundle"""
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, request.param))


@pytest.fixture()
@allure.title("Create provider")
def upload_and_create_provider(provider_bundle) -> Provider:
    """Create provider from uploaded bundle"""
    return provider_bundle.provider_create(PROVIDER_NAME)


@pytest.fixture()
@allure.title("Create a cluster with all type of fields in config")
def create_cluster_with_all_config_fields(sdk_client_fs: ADCMClient) -> Cluster:
    """Create community cluster and add host"""
    bundle = cluster_bundle(sdk_client_fs, BUNDLE_WITH_DESCRIPTION_FIELDS)
    return bundle.cluster_create(name=CLUSTER_NAME)


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
def create_community_cluster_with_host_and_service(sdk_client_fs: ADCMClient, create_host) -> [Cluster, Host]:
    """Create community cluster with service and add host"""
    bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
    cluster = bundle.cluster_create(name=CLUSTER_NAME)
    cluster.service_add(name=SERVICE_NAME)
    cluster.host_add(create_host)
    return cluster, create_host


@pytest.fixture()
@allure.title("Create host")
def create_host(upload_and_create_provider):
    """Create default host using API"""
    provider = upload_and_create_provider
    return provider.host_create(HOST_NAME)


@allure.title("Check all values in host info")
def check_components_host_info(host_info: ComponentsHostRowInfo, name: str, components: str):
    """Check all values in host info"""
    check_host_value('name', host_info.name, name)
    check_host_value('components', host_info.components, components)


# !===== Funcs =====!


@allure.step("Check that cluster has been upgraded")
def check_cluster_upgraded(app_fs, upgrade_cluster_name: str, state: str):
    """Open cluster list page and check that cluster has been upgraded"""

    cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
    row = cluster_page.get_row_by_cluster_name(upgrade_cluster_name)
    assert cluster_page.get_cluster_state_from_row(row) == state, f"Cluster state should be {state}"


# !===== Tests =====!


class TestClusterListPage:
    """Tests for the /cluster page"""

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.parametrize(
        "bundle_archive",
        [
            pytest.param(get_data_dir(__file__, BUNDLE_COMMUNITY), id="community"),
            pytest.param(get_data_dir(__file__, BUNDLE_ENTERPRISE), id="enterprise"),
        ],
        indirect=True,
    )
    def test_check_cluster_list_page_with_cluster_creating(self, app_fs, bundle_archive):
        """Test cluster info from the cluster row at /cluster page"""
        edition = bundle_archive.split("cluster_")[2][:-4]
        cluster_params = {
            "bundle": f"test_cluster 1.5 {edition}",
            "description": "Test",
            "state": "created",
        }
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        with allure.step("Check no cluster rows"):
            assert len(cluster_page.table.get_all_rows()) == 0, "There should be no row with clusters"
        cluster_page.create_cluster(
            bundle_archive, cluster_params['description'], is_license=bool(edition == "enterprise")
        )
        with allure.step("Check uploaded cluster"):
            assert len(cluster_page.table.get_all_rows()) == 1, "There should be 1 row with cluster"
            uploaded_cluster = cluster_page.get_cluster_info_from_row(0)
            assert cluster_params['bundle'] == uploaded_cluster['bundle'], (
                f"Cluster bundle should be {cluster_params['bundle']} and " f"not {uploaded_cluster['bundle']}"
            )
            assert cluster_params['description'] == uploaded_cluster['description'], (
                f"Cluster description should be {cluster_params['description']} and "
                f"not {uploaded_cluster['description']}"
            )
            assert cluster_params['state'] == uploaded_cluster['state'], (
                f"Cluster state should be {cluster_params['state']} " f"and not {uploaded_cluster['state']}"
            )

    def test_check_cluster_list_page_pagination(self, sdk_client_fs: ADCMClient, app_fs):
        """Test /cluster page pagination"""
        with allure.step("Create 11 clusters"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
            for i in range(11):
                bundle.cluster_create(name=f"{CLUSTER_NAME} {i}")
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        cluster_page.close_info_popup()
        check_pagination(cluster_page.table, expected_on_second=1)

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.usefixtures("create_community_cluster")
    def test_check_cluster_list_page_action_run(self, app_fs):
        """Test action run from the button in the cluster row on /cluster page"""
        params = {"action_name": "test_action", "expected_state": "installed"}
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row = cluster_page.table.get_all_rows()[0]
        with cluster_page.wait_cluster_state_change(row):
            cluster_page.run_action_in_cluster_row(row, params["action_name"])
        with allure.step("Check cluster state has changed"):
            wait_and_assert_ui_info(
                {"state": params["expected_state"]},
                wrap_in_dict("state", cluster_page.get_cluster_state_from_row),
                get_info_kwargs={'row': row},
            )
        with allure.step("Check success cluster job"):
            assert cluster_page.header.get_success_job_amount() == 1, "There should be 1 success cluster job in header"

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_check_cluster_list_page_import_run(self, create_import_cluster_with_service, app_fs):
        """Test import run from the button in the cluster row on /cluster page"""
        cluster, _, _, _ = create_import_cluster_with_service
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row = cluster_page.get_row_by_cluster_name(CLUSTER_NAME)
        cluster_page.click_import_btn_in_row(row)
        import_page = ClusterImportPage(app_fs.driver, app_fs.adcm.url, cluster.id)
        import_page.wait_page_is_opened()
        with allure.step("Check import on import page"):
            assert len(import_page.get_import_items()) == 1, "Cluster import page should contain 1 import"

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_check_cluster_list_page_open_cluster_config(self, app_fs, create_community_cluster):
        """Test cluster config open from the button in the cluster row on /cluster page"""
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row = cluster_page.table.get_all_rows()[0]
        cluster_page.click_config_button_in_row(row)
        ClusterConfigPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).wait_page_is_opened()

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_check_cluster_list_page_open_cluster_main(self, app_fs, create_community_cluster):
        """Test cluster page open from the button in the cluster row on /cluster page"""
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row = cluster_page.table.get_all_rows()[0]
        cluster_page.click_cluster_name_in_row(row)
        ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).wait_page_is_opened()

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.usefixtures("create_community_cluster")
    def test_check_cluster_list_page_delete_cluster(self, app_fs):
        """Test delete cluster from the button in the cluster row on /cluster page"""
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row = cluster_page.table.get_all_rows()[0]
        with cluster_page.table.wait_rows_change():
            cluster_page.delete_cluster_by_row(row)
        with allure.step("Check there are no rows"):
            assert len(cluster_page.table.get_all_rows()) == 0, "Cluster table should be empty"

    def test_run_upgrade_on_cluster_list_page(self, sdk_client_fs, app_fs):
        """Test run upgrade cluster from the /cluster page"""
        params = {
            "upgrade_cluster_name": "upgrade cluster",
            "upgrade": "upgrade 2",
            "state": "upgradated",
        }
        with allure.step("Create main cluster"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
            bundle.cluster_create(name=CLUSTER_NAME)
        with allure.step("Create cluster to upgrade"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_UPGRADE)
            cluster_to_upgrade = bundle.cluster_create(name=params["upgrade_cluster_name"])
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row_with_upgrade = cluster_page.get_row_by_cluster_name(cluster_to_upgrade.name)
        cluster_page.run_upgrade_in_cluster_row(row=row_with_upgrade, upgrade_name=params["upgrade"])
        check_cluster_upgraded(app_fs, params["upgrade_cluster_name"], params["state"])

    @pytest.mark.parametrize(
        ("upgrade_name", "config", "hc_acl", "is_new_host", "disclaimer_text"),
        [
            ("simple_upgrade", None, False, False, False),
            ("upgrade_with_hc_acl", None, True, False, False),
            ("upgrade_with_config", {"somestring2": "test"}, False, False, False),
            ("upgrade_with_config_and_hc_acl", {"somestring2": "test"}, True, False, False),
            ("upgrade_with_hc_acl_and_disclaimer", None, True, False, DISCLAIMER_TEXT),
            (
                "upgrade_with_config_and_disclaimer",
                {"somestring2": "test"},
                False,
                False,
                DISCLAIMER_TEXT,
            ),
            (
                "upgrade_with_config_and_hc_acl_and_disclaimer",
                {"somestring2": "test"},
                True,
                False,
                DISCLAIMER_TEXT,
            ),
            # next steps are skipped until https://tracker.yandex.ru/ADCM-3001
            # ("upgrade_with_hc_acl", None, True, True, False),
            # ("upgrade_with_config_and_hc_acl", {"somestring2": "test"}, True, True, False),
            # ("upgrade_with_hc_acl_and_disclaimer", None, True, True, DISCLAIMER_TEXT),
            # ("upgrade_with_config_and_hc_acl_and_disclaimer", {"somestring2": "test"}, True, True, DISCLAIMER_TEXT),
        ],
    )
    def test_run_upgrade_v2_on_cluster_list_page(
        self,
        upload_and_create_provider,
        sdk_client_fs,
        app_fs,
        upgrade_name,
        config,
        hc_acl,
        is_new_host,
        disclaimer_text,
    ):
        """Test run upgrade new version from the /cluster page"""
        params = {"state": "upgraded"}
        with allure.step("Upload main cluster bundle"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            if not is_new_host:
                host = upload_and_create_provider.host_create(HOST_NAME)
                cluster.host_add(host)
        with allure.step("Upload cluster bundle to upgrade"):
            cluster_bundle(sdk_client_fs, BUNDLE_UPGRADE_V2)
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row_with_upgrade = cluster_page.get_row_by_cluster_name(CLUSTER_NAME)
        cluster_page.run_upgrade_in_cluster_row(
            row=row_with_upgrade,
            upgrade_name=upgrade_name,
            config=config,
            hc_acl=hc_acl,
            is_new_host=is_new_host,
            disclaimer_text=disclaimer_text,
        )
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        cluster_page.header.wait_success_job_amount(1)
        check_cluster_upgraded(app_fs, CLUSTER_NAME, params["state"])


class TestClusterMainPage:
    """Tests for the /cluster/{}/main page"""

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_open_by_tab_cluster_main_page(self, app_fs, create_community_cluster):
        """Test open /cluter/{}/main page from left menu"""
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_main_page = cluster_config_page.open_main_tab()
        cluster_main_page.check_all_elements()
        cluster_main_page.check_cluster_toolbar(CLUSTER_NAME)

    def test_check_cluster_admin_page_open_by_toolbar(self, app_fs, create_community_cluster):
        """Test open admin/intro page from cluster toolbar"""
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_main_page.toolbar.click_admin_link()
        AdminIntroPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()

    def test_check_cluster_main_page_open_by_toolbar(self, app_fs, create_community_cluster):
        """Test open /cluter/{}/main page from cluster toolbar"""
        params = {"cluster_list_name": "CLUSTERS"}
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_main_page.toolbar.click_link_by_name(params["cluster_list_name"])
        ClusterListPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()
        cluster_import_page = ClusterImportPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_import_page.toolbar.click_link_by_name(CLUSTER_NAME)
        cluster_main_page.wait_page_is_opened()
        cluster_main_page.check_cluster_toolbar(CLUSTER_NAME)

    def test_run_upgrade_on_cluster_page_by_toolbar(self, sdk_client_fs, app_fs):
        """Test run upgrade cluster from the /cluster/{}/main page toolbar"""
        params = {
            "upgrade_cluster_name": "upgrade cluster",
            "upgrade": "upgrade 2",
            "state": "upgradated",
        }
        with allure.step("Create main cluster"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_COMMUNITY)
            bundle.cluster_create(name=CLUSTER_NAME)
        with allure.step("Create cluster to upgrade"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_UPGRADE)
            cluster_to_upgrade = bundle.cluster_create(name=params["upgrade_cluster_name"])
        main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, cluster_to_upgrade.id).open()
        main_page.toolbar.run_upgrade(params["upgrade_cluster_name"], params["upgrade"])
        check_cluster_upgraded(app_fs, params["upgrade_cluster_name"], params["state"])

    def test_check_cluster_run_action_on_cluster_page_by_toolbar(self, app_fs, create_community_cluster):
        """Test run action from the /cluster/{}/main page toolbar"""
        params = {"action_name": "long_action"}
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_main_page.toolbar.run_action(CLUSTER_NAME, params["action_name"])
        with allure.step("Check success job"):
            assert (
                cluster_main_page.header.get_in_progress_job_amount() == 1
            ), "There should be 1 in progress job in header"


class TestClusterServicePage:
    """Tests for the /cluster/{}/service page"""

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_check_cluster_service_page_open_by_tab(self, app_fs, create_community_cluster):
        """Test open /cluter/{}/service page from left menu"""
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_service_page = cluster_config_page.open_services_tab()
        cluster_service_page.check_all_elements()
        cluster_service_page.check_cluster_toolbar(CLUSTER_NAME)

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_check_create_and_open_service_page_from_cluster_page(self, app_fs, create_community_cluster):
        """Test add service and open service page from cluster/{}/service page"""
        params = {"service_name": "test_service - 1.2"}
        cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_service_page.add_service_by_name(params["service_name"])
        service_row = cluster_service_page.table.get_all_rows()[0]
        service_row.click()
        service_main_page = ServiceMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id, 1)
        service_main_page.wait_page_is_opened()
        service_main_page.check_service_toolbar(CLUSTER_NAME, SERVICE_NAME)

    def test_concerns_from_cluster_list_page(self, sdk_client_fs: ADCMClient, app_fs):
        """Test click on concern from cluster list page"""
        params = {"concern_object_name": CLUSTER_NAME}
        bundle = cluster_bundle(sdk_client_fs, BUNDLE_REQUIRED_FIELDS)
        cluster = bundle.cluster_create(name=CLUSTER_NAME)
        cluster_list_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        row = cluster_list_page.table.get_all_rows()[0]
        cluster_list_page.click_on_concern_by_object_name(row, params["concern_object_name"])
        cluster_main_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id)
        cluster_main_page.wait_page_is_opened()
        cluster_main_page.check_cluster_toolbar(CLUSTER_NAME)

    def test_concerns_from_from_service_list_page(self, sdk_client_fs: ADCMClient, app_fs):
        """Test click on concern from cluster/{}/service page"""
        params = {"concern_object_name": SERVICE_NAME}
        bundle = cluster_bundle(sdk_client_fs, BUNDLE_REQUIRED_FIELDS)
        cluster = bundle.cluster_create(name=CLUSTER_NAME).service_add(name=SERVICE_NAME)
        cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_service_page.table.get_all_rows()[0]
        cluster_service_page.click_on_concern_by_object_name(row, params["concern_object_name"])
        service_main_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, 1)
        service_main_page.wait_page_is_opened()
        service_main_page.check_service_toolbar(CLUSTER_NAME, SERVICE_NAME)

    @including_https
    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_check_actions_from_service_list_page(self, app_fs, create_community_cluster_with_service):
        """Test run action from the row on cluster/{}/service page"""
        params = {"action_name": "test_action", "expected_state": "installed"}

        cluster, _ = create_community_cluster_with_service
        cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_service_page.table.get_all_rows()[0]
        with cluster_service_page.wait_service_state_change(row):
            cluster_service_page.run_action_in_service_row(row, params["action_name"])
        with allure.step("Check service state has changed"):
            assert (
                cluster_service_page.get_service_state_from_row(row) == params["expected_state"]
            ), f"Cluster state should be {params['expected_state']}"
        with allure.step("Check success service job"):
            assert (
                cluster_service_page.header.get_success_job_amount() == 1
            ), "There should be 1 success service job in header"

    def test_check_service_list_page_import_run(self, app_fs, create_import_cluster_with_service):
        """Test run import from the row on cluster/{}/service page"""
        cluster, service, _, _ = create_import_cluster_with_service
        cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_service_page.table.get_all_rows()[0]
        cluster_service_page.click_import_btn_in_row(row)
        import_page = ServiceImportPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id)
        import_page.wait_page_is_opened()
        with allure.step("Check import on import page"):
            assert len(import_page.get_import_items()) == 1, "Service import page should contain 1 import"
        import_page.check_service_toolbar(CLUSTER_NAME, SERVICE_NAME)

    def test_check_service_list_page_open_service_config(self, app_fs, create_community_cluster_with_service):
        """Test open service config from the row on cluster/{}/service page"""
        cluster, service = create_community_cluster_with_service
        cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_service_page.table.get_all_rows()[0]
        cluster_service_page.click_config_btn_in_row(row)
        service_conf_page = ServiceConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, service.id)
        service_conf_page.wait_page_is_opened()
        service_conf_page.check_service_toolbar(CLUSTER_NAME, SERVICE_NAME)

    def test_check_pagination_on_service_list_page(self, sdk_client_fs: ADCMClient, app_fs):
        """Test pagination on cluster/{}/service page"""
        bundle = cluster_bundle(sdk_client_fs, BUNDLE_WITH_SERVICES)
        cluster = bundle.cluster_create(name=CLUSTER_NAME)
        cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_service_page.add_service_by_name(service_name="All")
        try:
            cluster_service_page.wait_page_is_opened(timeout=30)
        except TimeoutException:
            cluster_service_page.driver.refresh()
            cluster_service_page.wait_page_is_opened(timeout=30)
        check_pagination(cluster_service_page.table, expected_on_second=2)

    def test_delete_service_on_service_list_page(self, app_fs, create_community_cluster_with_service):
        """Test delete service from cluster/{}/service page"""

        cluster, _ = create_community_cluster_with_service
        cluster_service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_service_page.table.get_all_rows()[0]
        cluster_service_page.click_delete_btn_in_row(row)
        with allure.step("Check that after deleting service row there are no rows"):
            assert len(cluster_service_page.table.get_all_rows(timeout=2)) == 0, "There should not be any rows"


class TestClusterHostPage:
    """Tests for the /cluster/{}/host page"""

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_required_fields_from_cluster_host_page(self, app_fs, create_community_cluster_with_service):
        """Test fields on cluster/{}/host page"""
        cluster, _ = create_community_cluster_with_service
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_main_page.open_hosts_tab()
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id)
        cluster_host_page.wait_page_is_opened()
        cluster_host_page.check_all_elements()
        cluster_host_page.check_cluster_toolbar(CLUSTER_NAME)

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.parametrize("bundle_archive", [get_data_dir(__file__, "provider")], indirect=True)
    def test_create_host_and_hostprovider_from_cluster_host_page(
        self, app_fs, bundle_archive, create_community_cluster_with_service
    ):
        """Test create host and hostprovider from cluster/{}/host page"""
        cluster, _ = create_community_cluster_with_service
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_host_page.wait_page_is_opened()
        dialog = cluster_host_page.click_add_host_btn(is_not_first_host=False)
        new_provider_name = dialog.create_provider_and_host(bundle_archive, HOST_NAME)
        expected_values = {
            'fqdn': HOST_NAME,
            'provider': new_provider_name,
            'cluster': None,
            'state': 'created',
        }
        wait_and_assert_ui_info(
            expected_values,
            cluster_host_page.get_host_info_from_row,
            get_info_kwargs={'table_has_cluster_column': False},
        )

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.usefixtures("upload_and_create_provider")
    def test_create_host_from_cluster_host_page(self, app_fs, create_community_cluster_with_service):
        """Test create host from cluster/{}/host page"""
        expected_values = {
            'fqdn': HOST_NAME,
            'provider': PROVIDER_NAME,
            'cluster': None,
            'state': 'created',
        }
        cluster, _ = create_community_cluster_with_service
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_host_page.wait_page_is_opened()
        dialog = cluster_host_page.click_add_host_btn(is_not_first_host=False)
        dialog.create_host(HOST_NAME)
        wait_and_assert_ui_info(
            expected_values,
            cluster_host_page.get_host_info_from_row,
            get_info_kwargs={'table_has_cluster_column': False},
        )
        host_row = cluster_host_page.table.get_all_rows()[0]
        cluster_host_page.click_on_host_name_in_host_row(host_row)
        HostMainPage(app_fs.driver, app_fs.adcm.url, cluster.id, 1).wait_page_is_opened()
        cluster_host_page.check_cluster_hosts_toolbar(CLUSTER_NAME, HOST_NAME)

    @pytest.mark.usefixtures('create_host')
    def test_create_host_error_from_cluster_host_page(self, app_fs, create_community_cluster_with_service):
        """Test create host from cluster/{}/host page error"""
        cluster, _ = create_community_cluster_with_service
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_host_page.wait_page_is_opened()
        cluster_host_page.close_info_popup()
        dialog = cluster_host_page.click_add_host_btn()
        dialog.create_host(HOST_NAME)
        with allure.step("Check error message"):
            assert (
                cluster_host_page.get_info_popup_text() == '[ CONFLICT ] HOST_CONFLICT -- duplicate host'
            ), "No message about host duplication"

    @pytest.mark.parametrize('provider_bundle', [PROVIDER_WITH_ISSUE_NAME], indirect=True)
    def test_open_host_concern_from_cluster_host_page(self, app_fs, create_community_cluster_with_host):
        """Test open host concern from cluster/{}/host page"""
        cluster, host = create_community_cluster_with_host
        params = {"concern_object_name": host.fqdn}
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_host_page.wait_page_is_opened()
        row = cluster_host_page.table.get_all_rows()[0]
        cluster_host_page.click_on_concern_by_object_name(row, params["concern_object_name"])
        host_page = HostConfigPage(app_fs.driver, app_fs.adcm.url, host.id)
        host_page.wait_page_is_opened()
        host_page.check_host_toolbar(HOST_NAME)

    def test_host_action_run_from_cluster(self, app_fs, create_community_cluster_with_host):
        """Test host action run from cluster/{}/host page"""
        params = {"action_name": "test_action", "expected_state": "installed"}
        cluster, _ = create_community_cluster_with_host
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_host_page.table.get_all_rows()[0]
        with cluster_host_page.wait_host_state_change(row):
            cluster_host_page.run_action_in_host_row(row, params["action_name"])
        with allure.step("Check host state has changed"):
            assert (
                cluster_host_page.get_host_state_from_row(row) == params["expected_state"]
            ), f"Cluster state should be {params['expected_state']}"
        with allure.step("Check success host job"):
            assert (
                cluster_host_page.header.get_success_job_amount() == 1
            ), "There should be 1 success host job in header"

    def test_check_delete_host_from_cluster_host_page(self, app_fs, create_community_cluster_with_host):
        """Test host delete from cluster/{}/host page"""
        cluster, _ = create_community_cluster_with_host
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_host_page.table.get_all_rows()[0]
        with cluster_host_page.table.wait_rows_change():
            cluster_host_page.delete_host_by_row(row)
        with allure.step("Check there are no rows"):
            assert len(cluster_host_page.table.get_all_rows()) == 0, "Host table should be empty"

    def test_delete_linked_host_from_cluster_components_page(
        self, app_fs, create_community_cluster_with_host_and_service
    ):
        """Test host with component delete from cluster/{}/host page"""
        params = {"message": "[ CONFLICT ] HOST_CONFLICT -- Host #1 has component(s)"}
        cluster, host = create_community_cluster_with_host_and_service
        cluster.hostcomponent_set((host, cluster.service(name=SERVICE_NAME).component(name=COMPONENT_NAME)))
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_host_page.table.get_all_rows()[0]
        cluster_host_page.delete_host_by_row(row)
        with allure.step("Check error message"):
            assert cluster_host_page.get_info_popup_text() == params["message"], "No error message"

    def test_open_host_config_from_cluster_host_page(self, app_fs, create_community_cluster_with_host):
        """Test open host config from cluster/{}/host page"""
        cluster, host = create_community_cluster_with_host
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        row = cluster_host_page.table.get_all_rows()[0]
        cluster_host_page.click_config_btn_in_row(row)
        HostConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id, host.id).wait_page_is_opened()
        cluster_host_page.check_cluster_hosts_toolbar(CLUSTER_NAME, HOST_NAME)

    def test_check_pagination_on_cluster_host_page(self, app_fs, upload_and_create_provider, create_community_cluster):
        """Test pagination on cluster/{}/host page"""
        cluster = create_community_cluster
        provider = upload_and_create_provider
        host_count = 11
        with allure.step(f'Create {host_count} hosts'):
            for i in range(host_count):
                host = provider.host_create(f"{HOST_NAME}-{i}")
                cluster.host_add(host)
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, 1).open()
        check_pagination(cluster_host_page.table, expected_on_second=1)
        cluster_host_page.check_cluster_toolbar(CLUSTER_NAME)

    @pytest.mark.smoke()
    def test_maintenance_mode_from_cluster_host_page(self, app_fs, create_community_cluster_with_host):
        """Test turn on and off maintenance mode on cluster/{}/host page"""

        cluster, _ = create_community_cluster_with_host
        cluster_host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()

        with allure.step("Check that user can change maintenance mode state"):
            cluster_host_page.assert_maintenance_mode_state(0)
            cluster_host_page.click_on_maintenance_mode_btn(0)
            cluster_host_page.assert_maintenance_mode_state(0, False)


class TestClusterComponentsPage:
    """Tests for the /cluster/{}/component page"""

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_check_cluster_components_page_open_by_tab(self, app_fs, create_community_cluster):
        """Test open /cluter/{}/component page from left menu"""
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_components_page = cluster_config_page.open_components_tab()
        cluster_components_page.check_all_elements()
        cluster_components_page.check_cluster_toolbar(CLUSTER_NAME)

    def test_check_cluster_components_page_open_service_page(self, app_fs, create_community_cluster):
        """Test open /cluster/{}/service from /cluster/{}/component"""
        cluster_components_page = ClusterComponentsPage(
            app_fs.driver, app_fs.adcm.url, create_community_cluster.id
        ).open()
        cluster_components_page.click_service_page_link()
        service_page = ClusterServicesPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id)
        service_page.wait_page_is_opened()
        service_page.check_cluster_toolbar(CLUSTER_NAME)

    def test_check_cluster_components_page_open_hosts_page(self, app_fs, create_community_cluster):
        """Test open /cluter/{}/host from /cluter/{}/component"""
        cluster_components_page = ClusterComponentsPage(
            app_fs.driver, app_fs.adcm.url, create_community_cluster.id
        ).open()
        cluster_components_page.click_hosts_page_link()
        host_page = ClusterHostPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id)
        host_page.wait_page_is_opened()
        host_page.check_cluster_toolbar(CLUSTER_NAME)

    @pytest.mark.parametrize("bundle_archive", [get_data_dir(__file__, "provider")], indirect=True)
    def test_check_cluster_components_page_create_host(self, app_fs, bundle_archive, create_community_cluster):
        """Test add host from /cluster/{}/component"""
        cluster_components_page = ClusterComponentsPage(
            app_fs.driver, app_fs.adcm.url, create_community_cluster.id
        ).open()
        dialog = cluster_components_page.click_add_host_btn()
        dialog.create_provider_and_host(bundle_path=bundle_archive, fqdn=HOST_NAME)
        host_row = cluster_components_page.get_host_rows()[0]
        check_components_host_info(cluster_components_page.get_row_info(host_row), HOST_NAME, "0")

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    @pytest.mark.parametrize(
        "bundle_name",
        [
            "cluster_with_not_required_component",
            "cluster_with_required_component",
            "cluster_with_required_component_short",
        ],
    )
    def test_check_cluster_components_page_create_components(self, app_fs, sdk_client_fs, create_host, bundle_name):
        """Test adding components on hosts"""

        params = {"message": "Successfully saved."}
        is_not_required = "_not_required" in bundle_name

        with allure.step("Add cluster with service and host"):
            bundle = cluster_bundle(sdk_client_fs, bundle_name)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            cluster.service_add(name=SERVICE_NAME)
            cluster.host_add(create_host)

        cluster_components_page = ClusterComponentsPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()

        with allure.step("Check that required component has * in name"):
            component_name = cluster_components_page.get_components_rows()[0].text
            assert (
                "*" not in component_name if is_not_required else f"* {COMPONENT_NAME}" in component_name
            ), f'There are {"" if is_not_required else "no"} * in component name "{component_name}"'

        host_row = cluster_components_page.find_host_row_by_name(HOST_NAME)
        component_row = cluster_components_page.find_component_row_by_name(COMPONENT_NAME)
        cluster_components_page.click_host(host_row)
        cluster_components_page.click_component(component_row)

        cluster_components_page.close_info_popup()
        cluster_components_page.click_save_btn()
        with allure.step("Check that host and component are linked"):
            assert cluster_components_page.get_info_popup_text() == params["message"], "No message about success"
            host_row = cluster_components_page.get_host_rows()[0]
            check_components_host_info(cluster_components_page.get_row_info(host_row), HOST_NAME, "1")
            component_row = cluster_components_page.get_components_rows()[0]
            check_components_host_info(
                cluster_components_page.get_row_info(component_row),
                COMPONENT_NAME,
                "1" if is_not_required else "1 / 1",
            )

    def test_check_cluster_components_page_restore_components(
        self, app_fs, create_community_cluster_with_host_and_service
    ):
        """Test restore components to hosts distribution"""
        cluster, *_ = create_community_cluster_with_host_and_service
        cluster_components_page = ClusterComponentsPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        host_row = cluster_components_page.find_host_row_by_name(HOST_NAME)
        component_row = cluster_components_page.find_component_row_by_name(COMPONENT_NAME)
        cluster_components_page.click_host(host_row)
        cluster_components_page.click_component(component_row)

        cluster_components_page.close_info_popup()
        cluster_components_page.click_restore_btn()
        with allure.step("Check that host and component are not linked"):
            host_row = cluster_components_page.get_host_rows()[0]
            check_components_host_info(cluster_components_page.get_row_info(host_row), HOST_NAME, "0")
            component_row = cluster_components_page.get_components_rows()[0]
            check_components_host_info(cluster_components_page.get_row_info(component_row), COMPONENT_NAME, "0")

    def test_check_cluster_components_page_delete_host_from_component(
        self, app_fs, create_community_cluster_with_host_and_service
    ):
        """Test delete component from host"""
        cluster, *_ = create_community_cluster_with_host_and_service
        cluster_components_page = ClusterComponentsPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        host_row = cluster_components_page.find_host_row_by_name(HOST_NAME)
        component_row = cluster_components_page.find_component_row_by_name(COMPONENT_NAME)

        cluster_components_page.click_host(host_row)
        cluster_components_page.click_component(component_row)
        cluster_components_page.click_save_btn()

        cluster_components_page.click_number_in_component(component_row)
        cluster_components_page.delete_related_item_in_row_by_name(component_row, HOST_NAME)

        with allure.step("Check that host and component are not linked"):
            host_row = cluster_components_page.get_host_rows()[0]
            check_components_host_info(cluster_components_page.get_row_info(host_row), HOST_NAME, "0")
            component_row = cluster_components_page.get_components_rows()[0]
            check_components_host_info(cluster_components_page.get_row_info(component_row), COMPONENT_NAME, "0")

    def test_add_few_hosts_to_component_on_cluster_components_page(self, sdk_client_fs, app_fs, create_host):
        """Test not all components distributed over hosts"""
        with allure.step("Create cluster with service and host"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_WITH_SERVICES)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            cluster.service_add(name=f"{SERVICE_NAME}_1")
            cluster.host_add(create_host)

        cluster_components_page = ClusterComponentsPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        host_row = cluster_components_page.find_host_row_by_name(HOST_NAME)
        component_row = cluster_components_page.find_component_row_by_name(COMPONENT_NAME)

        cluster_components_page.click_host(host_row)
        cluster_components_page.click_component(component_row)
        with allure.step("Check that save button is disabled when not all required amount of hosts are linked"):
            assert cluster_components_page.check_that_save_btn_disabled(), "Save button should be disabled"

    def test_warning_on_cluster_components_page(self, app_fs, sdk_client_fs):
        """Test components warning !"""

        with allure.step("Create cluster and add service"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_WITH_REQUIRED_COMPONENT)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
            cluster.service_add(name=SERVICE_NAME)
        cluster_components_page = ClusterComponentsPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_components_page.config.check_hostcomponents_warn_icon_on_left_menu()
        cluster_components_page.toolbar.check_warn_button(
            tab_name=CLUSTER_NAME,
            expected_warn_text=['Test cluster has an issue with host-component mapping'],
        )


class TestClusterConfigPage:
    """Tests for the /cluster/{}/config page"""

    def test_cluster_config_page_open_by_tab(self, app_fs, create_community_cluster):
        """Test open /cluster/{}/config from left menu"""
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_config_page = cluster_main_page.open_config_tab()
        cluster_config_page.check_all_elements()
        cluster_config_page.check_cluster_toolbar(CLUSTER_NAME)

    def test_filter_config_on_cluster_config_page(self, app_fs, create_community_cluster):
        """Test config filtration on cluster/{}/config page"""
        params = {"search_param": "str_param", "group_name": "core-site"}
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        with cluster_config_page.config.wait_rows_change():
            cluster_config_page.config.search(params["search_param"])
        with allure.step(f"Check that rows are filtered by {params['search_param']}"):
            config_rows = cluster_config_page.config.get_all_config_rows()
            assert len(config_rows) == 1, "Rows are not filtered: there should be 1 row"
            assert (
                cluster_config_page.config.get_config_row_info(config_rows[0]).name == f"{params['search_param']}:"
            ), f"Name should be {params['search_param']}"
        with cluster_config_page.config.wait_rows_change():
            cluster_config_page.config.clear_search_input()
        with allure.step("Check that rows are not filtered"):
            config_rows = cluster_config_page.config.get_all_config_rows()
            assert len(config_rows) == 5, "Rows are filtered: there should be 4 row and 1 group"
        with cluster_config_page.config.wait_rows_change(expected_rows_amount=3):
            cluster_config_page.config.click_on_group(params["group_name"])

    def test_save_custom_config_on_cluster_config_page(self, app_fs, create_cluster_with_all_config_fields):
        """Test config save on cluster/{}/config page"""

        params = {
            "config_name_new": "test_name",
            "config_name_old": "init",
        }

        cluster_config_page = ClusterConfigPage(
            app_fs.driver, app_fs.adcm.url, create_cluster_with_all_config_fields.id
        ).open()
        cluster_config_page.config.fill_config_fields_with_test_values()
        cluster_config_page.config.set_description(params["config_name_new"])
        cluster_config_page.config.save_config()
        cluster_config_page.config.compare_versions(params["config_name_old"])
        cluster_config_page.config.check_config_fields_history_with_test_values()

    def test_reset_config_in_row_on_cluster_config_page(self, app_fs, create_community_cluster):
        """Test config reset on cluster/{}/config page"""
        params = {
            "row_name": "str_param",
            "row_value_new": "test",
            "row_value_old": "123",
            "config_name": "test_name",
        }
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        config_row = cluster_config_page.config.get_all_config_rows()[0]
        cluster_config_page.config.type_in_field_with_few_inputs(
            row=config_row, values=[params["row_value_new"]], clear=True
        )
        cluster_config_page.config.set_description(params["config_name"])
        cluster_config_page.config.save_config()
        cluster_config_page.driver.refresh()
        cluster_config_page.config.assert_input_value_is(
            expected_value=params["row_value_new"], display_name=params["row_name"]
        )

        config_row = cluster_config_page.config.get_all_config_rows()[0]
        cluster_config_page.config.reset_to_default(row=config_row)
        cluster_config_page.config.assert_input_value_is(
            expected_value=params["row_value_old"], display_name=params["row_name"]
        )

    def test_field_validation_on_cluster_config_page(self, app_fs, sdk_client_fs):
        """Test config fields validation on cluster/{}/config page"""
        params = {
            'pass_name': 'Important password',
            'req_name': 'Required item',
            'not_req_name': 'Just item',
            'wrong_value': 'test',
        }
        with allure.step("Create cluster"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_WITH_REQUIRED_FIELDS)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_config_page.config.check_password_confirm_required(params['pass_name'])
        cluster_config_page.config.check_field_is_required(params['req_name'])
        config_row = cluster_config_page.config.get_all_config_rows()[0]
        cluster_config_page.config.type_in_field_with_few_inputs(row=config_row, values=[params['wrong_value']])
        cluster_config_page.config.check_field_is_invalid_error(params['not_req_name'])
        cluster_config_page.config.check_config_warn_icon_on_left_menu()
        cluster_config_page.toolbar.check_warn_button(
            tab_name=CLUSTER_NAME, expected_warn_text=['Test cluster has an issue with its config']
        )

    def test_field_validation_on_cluster_config_page_with_default_value(self, app_fs, sdk_client_fs):
        """Test config fields validation on /cluster/{}/service/{}/config page"""

        params = {'field_name': 'string', 'new_value': 'test', "config_name": "test_name"}

        with allure.step("Create cluster"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_DEFAULT_FIELDS)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        cluster_config_page.config.clear_field_by_keys(params['field_name'])
        cluster_config_page.config.check_field_is_required(params['field_name'])
        cluster_config_page.config.type_in_field_with_few_inputs(
            row=cluster_config_page.config.get_all_config_rows()[0], values=[params['new_value']]
        )
        cluster_config_page.config.save_config()
        cluster_config_page.config.assert_input_value_is(
            expected_value=params["new_value"], display_name=params["field_name"]
        )

    def test_field_tooltips_on_cluster_config_page(self, app_fs, sdk_client_fs):
        """Test config fields tooltips on cluster/{}/config page"""

        with allure.step("Create cluster"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_WITH_DESCRIPTION_FIELDS)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
        cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        for item in CONFIG_ITEMS:
            cluster_config_page.config.check_text_in_tooltip(item, f"Test description {item}")

    # pylint: enable=too-many-locals
    @pytest.mark.full()
    @parametrize_by_data_subdirs(__file__, 'bundles_for_numbers_tests')
    def test_number_validation_on_cluster_config_page(self, sdk_client_fs: ADCMClient, path, app_fs):
        """Check that we have errors and save button is not active for number field with values out of range"""
        params = {"filed_name": "numbers_test"}

        _, cluster_config_page = prepare_cluster_and_open_config_page(sdk_client_fs, path, app_fs)

        with allure.step('Check that save button is active'):
            cluster_config_page.config.get_config_row("numbers_test").click()
            assert not cluster_config_page.config.is_save_btn_disabled(), 'Save button should be active'
        cluster_config_page.config.clear_field_by_keys(params["filed_name"])

        with allure.step('Check that save button is disabled'):
            assert cluster_config_page.config.is_save_btn_disabled(), 'Save button should be disabled'
        cluster_config_page.config.check_field_is_required(params["filed_name"])

        cluster_config_page.config.type_in_field_with_few_inputs(
            row=cluster_config_page.config.get_all_config_rows()[0], values=["asdsa"]
        )
        cluster_config_page.config.check_field_is_invalid_error(params["filed_name"])
        with allure.step('Check that save button is disabled'):
            assert cluster_config_page.config.is_save_btn_disabled(), 'Save button should be disabled'

        cluster_config_page.config.type_in_field_with_few_inputs(
            row=cluster_config_page.config.get_all_config_rows()[0], values=["-111111"], clear=True
        )
        with allure.step('Check that save button is disabled'):
            assert cluster_config_page.config.is_save_btn_disabled(), 'Save button should be disabled'
        cluster_config_page.config.check_invalid_value_message(
            f"Field [{params['filed_name']}] value cannot be less than"
        )

        cluster_config_page.config.type_in_field_with_few_inputs(
            row=cluster_config_page.config.get_all_config_rows()[0], values=["111111"], clear=True
        )
        with allure.step('Check that save button is disabled'):
            assert cluster_config_page.config.is_save_btn_disabled(), 'Save button should be disabled'
        cluster_config_page.config.check_invalid_value_message(
            f"Field [{params['filed_name']}] value cannot be greater than"
        )

    @pytest.mark.full()
    @pytest.mark.parametrize(("number_type", "value"), RANGE_VALUES)
    def test_number_in_range_values_on_cluster_config_page(self, sdk_client_fs: ADCMClient, value, app_fs, number_type):
        """Test save button is active for valid number values"""

        path = get_data_dir(__file__) + f"/bundles_for_numbers_tests/{number_type}-positive_and_negative"
        _, cluster_config_page = prepare_cluster_and_open_config_page(sdk_client_fs, path, app_fs)
        cluster_config_page.config.type_in_field_with_few_inputs(
            row=cluster_config_page.config.get_all_config_rows()[0], values=[str(value)], clear=True
        )
        with allure.step('Check that save button active for number fields in min-max range'):
            assert not cluster_config_page.config.is_save_btn_disabled(), 'Save button should be active'

    def test_float_in_integer_field_on_cluster_config_page(self, sdk_client_fs: ADCMClient, app_fs):
        """Test set float value for integer field"""

        params = {"filed_name": "numbers_test"}
        path = get_data_dir(__file__) + "/bundles_for_numbers_tests/integer-positive_and_negative"
        _, cluster_config_page = prepare_cluster_and_open_config_page(sdk_client_fs, path, app_fs)
        cluster_config_page.config.type_in_field_with_few_inputs(
            row=cluster_config_page.config.get_all_config_rows()[0], values=["1.2"], clear=True
        )
        with allure.step('Check that we cannot set float in integer field'):
            assert cluster_config_page.config.is_save_btn_disabled(), 'Save button should be disabled'
            cluster_config_page.config.check_field_is_invalid_error(params["filed_name"])

    def test_save_list_on_cluster_config_page(self, sdk_client_fs: ADCMClient, app_fs):
        """Test set value for list field, save and refresh page"""

        params = {"new_value": ["test", "test", "test"]}
        config, _, path = prepare_config(
            generate_configs(
                field_type="list",
                invisible=False,
                advanced=False,
                default=True,
                required=False,
                read_only=False,
            )
        )
        _, cluster_config_page = prepare_cluster_and_open_config_page(sdk_client_fs, path, app_fs)
        cluster_config_page.config.type_in_field_with_few_inputs(
            row=cluster_config_page.config.get_all_config_rows()[0],
            values=params["new_value"],
            clear=True,
        )
        cluster_config_page.config.save_config()
        cluster_config_page.driver.refresh()
        with allure.step('Check saved list values'):
            cluster_config_page.config.assert_list_value_is(
                expected_value=params["new_value"], display_name=config['config'][0]['name']
            )

    def test_save_map_on_cluster_config_page(self, sdk_client_fs: ADCMClient, app_fs):
        """Test set value for map field, save and refresh page"""

        params = {"new_value": {'test': 'test', 'test_2': 'test', 'test_3': 'test'}}
        config, _, path = prepare_config(
            generate_configs(
                field_type="map",
                invisible=False,
                advanced=False,
                default=True,
                required=False,
                read_only=False,
            )
        )
        _, cluster_config_page = prepare_cluster_and_open_config_page(sdk_client_fs, path, app_fs)
        cluster_config_page.config.type_in_field_with_few_inputs(
            row=cluster_config_page.config.get_all_config_rows()[0],
            values=['test', 'test', 'test_2', 'test', 'test_3', 'test'],
            clear=True,
        )
        cluster_config_page.config.save_config()
        cluster_config_page.driver.refresh()
        with allure.step('Check saved map values'):
            cluster_config_page.config.assert_map_value_is(
                expected_value=params["new_value"], display_name=config['config'][0]['name']
            )


class TestClusterGroupConfigPage:
    """Tests for the cluster/{}/group_config page"""

    def test_open_by_tab_group_config_list_cluster_page(self, app_fs, create_community_cluster):
        """Test open cluster/{}/group_config from left menu"""

        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_groupconf_page = cluster_main_page.open_group_config_tab()
        cluster_groupconf_page.check_all_elements()
        cluster_groupconf_page.check_cluster_toolbar(CLUSTER_NAME)

    def test_open_by_tab_group_config_host_cluster_page(self, app_fs, create_community_cluster):
        """Test open cluster/{}/group_config from left menu"""

        params = {'group_name': 'Test group'}
        cluster_group_config = create_community_cluster.group_config_create(name=params['group_name'])
        cluster_config_page = ClusterGroupConfigConfig(
            app_fs.driver, app_fs.adcm.url, create_community_cluster.id, cluster_group_config.id
        ).open()
        cluster_groupconf_page = cluster_config_page.open_hosts_tab()
        cluster_groupconf_page.check_all_elements()
        cluster_groupconf_page.check_cluster_group_conf_toolbar(CLUSTER_NAME, params['group_name'])

    def test_open_by_tab_group_config_cluster_page(self, app_fs, create_community_cluster):
        """Test open cluster/{}/group_config from left menu"""

        params = {'group_name': 'Test group'}
        cluster_group_config = create_community_cluster.group_config_create(name=params['group_name'])
        cluster_host_config_page = ClusterGroupConfigHosts(
            app_fs.driver, app_fs.adcm.url, create_community_cluster.id, cluster_group_config.id
        ).open()
        cluster_groupconf_page = cluster_host_config_page.open_config_tab()
        cluster_groupconf_page.check_all_elements()
        cluster_groupconf_page.check_cluster_group_conf_toolbar(CLUSTER_NAME, params['group_name'])

    def test_create_group_config_cluster(self, app_fs, create_community_cluster):
        """Test create group config on cluster/{}/group_config"""

        params = {
            'name': 'Test name',
            'description': 'Test description',
        }

        cluster_group_conf_page = ClusterGroupConfigPage(
            app_fs.driver, app_fs.adcm.url, create_community_cluster.id
        ).open()
        with cluster_group_conf_page.group_config.wait_rows_change(expected_rows_amount=1):
            cluster_group_conf_page.group_config.create_group(name=params['name'], description=params['description'])
        group_row = cluster_group_conf_page.group_config.get_all_config_rows()[0]
        with allure.step("Check created row in cluster"):
            group_info = cluster_group_conf_page.group_config.get_config_row_info(group_row)
            assert group_info == GroupConfigRowInfo(
                name=params['name'], description=params['description']
            ), "Row value differs in cluster groups"
        with cluster_group_conf_page.group_config.wait_rows_change(expected_rows_amount=0):
            cluster_group_conf_page.group_config.delete_row(group_row)

    def test_check_pagination_on_group_config_component_page(self, sdk_client_fs, app_fs, create_community_cluster):
        """Test pagination on cluster/{}/group_config page"""
        create_few_groups(sdk_client_fs, create_community_cluster)
        group_conf_page = ClusterGroupConfigPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        check_pagination(group_conf_page.table, expected_on_second=1)

    # pylint: disable=too-many-locals, undefined-loop-variable, too-many-statements

    def test_two_fields_on_cluster_config_page(self, sdk_client_fs: ADCMClient, app_fs):
        """Test two different fields on group config page"""

        path = get_data_dir(__file__, 'cluster_with_two_different_fields')
        cluster, *_ = prepare_cluster_and_open_config_page(sdk_client_fs, path, app_fs)
        cluster_group_config = cluster.group_config_create(name="Test group")
        cluster_config_page = ClusterGroupConfigConfig(
            app_fs.driver, app_fs.adcm.url, cluster.id, cluster_group_config.id
        ).open()
        config_rows = cluster_config_page.group_config.get_all_group_config_rows()
        with allure.step("Check that first field is enabled"):
            first_row = config_rows[0]
            assert not cluster_config_page.group_config.is_customization_chbx_disabled(
                first_row
            ), "Checkbox for first field should be enabled"
            cluster_config_page.group_config.click_on_customization_chbx(first_row)
            cluster_config_page.config.check_inputs_enabled(first_row)
        with allure.step("Check that second field is disabled"):
            second_row = config_rows[1]
            assert cluster_config_page.group_config.is_customization_chbx_disabled(
                second_row
            ), "Checkbox for second field should be disabled"
            cluster_config_page.group_config.click_on_customization_chbx(second_row)
            cluster_config_page.config.check_inputs_disabled(second_row)


class TestClusterStatusPage:
    """Tests for the /cluster/{}/status page"""

    one_successful = 'successful 1/1'
    one_negative = 'successful 0/1'

    success_status = [
        StatusRowInfo(True, CLUSTER_NAME, 'successful 2/2', SUCCESS_COLOR, None),
        StatusRowInfo(True, 'Hosts', one_successful, SUCCESS_COLOR, None),
        StatusRowInfo(True, None, None, None, 'test-host'),
        StatusRowInfo(True, 'Services', one_successful, SUCCESS_COLOR, None),
        StatusRowInfo(True, SERVICE_NAME, one_successful, SUCCESS_COLOR, None),
        StatusRowInfo(True, 'first', one_successful, SUCCESS_COLOR, None),
        StatusRowInfo(True, None, None, None, 'test-host'),
    ]
    host_negative_status = [
        StatusRowInfo(False, CLUSTER_NAME, 'successful 1/2', NEGATIVE_COLOR, None),
        StatusRowInfo(False, 'Hosts', one_negative, NEGATIVE_COLOR, None),
        StatusRowInfo(False, None, None, None, 'test-host'),
        StatusRowInfo(True, 'Services', one_successful, SUCCESS_COLOR, None),
        StatusRowInfo(True, SERVICE_NAME, one_successful, SUCCESS_COLOR, None),
        StatusRowInfo(True, 'first', one_successful, SUCCESS_COLOR, None),
        StatusRowInfo(True, None, None, None, 'test-host'),
    ]
    host_and_component_negative_status = [
        StatusRowInfo(False, CLUSTER_NAME, 'successful 0/2', NEGATIVE_COLOR, None),
        StatusRowInfo(False, 'Hosts', one_negative, NEGATIVE_COLOR, None),
        StatusRowInfo(False, None, None, None, 'test-host'),
        StatusRowInfo(False, 'Services', one_negative, NEGATIVE_COLOR, None),
        StatusRowInfo(False, SERVICE_NAME, one_negative, NEGATIVE_COLOR, None),
        StatusRowInfo(False, 'first', one_negative, NEGATIVE_COLOR, None),
        StatusRowInfo(False, None, None, None, 'test-host'),
    ]

    def test_open_by_tab_cluster_status_page(self, app_fs, create_community_cluster):
        """Test open /cluster/{}/config from left menu"""
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        cluster_status_page = cluster_main_page.open_status_tab()
        cluster_status_page.check_all_elements()
        cluster_status_page.check_cluster_toolbar(CLUSTER_NAME)

    def test_status_on_cluster_status_page(
        self, app_fs, adcm_fs, sdk_client_fs, create_community_cluster_with_host_and_service
    ):
        """Changes status on cluster/{}/status page"""
        cluster, host = create_community_cluster_with_host_and_service
        cluster_component = cluster.service(name=SERVICE_NAME).component(name=COMPONENT_NAME)
        cluster.hostcomponent_set((host, cluster_component))
        cluster_status_page = ClusterStatusPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        status_changer = ADCMObjectStatusChanger(sdk_client_fs, adcm_fs)
        with allure.step("Check positive status"):
            status_changer.enable_cluster(cluster)
            cluster_status_page.driver.refresh()
            cluster_status_page.compare_current_and_expected_state(self.success_status)
        with allure.step("Check negative status on host"):
            status_changer.set_host_negative_status(host)
            cluster_status_page.driver.refresh()
            cluster_status_page.compare_current_and_expected_state(self.host_negative_status)
        with allure.step("Check negative status on service"):
            status_changer.set_component_negative_status((host, cluster_component))
            cluster_status_page.driver.refresh()
            cluster_status_page.compare_current_and_expected_state(self.host_and_component_negative_status)
        with allure.step("Check collapse button"):
            with cluster_status_page.wait_rows_collapsed():
                cluster_status_page.click_collapse_all_btn()
            assert len(cluster_status_page.get_all_rows()) == 1, "Status rows should have been collapsed"

    @pytest.mark.xfail(reason="https://arenadata.atlassian.net/browse/ADCM-2636")
    def test_service_passive_status_on_cluster_status_page(
        self, app_fs, adcm_fs, create_host, sdk_client_fs: ADCMClient
    ):
        """Check that service status with monitoring: passive don't break status tree"""

        bundle = cluster_bundle(sdk_client_fs, "service_monitoring_passive")
        cluster = bundle.cluster_create(name=CLUSTER_NAME)
        service = cluster.service_add(name=SERVICE_NAME)
        host = cluster.host_add(create_host)
        cluster.hostcomponent_set((host, service))

        service_status_page = ClusterStatusPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        status_changer = ADCMObjectStatusChanger(sdk_client_fs, adcm_fs)
        with allure.step("Check positive status"):
            status_changer.enable_cluster(cluster)
            service_status_page.driver.refresh()
            service_status_page.compare_current_and_expected_state(self.success_status)
        with allure.step("Check negative status on service"):
            status_changer.set_component_negative_status((host, service.component()))
            service_status_page.driver.refresh()
            service_status_page.compare_current_and_expected_state(self.host_and_component_negative_status)


class TestClusterImportPage:
    """Tests for the /cluster/{}/import page"""

    def test_open_by_tab_cluster_import_page(self, app_fs, create_community_cluster):
        """Test open /cluster/{}/config from left menu"""
        cluster_main_page = ClusterMainPage(app_fs.driver, app_fs.adcm.url, create_community_cluster.id).open()
        import_page = cluster_main_page.open_import_tab()
        import_page.check_all_elements()
        import_page.check_cluster_toolbar(CLUSTER_NAME)

    def test_cluster_import_from_cluster_import_page(self, app_fs, create_import_cluster_with_service):
        """Test cluster import on cluster/{}/import page"""
        params = {"message": "Successfully saved"}
        cluster, _, _, _ = create_import_cluster_with_service
        import_page = ClusterImportPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        import_item = import_page.get_import_items()[0]
        with allure.step("Check import on import page"):
            assert import_page.get_import_item_info(import_item) == ImportItemInfo(
                'Pre-uploaded Dummy cluster to import', 'Pre-uploaded Dummy cluster to import 2.5'
            ), "Text in import item changed"
        import_page.close_info_popup()
        import_page.click_checkbox_in_import_item(import_item)
        import_page.click_save_btn()
        with allure.step("Check that import is saved"):
            assert import_page.get_info_popup_text() == params["message"], "No message about success"
            assert import_page.is_chxb_in_item_checked(import_item), "Checkbox with import should have been checked"

    def test_warning_on_cluster_import_page(self, app_fs, sdk_client_fs):
        """Test import warning !"""

        with allure.step("Create cluster"):
            bundle = cluster_bundle(sdk_client_fs, BUNDLE_WITH_REQUIRED_IMPORT)
            cluster = bundle.cluster_create(name=CLUSTER_NAME)
        import_page = ClusterImportPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
        import_page.config.check_import_warn_icon_on_left_menu()
        import_page.toolbar.check_warn_button(
            tab_name=CLUSTER_NAME,
            expected_warn_text=['Test cluster has an issue with required import'],
        )


class TestClusterRenaming:

    SPECIAL_CHARS = (".", "-", "_")
    DISALLOWED_AT_START_END = (*SPECIAL_CHARS, " ")
    EXPECTED_ERROR = "Please enter a valid name"

    def test_rename_cluster(self, sdk_client_fs, app_fs, create_community_cluster):
        cluster = create_community_cluster
        cluster_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
        self._test_correct_name_can_be_set(cluster, cluster_page)
        self._test_an_error_is_shown_on_incorrect_char_in_name(cluster, cluster_page)
        self._test_an_error_is_not_shown_on_correct_char_in_name(cluster, cluster_page)

    @allure.step("Check settings new correct cluster name")
    def _test_correct_name_can_be_set(self, cluster: Cluster, page: ClusterListPage) -> None:
        new_name = "Hahahah"

        dialog = page.open_rename_cluster_dialog(page.get_row_by_cluster_name(cluster.name))
        dialog.set_new_name(new_name)
        dialog.save()
        with allure.step("Check name of cluster in table"):
            name_in_row = page.get_cluster_info_from_row(0)["name"]
            assert name_in_row == new_name, f"Incorrect cluster name, expected: {new_name}"
            cluster.reread()
            assert cluster.name == new_name, f"Cluster name on backend is incorrect, expected: {new_name}"

    def _test_an_error_is_shown_on_incorrect_char_in_name(self, cluster: Cluster, page: ClusterListPage) -> None:
        dummy_name = "clUster"
        incorrect_names = (
            *[f"{char}{dummy_name}" for char in self.DISALLOWED_AT_START_END],
            *[f"{dummy_name}{char}" for char in self.DISALLOWED_AT_START_END],
            *[f"{dummy_name[0]}{char}{dummy_name[1:]}" for char in ("и", "!")],
        )

        dialog = page.open_rename_cluster_dialog(page.get_row_by_cluster_name(cluster.name))

        for cluster_name in incorrect_names:
            with allure.step(f"Check if printing cluster name '{cluster_name}' triggers a warning message"):
                dialog.set_new_name(dummy_name)
                dialog.set_new_name(cluster_name)
                assert dialog.is_error_message_visible(), "Error about incorrect name should be visible"
                assert dialog.error == self.EXPECTED_ERROR, f"Incorrect error message, expected: {self.EXPECTED_ERROR}"

        dialog.cancel()

    def _test_an_error_is_not_shown_on_correct_char_in_name(self, cluster: Cluster, page: ClusterListPage) -> None:
        dummy_name = "clUster"
        correct_names = (
            *[f"{dummy_name[0]}{char}{dummy_name[1:]}" for char in (*self.DISALLOWED_AT_START_END, "9")],
            f"9{dummy_name}",
        )

        dialog = page.open_rename_cluster_dialog(page.get_row_by_cluster_name(cluster.name))

        for cluster_name in correct_names:
            with allure.step(f"Check if printing cluster name '{cluster_name}' shows no error"):
                dialog.set_new_name(dummy_name)
                dialog.set_new_name(cluster_name)
                assert not dialog.is_error_message_visible(), "Error about correct name should not be shown"
                dialog.save()
                name_in_row = page.get_cluster_info_from_row(0)["name"]
                assert name_in_row == cluster_name, f"Incorrect cluster name, expected: {cluster_name}"
                dialog = page.open_rename_cluster_dialog(page.get_row_by_cluster_name(cluster_name))
