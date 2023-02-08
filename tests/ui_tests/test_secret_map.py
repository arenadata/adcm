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

"""Test designed to check field secret map in config page"""

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Component, Service
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_component_action_and_assert_result,
    run_service_action_and_assert_result,
)
from adcm_pytest_plugin.utils import get_data_dir

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.cluster.page import ClusterConfigPage
from tests.ui_tests.app.page.component.page import ComponentConfigPage
from tests.ui_tests.app.page.service.page import ServiceConfigPage

ROW_NAME = "secret_map"
ACTION = "action"
PARAMS = {
    "first_key": "first_test_key",
    "first_value": "first_test_value",
    "second_key": "second_test_key",
    "second_value": "second_test_value",
    "action_key": "key_secret",
    "expected_value": "********",
}


@pytest.fixture(name="secret_map_cluster_objects")
def prepared_cluster_objects(sdk_client_fs: ADCMClient) -> [Cluster, Service, Component]:
    """Upload cluster bundle and create cluster"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
    cluster = bundle.cluster_create(name="secret_config")
    service = cluster.service_add(name="test_service")
    component = service.component(name="first_component")
    return cluster, service, component


class TestSecretMap:
    """Test to check secret map in ui interface"""

    client: ADCMTest
    pytestmark = [pytest.mark.usefixtures("_init")]

    @pytest.fixture()
    def _init(self, app_fs, secret_map_cluster_objects):
        self.client = app_fs

    def _prepare_adcm_objects(self, cluster: Cluster, service: Service, component: Component):
        for config_page in [
            ClusterConfigPage(self.client.driver, self.client.adcm.url, cluster.id),
            ServiceConfigPage(self.client.driver, self.client.adcm.url, cluster.id, service.id),
            ComponentConfigPage(
                self.client.driver, self.client.adcm.url, cluster.id, service.id, component.component_id
            ),
        ]:
            config_page.open()
            _fill_secret_map_by_config(page=config_page, values=[PARAMS["first_key"], PARAMS["first_value"]])

    @pytest.mark.parametrize("obj_to_pick", [Cluster, Service, Component])
    @pytest.mark.usefixtures("_login_to_adcm_over_api")
    def test_secret_map_cluster(self, app_fs, secret_map_cluster_objects, generic_provider, obj_to_pick):
        """Test to check secret map field in ui for cluster"""
        cluster, service, component = secret_map_cluster_objects
        cluster.host_add(generic_provider.host_create("testhost"))
        self._prepare_adcm_objects(cluster, service, component)

        if obj_to_pick == Cluster:
            obj_page = ClusterConfigPage(self.client.driver, self.client.adcm.url, cluster.id).open()
            run_cluster_action_and_assert_result(cluster=cluster, action=ACTION)
        elif obj_to_pick == Service:
            obj_page = ServiceConfigPage(self.client.driver, self.client.adcm.url, cluster.id, service.id).open()
            run_service_action_and_assert_result(service=service, action=ACTION)
        else:
            obj_page = ComponentConfigPage(
                self.client.driver,
                self.client.adcm.url,
                cluster.id,
                service.service_id,
                component.component_id,
            ).open()
            run_component_action_and_assert_result(component=component, action=ACTION)

        with allure.step("Checks config filled by action"):
            obj_page.driver.refresh()
            obj_page.config.assert_map_value_is(
                expected_value={"key_secret": PARAMS["expected_value"]}, display_name=ROW_NAME
            )
        with allure.step("Add second secret map using config form"):
            row = obj_page.config.get_config_row(ROW_NAME)
            obj_page.config.clear_secret(row)
            _fill_secret_map_by_config(
                page=obj_page,
                values=[PARAMS["first_key"], PARAMS["first_value"], PARAMS["second_key"], PARAMS["second_value"]],
            )
        with allure.step("Checks config"):
            obj_page.config.assert_map_value_is(
                expected_value={
                    PARAMS["first_key"]: PARAMS["expected_value"],
                    PARAMS["second_key"]: PARAMS["expected_value"],
                },
                display_name=ROW_NAME,
            )

        with allure.step("Clear all secret map fields in config"):
            obj_page.config.clear_secret(obj_page.config.get_config_row(ROW_NAME))
            obj_page.config.assert_map_value_is(
                expected_value={},
                display_name=ROW_NAME,
            )


@allure.step("Fill secret map using config page")
def _fill_secret_map_by_config(page: ClusterConfigPage, values: list) -> None:
    config_row = page.config.get_config_row(ROW_NAME)
    page.config.click_add_item_btn_in_row(config_row)
    assert page.config.is_save_btn_disabled(), "Save button should be disabled"
    page.config.type_in_field_with_few_inputs(row=config_row, values=values, clear=True)
    page.config.save_config()
