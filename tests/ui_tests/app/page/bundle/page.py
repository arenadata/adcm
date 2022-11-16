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

"""Bundle page PageObjects classes"""

import allure
from tests.ui_tests.app.page.bundle.locators import (
    BundleLocators,
    BundleMainMenuLocators,
)
from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageFooter,
    PageHeader,
)
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar


class BundlePage(BasePageObject):
    """Helpers for working with bundle page"""

    bundle_id: int
    header: PageHeader
    footer: PageFooter
    config: CommonConfigMenuObj
    toolbar: CommonToolbar

    def __init__(self, driver, base_url, bundle_id: int):
        super().__init__(driver, base_url, "/bundle/{bundle_id}/main", bundle_id=bundle_id)
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.bundle_id = bundle_id
        self.toolbar = CommonToolbar(self.driver, self.base_url)

    @allure.step('Click on the "Main" menu item')
    def open_main_menu(self) -> 'BundlePage':
        """Click on the 'Main' menu item"""
        self.find_and_click(BundleLocators.MenuNavigation.main)
        self.wait_page_is_opened()
        return self

    @allure.step('Check all fields are presented on Main page')
    def check_all_main_menu_fields_are_presented(self):
        """Check all fields on main menu page are presented"""
        self.assert_displayed_elements(
            [
                BundleMainMenuLocators.title,
                BundleMainMenuLocators.subtitle,
                BundleMainMenuLocators.text,
            ]
        )

    def check_bundle_toolbar(self, bundle_name: str):
        self.toolbar.check_toolbar_elements(["BUNDLES", bundle_name])
