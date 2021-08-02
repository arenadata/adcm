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
from typing import Set

import allure

from adcm_pytest_plugin.utils import wait_until_step_succeeds

from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.common.base_page import BasePageObject, PageHeader, PageFooter
from tests.ui_tests.app.page.common.common_locators import ObjectPageLocators
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.dialogs import ActionDialog
from tests.ui_tests.app.page.host.locators import HostLocators, HostActionsLocators


class HostPageMixin(BasePageObject):
    """Helpers for working with host page"""

    # /action /main etc.
    MENU_SUFFIX: str
    host_id: int
    header: PageHeader
    footer: PageFooter
    config: CommonConfigMenuObj

    __ACTIVE_MENU_CLASS = 'active'

    def __init__(self, driver, base_url, host_id: int):
        if self.MENU_SUFFIX is None:
            raise AttributeError('You should explicitly set MENU_SUFFIX in class definition')
        super().__init__(driver, base_url, f"/host/{host_id}/{self.MENU_SUFFIX}")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.host_id = host_id

    @allure.step('Check FQDN is equal to {fqdn}')
    def check_fqdn_equal_to(self, fqdn: str):
        """Check if fqdn on page is equal to given one"""

        def check(element):
            real_fqdn = element.text
            assert real_fqdn == fqdn, f'Expected FQDN is {fqdn}, but FQDN in menu is {real_fqdn}'

        fqdn_element = self.find_element(ObjectPageLocators.title)
        wait_until_step_succeeds(check, timeout=5, period=0.1, element=fqdn_element)

    def get_bundle_label(self) -> str:
        """Get text from label below FQDN"""
        return self.find_element(ObjectPageLocators.subtitle).text

    @allure.step('Open "Main" menu')
    def open_main_menu(self) -> 'HostMainPage':
        self.find_and_click(HostLocators.MenuNavigation.main)
        page = HostMainPage(self.driver, self.base_url, self.host_id)
        page.wait_page_is_opened()
        return page

    @allure.step('Open "Configuration" menu')
    def open_config_menu(self) -> 'HostConfigPage':
        self.find_and_click(HostLocators.MenuNavigation.config)
        page = HostConfigPage(self.driver, self.base_url, self.host_id)
        page.wait_page_is_opened()
        return page

    @allure.step('Open "Status" menu')
    def open_status_menu(self) -> 'HostStatusPage':
        self.find_and_click(HostLocators.MenuNavigation.status)
        page = HostStatusPage(self.driver, self.base_url, self.host_id)
        page.wait_page_is_opened()
        return page

    @allure.step('Open "Actions" menu')
    def open_action_menu(self) -> 'HostActionsPage':
        self.find_and_click(HostLocators.MenuNavigation.actions)
        page = HostActionsPage(self.driver, self.base_url, self.host_id)
        page.wait_page_is_opened()
        return page

    def active_menu_is(self, menu_locator: Locator) -> bool:
        """
        Check that menu item is active
        :param menu_locator: Menu locator from HostLocators.Menu
        """
        menu_link = self.find_element(menu_locator)
        menu_class = menu_link.get_attribute("class")
        return self.__ACTIVE_MENU_CLASS in menu_class


class HostMainPage(HostPageMixin):
    """Host page Main menu"""

    MENU_SUFFIX = 'main'


class HostConfigPage(HostPageMixin):
    """Host page config menu"""

    MENU_SUFFIX = 'config'


class HostStatusPage(HostPageMixin):
    """Host page status menu"""

    MENU_SUFFIX = 'status'


class HostActionsPage(HostPageMixin):
    """Host page actions page"""

    MENU_SUFFIX = 'action'

    def get_action_names(self) -> Set[str]:
        return {element.text for element in self.find_elements(HostActionsLocators.action_name)}

    def run_action_from_menu(self, action_name: str):
        self.find_and_click(HostActionsLocators.action_btn(action_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)
