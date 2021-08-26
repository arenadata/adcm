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
from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar
from tests.ui_tests.app.page.service.locators import ServiceImportLocators


class ServicePageMixin(BasePageObject):
    """Helpers for working with service page"""

    # /action /main etc.
    MENU_SUFFIX: str
    cluster_id: int
    service_id: int
    header: PageHeader
    footer: PageFooter
    config: CommonConfigMenuObj
    toolbar: CommonToolbar
    table: CommonTableObj

    __ACTIVE_MENU_CLASS = 'active'

    def __init__(self, driver, base_url, cluster_id: int, service_id: int):
        if self.MENU_SUFFIX is None:
            raise AttributeError('You should explicitly set MENU_SUFFIX in class definition')
        super().__init__(
            driver,
            base_url,
            "/cluster/{cluster_id}/service/{service_id}/" + self.MENU_SUFFIX,
            cluster_id=cluster_id,
            service_id=service_id,
        )
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.cluster_id = cluster_id
        self.service_id = service_id
        self.toolbar = CommonToolbar(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url)


class ServiceMainPage(ServicePageMixin):
    """Service page Main menu"""

    MENU_SUFFIX = 'main'


class ServiceConfigPage(ServicePageMixin):
    """Service page Main menu"""

    MENU_SUFFIX = 'config'


class ServiceImportPage(ServicePageMixin):
    """Service page Main menu"""

    MENU_SUFFIX = 'import'

    def get_import_items(self):
        return self.find_elements(ServiceImportLocators.import_item_block)
