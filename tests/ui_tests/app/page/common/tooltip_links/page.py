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

"""Tooltip page PageObjects classes"""

import allure

from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.dialogs.locators import ActionDialog
from tests.ui_tests.app.page.common.tooltip_links.locator import CommonToolbarLocators


class CommonToolbar(BasePageObject):
    """Common Toolbar class"""

    def __init__(self, driver, base_url):
        super().__init__(driver, base_url)

    @allure.step("Click on admin link")
    def click_admin_link(self):
        """Click on admin link"""
        self.wait_element_hide(CommonToolbarLocators.progress_bar)
        self.wait_element_visible(CommonToolbarLocators.admin_link).click()

    @allure.step("Click on link {link_name}")
    def click_link_by_name(self, link_name: str):
        """Click on link by name"""
        self.wait_element_hide(CommonToolbarLocators.progress_bar)
        self.wait_element_visible(CommonToolbarLocators.admin_link)
        self.find_and_click(CommonToolbarLocators.text_link(link_name.upper().strip("_")))

    @allure.step("Run action {action_name} in {tab_name}")
    def run_action(self, tab_name: str, action_name: str):
        """Run Action from toolbar"""
        self.wait_element_visible(CommonToolbarLocators.admin_link)
        self.find_and_click(CommonToolbarLocators.action_btn(tab_name.upper().strip("_")))
        self.wait_element_visible(CommonToolbarLocators.Popup.popup_block)
        self.find_and_click(CommonToolbarLocators.Popup.item(action_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)
        self.wait_element_hide(ActionDialog.body)

    @allure.step("Check action {action_name} in ADCM tab is inactive")
    def is_adcm_action_inactive(self, action_name: str):
        """Check Action from toolbar"""

        self.wait_element_visible(CommonToolbarLocators.admin_link)
        self.find_and_click(CommonToolbarLocators.adcm_action_btn)
        is_active = (
            self.wait_element_visible(CommonToolbarLocators.Popup.item(action_name)).get_attribute('disabled') == "true"
        )
        self.find_and_click(CommonToolbarLocators.adcm_action_btn, is_js=True)
        return is_active

    @allure.step("Run action {action_name} in ADCM tab")
    def run_adcm_action(self, action_name: str):
        """Run Action from toolbar"""

        self.wait_element_visible(CommonToolbarLocators.admin_link)
        self.find_and_click(CommonToolbarLocators.adcm_action_btn)
        self.wait_element_visible(CommonToolbarLocators.Popup.popup_block)
        self.wait_element_clickable(CommonToolbarLocators.Popup.item(action_name)).click()
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)
        self.wait_element_hide(ActionDialog.body)

    @allure.step("Run upgrade {upgrade_name} in {tab_name}")
    def run_upgrade(self, tab_name: str, upgrade_name: str):
        """Run Upgrade from toolbar"""
        self.wait_element_visible(CommonToolbarLocators.admin_link)
        self.find_and_click(CommonToolbarLocators.upgrade_btn(tab_name.upper().strip("_")))
        self.wait_element_visible(CommonToolbarLocators.Popup.popup_block)
        self.find_and_click(CommonToolbarLocators.Popup.item(upgrade_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)
        self.wait_element_hide(ActionDialog.body)

    @allure.step("Click warn button in {tab_name}")
    def check_warn_button(self, tab_name: str, expected_warn_text: list):
        """Click warn button from toolbar"""
        self.wait_element_visible(CommonToolbarLocators.admin_link)
        self.find_and_click(CommonToolbarLocators.warn_btn(tab_name.upper().strip("_")))
        self.wait_element_visible(CommonToolbarLocators.WarnPopup.popup_block)
        warn_text_popup = [item.text for item in self.find_elements(CommonToolbarLocators.WarnPopup.item)]
        assert (
            expected_warn_text == warn_text_popup
        ), f"Expected warning is {expected_warn_text}, but actual is {warn_text_popup}"

    @allure.step("Check no warn button in {tab_name}")
    def check_no_warn_button(self, tab_name: str):
        """Check there are no warn button from toolbar"""
        self.wait_element_visible(CommonToolbarLocators.admin_link)
        self.check_element_should_be_hidden(CommonToolbarLocators.warn_btn(tab_name.upper().strip("_")), timeout=3)

    def check_toolbar_elements(self, tab_names: [str]):
        self.assert_displayed_elements([CommonToolbarLocators.admin_link])
        tab_names_upper = [tab_name.upper().strip("_") for tab_name in tab_names]

        for tab_name in tab_names_upper:
            self.assert_displayed_elements([CommonToolbarLocators.text_link(tab_name)])

        tab_names_actual = (
            self.find_element(CommonToolbarLocators.all_links)
            .text.replace("\n", "")
            .replace("play_circle_outline", "")  # delete all extra text from toolbar
            .replace("sync_problem", "")
            .replace("priority_hight", "")
        )
        tab_names_expected = 'apps / ' + ' / '.join(tab_names_upper)
        assert (
            tab_names_actual == tab_names_expected
        ), f'Expected tab names: "{tab_names_expected}", but was "{tab_names_actual}'
