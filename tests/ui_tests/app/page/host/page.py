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

"""Host page PageObjects classes"""


import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds

from tests.ui_tests.app.page.common.base_page import BaseDetailedPage, BasePageObject
from tests.ui_tests.app.page.common.common_locators import ObjectPageLocators
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.status.page import StatusPage
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar
from tests.ui_tests.app.page.host.locators import HostLocators
from tests.ui_tests.core.checks import check_elements_are_displayed
from tests.ui_tests.core.locators import BaseLocator


class HostPageMixin(BasePageObject):
    """Helpers for working with host page"""

    # /action /main etc.
    MENU_SUFFIX: str
    MAIN_ELEMENTS: list
    host_id: int
    cluster_id: int
    config: CommonConfigMenuObj
    toolbar: CommonToolbar
    __ACTIVE_MENU_CLASS = "active"

    def __init__(self, driver, base_url, host_id: int, cluster_id: int | None = None):
        if self.MENU_SUFFIX is None:
            raise AttributeError("You should explicitly set MENU_SUFFIX in class definition")
        super().__init__(
            driver,
            base_url,
            "/cluster/{cluster_id}/host/{host_id}/" + self.MENU_SUFFIX
            if cluster_id
            else "/host/{host_id}/" + self.MENU_SUFFIX,
            cluster_id=cluster_id,
            host_id=host_id,
        )
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.host_id = host_id
        self.toolbar = CommonToolbar(self.driver, self.base_url)

    @allure.step("Check FQDN is equal to {fqdn}")
    def check_fqdn_equal_to(self, fqdn: str):
        """Check if fqdn on page is equal to given one"""

        def _check(element):
            real_fqdn = element.text
            assert real_fqdn == fqdn, f"Expected FQDN is {fqdn}, but FQDN in menu is {real_fqdn}"

        fqdn_element = self.find_element(ObjectPageLocators.title)
        wait_until_step_succeeds(_check, timeout=5, period=0.1, element=fqdn_element)

    def get_bundle_label(self) -> str:
        """Get text from label below FQDN"""
        return self.find_element(ObjectPageLocators.subtitle).text

    @allure.step('Open "Main" menu')
    def open_main_tab(self) -> "HostMainPage":
        """Open 'Main' menu"""
        self.find_and_click(HostLocators.MenuNavigation.main_tab)
        page = HostMainPage(self.driver, self.base_url, self.host_id, None)
        page.wait_page_is_opened()
        return page

    @allure.step('Open "Configuration" menu')
    def open_config_tab(self) -> "HostConfigPage":
        """Open 'Configuration' menu"""
        self.find_and_click(HostLocators.MenuNavigation.config_tab)
        page = HostConfigPage(self.driver, self.base_url, self.host_id, None)
        page.wait_page_is_opened()
        return page

    @allure.step('Open "Status" menu')
    def open_status_tab(self) -> "HostStatusPage":
        """Open 'Status' menu"""
        self.find_and_click(HostLocators.MenuNavigation.status_tab)
        page = HostStatusPage(self.driver, self.base_url, self.host_id, None)
        page.wait_page_is_opened()
        return page

    def active_menu_is(self, menu_locator: BaseLocator) -> bool:
        """
        Check that menu item is active
        :param menu_locator: Menu locator from HostLocators.Menu
        """
        menu_link = self.find_element(menu_locator)
        menu_class = menu_link.get_attribute("class")
        return self.__ACTIVE_MENU_CLASS in menu_class

    @allure.step("Assert that all main elements on the page are presented")
    def check_all_elements(self):
        check_elements_are_displayed(self, self.MAIN_ELEMENTS)

    def check_host_toolbar(self, host_name: str):
        self.toolbar.check_toolbar_elements(["HOSTS", host_name])


class HostMainPage(HostPageMixin, BaseDetailedPage):
    """Host page Main menu"""

    MENU_SUFFIX = "main"
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
    ]


class HostConfigPage(HostPageMixin):
    """Host page config menu"""

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


class HostStatusPage(HostPageMixin, StatusPage):
    """Host page status menu"""

    MENU_SUFFIX = "status"
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
    ]
