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

"""Provider page PageObjects classes"""

import allure
from selenium.webdriver.remote.webelement import WebElement

from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)
from tests.ui_tests.app.page.common.common_locators import (
    ObjectPageLocators,
    ObjectPageMenuLocators,
    CommonActionLocators,
)
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.dialogs_locators import (
    ActionDialog,
)
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar


class ProviderPageMixin(BasePageObject):
    """Helpers for working with provider page"""

    # /action /main etc.
    MENU_SUFFIX: str
    MAIN_ELEMENTS: list
    provider_id: int
    header: PageHeader
    footer: PageFooter
    config: CommonConfigMenuObj
    toolbar: CommonToolbar
    table: CommonTableObj

    __ACTIVE_MENU_CLASS = 'active'

    def __init__(self, driver, base_url, provider_id: int):
        if self.MENU_SUFFIX is None:
            raise AttributeError('You should explicitly set MENU_SUFFIX in class definition')
        super().__init__(driver, base_url, "/provider/{provider_id}/" + self.MENU_SUFFIX, provider_id=provider_id)
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.provider_id = provider_id
        self.toolbar = CommonToolbar(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url)

    @allure.step("Open 'Main' tab")
    def open_main_tab(self):
        """Open 'Main' tab"""
        self.find_and_click(ObjectPageMenuLocators.main_tab)
        provider_main_page = ProviderMainPage(self.driver, self.base_url, self.provider_id)
        provider_main_page.wait_page_is_opened()
        return provider_main_page

    @allure.step("Open 'Configuration' tab")
    def open_config_tab(self):
        """Open 'Configuration' tab"""
        self.find_and_click(ObjectPageMenuLocators.config_tab)
        provider_conf_page = ProviderConfigPage(self.driver, self.base_url, self.provider_id)
        provider_conf_page.wait_page_is_opened()
        return provider_conf_page

    @allure.step("Open 'Actions' tab")
    def open_actions_tab(self):
        """Open 'Actions' tab"""
        self.find_and_click(ObjectPageMenuLocators.actions_tab)
        provider_action_page = ProviderActionsPage(self.driver, self.base_url, self.provider_id)
        provider_action_page.wait_page_is_opened()
        return provider_action_page

    @allure.step("Check all main elements on the page are presented")
    def check_all_elements(self):
        """Check all main elements on the page are presented"""
        self.assert_displayed_elements(self.MAIN_ELEMENTS)


class ProviderMainPage(ProviderPageMixin):
    """Provider page Main menu"""

    MENU_SUFFIX = 'main'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
    ]


class ProviderConfigPage(ProviderPageMixin):
    """Provider page Config menu"""

    MENU_SUFFIX = 'config'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
        CommonConfigMenu.description_input,
        CommonConfigMenu.search_input,
        CommonConfigMenu.advanced_label,
        CommonConfigMenu.save_btn,
        CommonConfigMenu.history_btn,
    ]


class ProviderActionsPage(ProviderPageMixin):
    """Provider page Actions menu"""

    MENU_SUFFIX = 'action'

    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        CommonActionLocators.action_card,
    ]

    def get_all_actions(self) -> [WebElement]:
        """Get all actions"""
        return self.find_elements(CommonActionLocators.action_card)

    @allure.step("Run action from actions tab")
    def click_run_btn_in_action(self, action: WebElement):
        """Run action from actions tab"""
        self.find_child(action, CommonActionLocators.ActionCard.play_btn).click()
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)

    @allure.step("Check that action page is empty")
    def check_no_actions_presented(self):
        """Check that action page is empty"""
        assert (
            "Nothing to display." in self.find_element(CommonActionLocators.info_text).text
        ), "There should be message 'Nothing to display'"
