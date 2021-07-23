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

from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.common.base_page import BasePageObject, PageHeader, PageFooter
from tests.ui_tests.app.page.common.dialogs import ActionDialog
from tests.ui_tests.app.page.host.locators import HostLocators


class HostPage(BasePageObject):
    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/host")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)

    def get_fqdn(self) -> str:
        return self.find_element(HostLocators.Header.fqdn).text

    def get_bundle_label(self) -> str:
        """Get text from label below FQDN"""
        return self.find_element(HostLocators.Header.provider).text

    def open_main_menu(self):
        self.find_and_click(HostLocators.MenuNavigation.main)

    def open_config_menu(self):
        self.find_and_click(HostLocators.MenuNavigation.config)

    def open_status_menu(self):
        self.find_and_click(HostLocators.MenuNavigation.status)

    def open_action_menu(self):
        self.find_and_click(HostLocators.MenuNavigation.actions)

    def run_action_from_menu(self, action_name: str, open_menu: bool = True):
        if open_menu:
            self.open_action_menu()
        self.find_and_click(HostLocators.Actions.action_btn(action_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)

    def get_action_names(self, open_menu: bool = True) -> Set[str]:
        if open_menu:
            self.open_action_menu()
        return {element.text for element in self.find_elements(HostLocators.Actions.action_name)}

    def active_menu_is(self, menu_locator: Locator) -> bool:
        """
        Check that menu item is active
        :param menu_locator: Menu locator from HostLocators.Menu
        """
        menu_link = self.find_element(menu_locator)
        menu_class = menu_link.get_property("class")
        return 'active' in menu_class
