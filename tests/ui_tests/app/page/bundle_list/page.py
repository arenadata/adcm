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

from dataclasses import dataclass

from tests.ui_tests.app.page.bundle_list.locators import BundleListLocators
from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)
from tests.ui_tests.app.page.common.dialogs import DeleteDialog
from tests.ui_tests.app.page.common.table.page import CommonTableObj


@dataclass
class BundleInfo:
    """Information about bundle from table row"""

    name: str
    version: str
    edition: str
    description: str


class BundleListPage(BasePageObject):
    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/bundle")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url, BundleListLocators.Table)

    def get_bundle_info(self, row_num: int = 0) -> BundleInfo:
        """Get information about bundle from row"""
        row = self.table.get_row(row_num)
        row_elements = BundleListLocators.Table.Row
        return BundleInfo(
            name=self.find_child(row, row_elements.name).text,
            version=self.find_child(row, row_elements.version).text,
            edition=self.find_child(row, row_elements.edition).text,
            description=self.find_child(row, row_elements.description).text,
        )

    @allure.step('Upload bundle from {bundle_path}')
    def upload_bundle(self, bundle_path: str):
        """Upload bundle with 'Upload bundles' button"""
        self.find_element(BundleListLocators.Tooltip.upload_btn).send_keys(bundle_path)

    @allure.step('Remove bundle')
    def delete_bundle(self, row_num: int = 0):
        """Remove bundle by clicking on trash icon in row"""
        row = self.table.get_row(row_num)
        self.find_child(row, BundleListLocators.Table.Row.delete_btn).click()
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)

    @allure.step('Accept licence agreement')
    def accept_licence(self, row_num: int = 0):
        """Accept license"""
        row = self.table.get_row(row_num)
        row_elements = BundleListLocators.Table.Row
        self.find_child(row, row_elements.license_btn).click()
        self.wait_element_visible(BundleListLocators.LicensePopup.block)
        self.find_and_click(BundleListLocators.LicensePopup.agree_btn)
        self.wait_element_hide(BundleListLocators.LicensePopup.block)

    def click_bundle_in_row(self, row_num: int = 0):
        """Click on bundle name"""
        row = self.table.get_row(row_num)
        bundle_name = self.find_child(row, BundleListLocators.Table.Row.name)
        bundle_name.click()
