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
from typing import Tuple, Type

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
from tests.ui_tests.app.page.common.configuration.page import (
    GroupRow,
    PasswordRow,
    SecretMapRow,
    SecretTextRow,
)
from tests.ui_tests.app.page.component.page import ComponentConfigPage
from tests.ui_tests.app.page.service.page import ServiceConfigPage


@pytest.fixture(name="secret_map_cluster_objects")
def prepared_cluster_objects(sdk_client_fs: ADCMClient) -> Tuple[Cluster, Service, Component]:
    """Upload cluster bundle and create cluster"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "secret"))
    cluster = bundle.cluster_create(name="secret_config")
    service = cluster.service_add(name="test_service")
    component = service.component(name="first_component")
    return cluster, service, component


@pytest.fixture(name="secret_map_default")
def prepared_cluster_objects_default(sdk_client_fs: ADCMClient) -> [Cluster, Service, Component]:
    """Upload cluster bundle and create cluster"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "secrets_default"))
    cluster = bundle.cluster_create(name="secret_config_default")
    service = cluster.service_add(name="test_service")
    component = service.component(name="first_component")
    return cluster, service, component


@pytest.fixture(name="secret_file")
def prepared_cluster_objects_secret_file(sdk_client_fs: ADCMClient) -> [Cluster, Service, Component]:
    """Upload cluster bundle and create cluster"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "secret_file"))
    cluster = bundle.cluster_create(name="secret_config_default")
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

    @staticmethod
    def _run_object_action(
        adcm_object: Type[Cluster | Service | Component], action_name: str, cluster, service, component
    ):
        if adcm_object == Cluster:
            run_cluster_action_and_assert_result(cluster, action_name)
        elif adcm_object == Service:
            run_service_action_and_assert_result(service, action_name)
        else:
            run_component_action_and_assert_result(component, action_name)

    def _open_object_page(
        self, adcm_object: Type[Cluster | Service | Component], cluster, service, component
    ) -> ClusterConfigPage | ServiceConfigPage | ComponentConfigPage:
        if adcm_object == Cluster:
            config_page = ClusterConfigPage(self.client.driver, self.client.adcm.url, cluster.id).open()
        elif adcm_object == Service:
            config_page = ServiceConfigPage(self.client.driver, self.client.adcm.url, cluster.id, service.id).open()
        else:
            config_page = ComponentConfigPage(
                self.client.driver,
                self.client.adcm.url,
                cluster.id,
                service.service_id,
                component.component_id,
            ).open()
        return config_page

    @staticmethod
    def _check_group_rows_read_only(config_page: ClusterConfigPage | ServiceConfigPage | ComponentConfigPage):
        groups = config_page.config.get_row(name="group", like=GroupRow)
        assert groups.get_row(
            name="secretmap", like=SecretMapRow
        ).read_only, "Group element secretmap must be read_only"
        assert groups.get_row(name="password", like=PasswordRow).read_only, "Group element password must be read_only"
        assert groups.get_row(
            name="secrettext", like=SecretTextRow
        ).read_only, "Group element secrettext must be read_only"
        assert groups.get_row(
            name="secretfile", like=SecretTextRow
        ).read_only, "Group element secretfile must be read_only"

    @pytest.mark.parametrize("obj_to_pick", [Cluster, Service, Component])
    @pytest.mark.usefixtures("_login_to_adcm_over_api")
    def test_secrets_ui(self, app_fs, secret_map_cluster_objects, generic_provider, obj_to_pick):
        cluster, service, component = secret_map_cluster_objects
        cluster.host_add(generic_provider.host_create("testhost"))
        config_page = self._open_object_page(obj_to_pick, cluster, service, component)

        with allure.step("Change config via ui"):
            secretmap_row = config_page.config.get_row(name="secretmap", like=SecretMapRow)
            secretmap_row.add_item()
            secretmap_row.fill({"first_key": "first_value"})

            password_row = config_page.config.get_row(name="password", like=PasswordRow)
            password_row.fill(value="first_pswd")

            secrettext_row = config_page.config.get_row(name="secrettext", like=SecretTextRow)
            secrettext_row.fill("first text")

            secretfile_row = config_page.config.get_row(name="secretfile", like=SecretTextRow)
            secretfile_row.fill("content")

            save_button = config_page.config.get_save_button()
            assert not save_button.is_disabled(), "save btn must be active"
            save_button.click()

            self._run_object_action(obj_to_pick, "check_after_1", cluster, service, component)

        with allure.step("Change non secret row in config via ui"):
            string_row = config_page.config.get_row(name="string")
            string_row.clear()
            string_row.fill("changed_string")

            save_button.click()
            self._run_object_action(obj_to_pick, "check_after_1", cluster, service, component)

        with allure.step("Change secret rows in config via ui"):
            secretmap_row = config_page.config.get_row(name="secretmap", like=SecretMapRow)
            secretmap_row.clear()
            secretmap_row.add_item()
            secretmap_row.fill({"first_key": "second_value"})

            password_row.clear()
            password_row.fill("second_pswd")

            secrettext_row.fill("second text")

            secretfile_row.fill("Changed content")

            save_button.click()

            self._run_object_action(obj_to_pick, "check_after_2", cluster, service, component)

        with allure.step("Check that secrets in group"):
            self._check_group_rows_read_only(config_page=config_page)

        with allure.step("Check secrets values"):
            assert secretmap_row.get_value() == {
                "first_key": "********"
            }, f"Expected value was 'first_key': '********' but presented is {secretmap_row.get_value()}"
            assert (
                password_row.get_value() == "second_pswd"
            ), f"Expected value was 'password' but presented is {password_row.get_value()}"
            assert (
                secrettext_row.get_value() == "********"
            ), f"Expected value was '********' but presented is {secrettext_row.get_value()}"
            assert (
                secretfile_row.get_value() == "********"
            ), f"Expected value was '********' but presented is {secretfile_row.get_value()}"

    @pytest.mark.parametrize("obj_to_pick", [Cluster, Service, Component])
    @pytest.mark.usefixtures("_login_to_adcm_over_api")
    def test_secrets_ui_default(self, app_fs, secret_map_default, generic_provider, obj_to_pick):
        cluster, service, component = secret_map_default
        cluster.host_add(generic_provider.host_create("testhost"))

        config_page = self._open_object_page(obj_to_pick, cluster, service, component)

        with allure.step("Change config via ui"):
            self._run_object_action(obj_to_pick, "check_after_1", cluster, service, component)

        with allure.step("Change non secret row in config via ui"):
            string_row = config_page.config.get_row(name="string")
            string_row.clear()
            string_row.fill("changed_string")

            save_button = config_page.config.get_save_button()
            assert not save_button.is_disabled(), "save btn must be active"
            save_button.click()

            self._run_object_action(obj_to_pick, "check_after_1", cluster, service, component)

        with allure.step("Change secret rows in config via ui"):
            secretmap_row = config_page.config.get_row(name="secretmap", like=SecretMapRow)
            secretmap_row.clear()
            secretmap_row.add_item()
            secretmap_row.fill({"first_key": "second_value"})

            password_row = config_page.config.get_row(name="password", like=PasswordRow)
            password_row.clear()
            password_row.fill(value="second_pswd")

            secrettext_row = config_page.config.get_row(name="secrettext", like=SecretTextRow)
            secrettext_row.clear()
            secrettext_row.fill("second text")

            secretfile_row = config_page.config.get_row(name="secretfile", like=SecretTextRow)
            secretfile_row.clear()
            secretfile_row.fill("Changed content")

            save_button.click()

            self._run_object_action(obj_to_pick, "check_after_2", cluster, service, component)

        with allure.step("Check that secrets in group"):
            self._check_group_rows_read_only(config_page=config_page)

        with allure.step("Check secrets values"):
            assert secretmap_row.get_value() == {
                "first_key": "********"
            }, f"Expected value was 'first_key': '********' but presented is {secretmap_row.get_value()}"
            assert (
                password_row.get_value() == "second_pswd"
            ), f"Expected value was 'password' but presented is {password_row.get_value()}"
            assert (
                secrettext_row.get_value() == "********"
            ), f"Expected value was '********' but presented is {secrettext_row.get_value()}"
            assert (
                secretfile_row.get_value() == "********"
            ), f"Expected value was '********' but presented is {secretfile_row.get_value()}"
