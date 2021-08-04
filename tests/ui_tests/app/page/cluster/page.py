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

from tests.ui_tests.app.page.cluster.locators import (
    ClusterImportLocators,
    ClusterMenuLocators,
    ClusterMainLocators,
    ClusterServicesLocators,
)
from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)
from tests.ui_tests.app.page.common.common_locators import ObjectPageLocators
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.table.locator import CommonTable
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar


class ClusterPageMixin(BasePageObject):
    """Helpers for working with cluster page"""

    # /action /main etc.
    MENU_SUFFIX: str
    cluster_id: int
    header: PageHeader
    footer: PageFooter
    config: CommonConfigMenuObj
    toolbar: CommonToolbar
    table: CommonTableObj

    __ACTIVE_MENU_CLASS = 'active'

    def __init__(self, driver, base_url, cluster_id: int):
        if self.MENU_SUFFIX is None:
            raise AttributeError('You should explicitly set MENU_SUFFIX in class definition')
        super().__init__(driver, base_url, f"/cluster/{cluster_id}/{self.MENU_SUFFIX}")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.cluster_id = cluster_id
        self.toolbar = CommonToolbar(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url)

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


class ClusterMainPage(ClusterPageMixin):
    """Cluster page Main menu"""

    MENU_SUFFIX = 'main'

    def check_all_elements(self):
        self.assert_displayed_elements(
            [
                ObjectPageLocators.title,
                ObjectPageLocators.subtitle,
                ClusterMainLocators.text,
            ]
        )


class ClusterServicesPage(ClusterPageMixin):
    """Cluster page config menu"""

    MENU_SUFFIX = 'service'

    def check_all_elements(self):
        self.assert_displayed_elements(
            [
                ObjectPageLocators.title,
                ObjectPageLocators.subtitle,
                ClusterServicesLocators.add_services_btn,
                CommonTable.header,
                CommonTable.Pagination.next_page,
                CommonTable.Pagination.previous_page,
            ]
        )


class ClusterImportPage(ClusterPageMixin):
    """Cluster page import menu"""

    MENU_SUFFIX = 'import'

    def get_import_items(self):
        return self.find_elements(ClusterImportLocators.import_item_block)


class ClusterConfigPage(ClusterPageMixin):
    """Cluster page config menu"""

    MENU_SUFFIX = 'config'
