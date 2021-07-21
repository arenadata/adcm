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
from tests.ui_tests.app.page.common.base_page import BasePageObject, PageHeader, PageFooter
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
        self.find_and_click(HostLocators.Menu.main)

    def open_config_menu(self):
        self.find_and_click(HostLocators.Menu.config)

    def open_status_menu(self):
        self.find_and_click(HostLocators.Menu.status)

    def open_action_menu(self):
        self.find_and_click(HostLocators.Menu.actions)
