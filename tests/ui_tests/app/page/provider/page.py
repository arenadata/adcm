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
from tests.ui_tests.app.page.common.base_page import BaseDetailedPage, BasePageObject
from tests.ui_tests.app.page.common.common_locators import (
    ObjectPageLocators,
    ObjectPageMenuLocators,
)
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.group_config_list.locators import (
    GroupConfigListLocators,
)
from tests.ui_tests.app.page.common.group_config_list.page import GroupConfigList
from tests.ui_tests.app.page.common.table.locator import CommonTable
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar
from tests.ui_tests.core.checks import check_elements_are_displayed


class ProviderPageMixin(BasePageObject):
    """Helpers for working with provider page"""

    # /main etc.
    MENU_SUFFIX: str
    MAIN_ELEMENTS: list
    provider_id: int
    config: CommonConfigMenuObj
    toolbar: CommonToolbar
    table: CommonTableObj
    group_config = GroupConfigList

    def __init__(self, driver, base_url, provider_id: int):
        if self.MENU_SUFFIX is None:
            raise AttributeError("You should explicitly set MENU_SUFFIX in class definition")
        super().__init__(driver, base_url, "/provider/{provider_id}/" + self.MENU_SUFFIX, provider_id=provider_id)
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.provider_id = provider_id
        self.toolbar = CommonToolbar(self.driver, self.base_url)
        self.table = CommonTableObj(driver=self.driver)
        self.group_config = GroupConfigList(self.driver, self.base_url)

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

    @allure.step("Open Group Configuration tab by menu click")
    def open_group_config_tab(self) -> "ProviderGroupConfigPage":
        """Open Group Configuration tab by menu click"""
        self.find_and_click(ObjectPageMenuLocators.group_config_tab)
        page = ProviderGroupConfigPage(self.driver, self.base_url, self.provider_id)
        page.wait_page_is_opened()
        return page

    @allure.step("Check all main elements on the page are presented")
    def check_all_elements(self):
        check_elements_are_displayed(self, self.MAIN_ELEMENTS)


class ProviderMainPage(ProviderPageMixin, BaseDetailedPage):
    """Provider page Main menu"""

    MENU_SUFFIX = "main"
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
    ]


class ProviderConfigPage(ProviderPageMixin):
    """Provider page Config menu"""

    MENU_SUFFIX = "config"
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


class ProviderGroupConfigPage(ProviderPageMixin):
    """Provider page group config menu"""

    MENU_SUFFIX = "group_config"
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
        GroupConfigListLocators.header_item,
        GroupConfigListLocators.add_btn,
        CommonTable.Pagination.next_page,
        CommonTable.Pagination.previous_page,
    ]
