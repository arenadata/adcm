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
from contextlib import contextmanager

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.webdriver.remote.webdriver import WebElement

from tests.ui_tests.app.page.cluster_list.locators import ClusterListLocators
from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)
from tests.ui_tests.app.page.common.dialogs import (
    ActionDialog,
    DeleteDialog,
)
from tests.ui_tests.app.page.common.table.page import CommonTableObj


class ClusterListPage(BasePageObject):
    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/cluster")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url, ClusterListLocators.ClusterTable)

    @allure.step("Create cluster from bundle")
    def create_cluster(self, bundle: str, description: str = None, is_license: bool = False):
        self.find_and_click(ClusterListLocators.Tooltip.cluster_add_btn)
        popup = ClusterListLocators.CreateClusterPopup
        self.wait_element_visible(popup.block)
        self.find_element(popup.upload_bundle_btn).send_keys(bundle)
        if description:
            self.find_element(popup.description_input).send_keys(description)
        self.find_and_click(popup.create_btn)
        if is_license:
            self.wait_element_visible(ClusterListLocators.LicensePopup.block)
            self.find_and_click(ClusterListLocators.LicensePopup.agree_btn)

    @allure.step("Get cluster info from row {row}")
    def get_cluster_info_from_row(self, row: int) -> dict:
        row_elements = ClusterListLocators.ClusterTable.ClusterRow
        cluster_row = self.table.get_all_rows()[row]
        return {
            "name": self.find_child(cluster_row, row_elements.name).text,
            "bundle": self.find_child(cluster_row, row_elements.bundle).text,
            "description": self.find_child(cluster_row, row_elements.description).text,
            "state": self.find_child(cluster_row, row_elements.state).text,
        }

    def click_action_btn_in_row(self, row: WebElement):
        self.find_child(row, self.table.table.ClusterRow.actions).click()

    def click_import_btn_in_row(self, row: WebElement):
        self.find_child(row, self.table.table.ClusterRow.imports).click()

    @allure.step("Run action {action_name} for cluster")
    def run_action_in_cluster_row(self, row: WebElement, action_name: str):
        self.click_action_btn_in_row(row)
        self.wait_element_visible(self.table.table.ActionPopup.block)
        self.find_and_click(self.table.table.ActionPopup.button(action_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)

    @contextmanager
    def wait_cluster_state_change(self, row: WebElement):
        state_before = self.get_cluster_state_from_row(row)
        yield

        def wait_state():
            state_after = self.get_cluster_state_from_row(row)
            assert state_after != state_before
            assert state_after != self.table.LOADING_STATE_TEXT

        wait_until_step_succeeds(wait_state, period=1, timeout=self.default_loc_timeout)

    @allure.step("Get cluster state")
    def get_cluster_state_from_row(self, row: WebElement):
        return self.find_child(row, self.table.table.ClusterRow.state).text

    @allure.step("Get row by cluster name '{cluster_name}'")
    def get_row_by_cluster_name(self, cluster_name: str) -> WebElement:
        rows = self.table.get_all_rows()
        for row in rows:
            if self.find_child(row, self.table.table.ClusterRow.name).text == cluster_name:
                return row
        raise AssertionError(f"Cluster '{cluster_name}' not found in table rows")

    def click_config_button_in_row(self, row: WebElement):
        self.find_child(row, self.table.table.ClusterRow.config).click()

    def click_cluster_name_in_row(self, row: WebElement):
        self.find_child(row, self.table.table.ClusterRow.name).click()

    @allure.step("Delete cluster")
    def delete_cluster_by_row(self, row: WebElement):
        self.find_child(row, self.table.table.ClusterRow.delete_btn).click()
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)
