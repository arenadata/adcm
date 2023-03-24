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

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebElement

from tests.ui_tests.app.page.cluster_list.locators import ClusterListLocators
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.concerns import ConcernPopover
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.dialogs.create_host_locators import (
    HostCreationLocators,
    ListConcernPopupLocators,
)
from tests.ui_tests.app.page.common.dialogs.locators import (
    ActionDialog,
    DeleteDialogLocators,
    ServiceLicenseDialog,
)
from tests.ui_tests.app.page.common.dialogs.rename import RenameDialog
from tests.ui_tests.app.page.common.dialogs.service_license import ServiceLicenseModal
from tests.ui_tests.app.page.common.host_components.locators import (
    HostComponentsLocators,
)
from tests.ui_tests.app.page.common.host_components.page import HostComponentsPage
from tests.ui_tests.app.page.common.table.page import CommonTableObj


class ClusterListPage(BasePageObject):  # pylint: disable=too-many-public-methods
    """Cluster List Page class"""

    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/cluster")
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.table = CommonTableObj(driver=self.driver, locators_class=ClusterListLocators.ClusterTable)

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
        name_locator = self.table.locators.ClusterRow.name
        suitable_row = next(
            filter(
                # if there's an "edit" icon, it's "text" will be a part of "cluster's name text", separated by "\n"
                # and since cluster can't have "\n" in name, we consider everything before a cluster's name
                lambda row: self.find_child(row, name_locator).text.split("\n", maxsplit=1)[0] == cluster_name,
                self.table.get_all_rows(),
            ),
            None,
        )

        if suitable_row:
            return suitable_row

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
        self.wait_element_visible(DeleteDialogLocators.body)
        self.find_and_click(DeleteDialogLocators.yes)
        self.wait_element_hide(DeleteDialogLocators.body)

    @allure.step("Open cluster rename dialog by clicking on cluster rename button")
    def open_rename_cluster_dialog(self, row: WebElement) -> RenameDialog:
        self.hover_element(row)
        self.find_child(row, self.table.locators.ClusterRow.rename_btn).click()
        return RenameDialog.wait_opened(driver=self.driver)

    @allure.step("Run upgrade {upgrade_name} for cluster from row")
    def run_upgrade_with_service_license(self, row: WebElement, upgrade_name: str) -> None:
        self.find_child(row, self.table.locators.ClusterRow.upgrade).click()
        self.wait_element_visible(self.table.locators.UpgradePopup.block)
        self.find_and_click(self.table.locators.UpgradePopup.button(upgrade_name))

    @allure.step("Get service license dialog header")
    def get_service_license_dialog_header(self) -> str:
        return self.find_element(ServiceLicenseDialog.block_header).text

    @allure.step("Get service license dialog")
    def get_service_license_dialog(self) -> ServiceLicenseModal:
        self.wait_element_visible(ServiceLicenseDialog.block)
        license_dialog = self.find_element(ServiceLicenseDialog.block)
        return ServiceLicenseModal(driver=self.driver, element=license_dialog)

    @allure.step("Confirm upgrade")
    def confirm_upgrade(self) -> None:
        self.wait_element_visible(ActionDialog.run)
        self.find_and_click(ActionDialog.run)

    @allure.step("Cancel upgrade")
    def cancel_upgrade(self) -> None:
        self.wait_element_visible(ActionDialog.cancel)
        self.find_and_click(ActionDialog.cancel)

    @allure.step("Do upgrade {upgrade_name} for cluster from row")
    def run_upgrade_in_cluster_row(
        self,
        row: WebElement,
        upgrade_name: str,
        config: dict | None = None,
        hc_acl: bool = False,
        is_new_host: bool = False,
        disclaimer_text: str | None = None,
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
                    row=self.config.get_config_row(display_name=key),
                    values=[value],
                )
            if self.is_element_displayed(ActionDialog.next_btn):
                self.find_and_click(ActionDialog.next_btn)
        if hc_acl:
            if is_new_host:
                components_page = HostComponentsPage(self.driver, self.base_url)
                dialog = components_page.click_add_host_btn()
                dialog.create_host("Test_host")
                self.wait_element_hide(HostCreationLocators.block)
            for comp_row in self.find_elements(HostComponentsLocators.component_row):
                comp_row_name = self.find_child(comp_row, HostComponentsLocators.Row.name)
                self.wait_element_visible(comp_row_name)
                comp_row_name.click()
            self.find_child(
                self.find_elements(HostComponentsLocators.host_row)[0],
                HostComponentsLocators.Row.name,
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

    @allure.step("Hover concern button in row")
    def hover_concern_button(self, row: WebElement) -> ConcernPopover:
        self.hover_element(self.find_child(row, self.table.locators.ClusterRow.actions))
        return ConcernPopover.wait_opened(self)

    def hover_name(self, row: WebElement):
        self.hover_element(self.find_child(row, self.table.locators.ClusterRow.name))
