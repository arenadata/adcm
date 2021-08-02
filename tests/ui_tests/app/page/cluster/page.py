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
import allure

from tests.ui_tests.app.page.cluster.locators import (
    ClusterImportLocators,
    ClusterMenuLocators,
    ClusterMainLocators,
)
from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)


class ClusterMenu(BasePageObject):
    def __init__(self, driver, base_url):
        super().__init__(driver, base_url)

    def open_main_tab(self):
        self.find_and_click(ClusterMenuLocators.main_tab)

    def open_services_tab(self):
        self.find_and_click(ClusterMenuLocators.services_tab)

    def open_hosts_tab(self):
        self.find_and_click(ClusterMenuLocators.hosts_tab)

    def open_components_tab(self):
        self.find_and_click(ClusterMenuLocators.components_tab)

    def open_config_tab(self):
        self.find_and_click(ClusterMenuLocators.config_tab)

    def open_status_tab(self):
        self.find_and_click(ClusterMenuLocators.status_tab)

    def open_import_tab(self):
        self.find_and_click(ClusterMenuLocators.import_tab)

    def open_actions_tab(self):
        self.find_and_click(ClusterMenuLocators.actions_tab)


class ClusterMainPage(BasePageObject):
    def __init__(self, driver, base_url, path):
        super().__init__(driver, base_url, f"/cluster/{path}/main")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)

    @allure.step("Check all elements are displayed")
    def check_all_elements(self):
        self.assert_displayed_elements(
            [ClusterMainLocators.title, ClusterMainLocators.bundle_link, ClusterMainLocators.text]
        )


class ClusterImportPage(BasePageObject):
    def __init__(self, driver, base_url, path):
        super().__init__(driver, base_url, f"/cluster/{path}/import")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)

    def get_import_items(self):
        return self.find_elements(ClusterImportLocators.import_item_block)


class ClusterConfigPage(BasePageObject):
    def __init__(self, driver, base_url, path):
        super().__init__(driver, base_url, f"/cluster/{path}/config")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
