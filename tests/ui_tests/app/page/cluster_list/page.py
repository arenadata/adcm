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

"""Cluster List page PageObjects classes"""
from contextlib import contextmanager
from typing import Optional

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebElement

from tests.ui_tests.app.page.cluster.locators import ClusterComponentsLocators
from tests.ui_tests.app.page.cluster_list.locators import ClusterListLocators
from tests.ui_tests.app.page.common.base_page import BasePageObject, PageFooter, PageHeader
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.dialogs.locators import ActionDialog, DeleteDialog
from tests.ui_tests.app.page.common.dialogs.rename import RenameDialog
from tests.ui_tests.app.page.common.host_components.page import HostComponentsPage
from tests.ui_tests.app.page.common.popups.locator import HostCreationLocators, ListConcernPopupLocators
from tests.ui_tests.app.page.common.popups.page import HostCreatePopupObj
from tests.ui_tests.app.page.common.table.page import CommonTableObj


class ClusterListPage(BasePageObject):  # pylint: disable=too-many-public-methods
    """Cluster List Page class"""

    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/cluster")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url, ClusterListLocators.ClusterTable)
        self.host_popup = HostCreatePopupObj(self.driver, self.base_url)

    @allure.step("Create cluster")
    def create_cluster(self, bundle: str, description: str = None, is_license: bool = False):
        """Create cluster"""
        self.find_and_click(ClusterListLocators.Tooltip.cluster_add_btn)
        popup = ClusterListLocators.CreateClusterPopup
        self.wait_element_visible(popup.block)
        self.find_element(popup.upload_bundle_btn).send_keys(bundle)
        if description:
            self.send_text_to_element(popup.description_input, description)
        self.find_and_click(popup.create_btn)
        if is_license:
            self.wait_element_visible(ClusterListLocators.LicensePopup.block)
            self.find_and_click(ClusterListLocators.LicensePopup.agree_btn)

    @allure.step("Upload bundle without creating a cluster")
    def upload_bundle_from_cluster_create_popup(self, bundle: str):
        """Upload bundle from cluster list page without creating a cluster"""
        self.find_and_click(ClusterListLocators.Tooltip.cluster_add_btn)
        popup = ClusterListLocators.CreateClusterPopup
        self.wait_element_visible(popup.block)
        self.find_element(popup.upload_bundle_btn).send_keys(bundle)
        self.find_and_click(popup.cancel_btn)
        self.wait_element_hide(popup.block)

    def get_cluster_info_from_row(self, row_pos: int) -> dict:
        """Get Cluster info from Cluster List row"""
        row_elements = ClusterListLocators.ClusterTable.ClusterRow
        cluster_row = self.table.get_all_rows()[row_pos]
        return {
            "name": self.find_child(cluster_row, row_elements.name).text,
            "bundle": self.find_child(cluster_row, row_elements.bundle).text,
            "description": self.find_child(cluster_row, row_elements.description).text,
            "state": self.find_child(cluster_row, row_elements.state).text,
        }

    @allure.step("Click on action button from row")
    def click_action_btn_in_row(self, row: WebElement):
        """Click on Action button from Cluster List row"""
        self.find_child(row, self.table.locators.ClusterRow.actions).click()

    @allure.step("Click on import button from row")
    def click_import_btn_in_row(self, row: WebElement):
        """Click on Import button from Cluster List row"""

        self.find_child(row, self.table.locators.ClusterRow.imports).click()

    @allure.step("Run action {action_name} for cluster from row")
    def run_action_in_cluster_row(self, row: WebElement, action_name: str):
        """Run action for cluster from row"""

        self.click_action_btn_in_row(row)
        self.wait_element_visible(self.table.locators.ActionPopup.block)
        self.find_and_click(self.table.locators.ActionPopup.button(action_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)
        self.wait_element_hide(ActionDialog.body)

    def get_all_actions_name_in_cluster(self, row: WebElement):
        """Get all actions for cluster from row"""

        self.click_action_btn_in_row(row)
        self.wait_element_visible(self.table.locators.ActionPopup.block)
        try:
            actions_names = [
                name.text for name in self.find_elements(self.table.locators.ActionPopup.action_buttons, timeout=2)
            ]
        except TimeoutException:
            actions_names = []
        self.find_and_click(self.table.locators.backdrop, is_js=True)
        self.wait_element_hide(self.table.locators.ActionPopup.block)
        return actions_names

    @contextmanager
    def wait_cluster_state_change(self, row: WebElement):
        """Wait for cluster state to change"""

        state_before = self.get_cluster_state_from_row(row)
        yield

        def _wait_state():
            state_after = self.get_cluster_state_from_row(row)
            assert state_after != state_before
            assert state_after != self.table.LOADING_STATE_TEXT

        wait_until_step_succeeds(_wait_state, period=1, timeout=self.default_loc_timeout)

    def get_cluster_state_from_row(self, row: WebElement):
        """Get Cluster state from row"""
        return self.find_child(row, self.table.locators.ClusterRow.state).text

    @allure.step("Get row by cluster name '{cluster_name}'")
    def get_row_by_cluster_name(self, cluster_name: str) -> WebElement:
        """Get Cluster row by cluster name"""
        rows = self.table.get_all_rows()
        for row in rows:
            if self.find_child(row, self.table.locators.ClusterRow.name).text == cluster_name:
                return row
        raise AssertionError(f"Cluster '{cluster_name}' not found in table rows")

    @allure.step("Click on config button from the row")
    def click_config_button_in_row(self, row: WebElement):
        """Click on Config button from the row"""
        self.find_child(row, self.table.locators.ClusterRow.config).click()

    @allure.step("Click on cluster name from the row")
    def click_cluster_name_in_row(self, row: WebElement):
        """Click on Cluster name from the row"""
        self.find_child(row, self.table.locators.ClusterRow.name).click()

    @allure.step("Delete cluster by button from the row")
    def delete_cluster_by_row(self, row: WebElement):
        """Delete Cluster by button from the row"""
        self.find_child(row, self.table.locators.ClusterRow.delete_btn).click()
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)

    @allure.step("Open cluster rename dialog by clicking on cluster rename button")
    def open_rename_cluster_dialog(self, row: WebElement) -> RenameDialog:
        self.hover_element(row)
        self.find_child(row, self.table.locators.ClusterRow.rename_btn).click()
        dialog = RenameDialog(driver=self.driver, base_url=self.base_url)
        dialog.wait_opened()
        return dialog

    @allure.step("Run upgrade {upgrade_name} for cluster from row")  # pylint: disable-next=too-many-arguments
    def run_upgrade_in_cluster_row(
        self,
        row: WebElement,
        upgrade_name: str,
        config: Optional[dict] = None,
        hc_acl: bool = False,
        is_new_host: bool = False,
        disclaimer_text: Optional[str] = None,
    ):
        """
        Run upgrade for cluster from row

        :param row: row with upgrade
        :param upgrade_name: upgrade action name
        :param config: config options
        :param hc_acl: hc_acl options
        :param is_new_host: condition if new host is needed, new host will be created and added in upgrade popup.
                            only with hc_acl option
        :param disclaimer_text: disclaimer text in first popup
        """

        self.find_child(row, self.table.locators.ClusterRow.upgrade).click()
        self.wait_element_visible(self.table.locators.UpgradePopup.block)
        self.find_and_click(self.table.locators.UpgradePopup.button(upgrade_name))
        self.wait_element_visible(ActionDialog.body)
        if disclaimer_text:
            assert self.find_element(ActionDialog.text).text == disclaimer_text, "Different text in disclaimer dialog"
            self.find_and_click(ActionDialog.run)
            self.wait_element_visible(ActionDialog.body)
        if config:
            for key, value in config.items():
                self.wait_element_visible(CommonConfigMenu.config_row)
                self.config.type_in_field_with_few_inputs(
                    row=self.config.get_config_row(display_name=key), values=[value]
                )
            if self.is_element_displayed(ActionDialog.next_btn):
                self.find_and_click(ActionDialog.next_btn)
        if hc_acl:
            if is_new_host:
                components_page = HostComponentsPage(self.driver, self.base_url)
                components_page.click_add_host_btn()
                self.host_popup.create_host("Test_host")
                self.wait_element_hide(HostCreationLocators.block)
            for comp_row in self.find_elements(ClusterComponentsLocators.component_row):
                comp_row_name = self.find_child(comp_row, ClusterComponentsLocators.Row.name)
                self.wait_element_visible(comp_row_name)
                comp_row_name.click()
            self.find_child(
                self.find_elements(ClusterComponentsLocators.host_row)[0], ClusterComponentsLocators.Row.name
            ).click()
        self.find_and_click(ActionDialog.run)
        self.wait_element_hide(ActionDialog.body)

    @allure.step("Click on cluster concern object name from the row")
    def click_on_concern_by_object_name(self, row: WebElement, concern_object_name: str):
        """Click on Cluster Concern object name from the row"""
        self.hover_element(self.find_child(row, self.table.locators.ClusterRow.actions))
        self.wait_element_visible(ListConcernPopupLocators.block)
        for issue in self.find_elements(ListConcernPopupLocators.link_to_concern_object):
            if concern_object_name in issue.text:
                issue.click()
                return
        raise AssertionError(f"Issue name '{concern_object_name}' not found in row issues")
