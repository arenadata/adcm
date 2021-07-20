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
from selenium.common.exceptions import (
    TimeoutException,
)

from tests.ui_tests.app.page.cluster_list_page.cluster_list_locators import ClusterListLocators
from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)


class ClusterListPage(BasePageObject):

    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/cluster")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)

    def download_cluster(self, bundle):
        self.find_and_click(ClusterListLocators.Tooltip.cluster_add_btn)
        popup = ClusterListLocators.CreateClusterPopup
        self.wait_element_visible(popup.block)
        self.find_element(popup.upload_bundle_btn).send_keys(bundle)
        self.find_and_click(popup.create_btn)

    def get_all_cluster_rows(self) -> list:
        try:
            return self.find_elements(ClusterListLocators.ClusterTable.row, timeout=5)
        except TimeoutException:
            return []

    def get_cluster_info_from_row(self, row: int) -> dict:
        row_elements = ClusterListLocators.ClusterTable.ClusterRow
        cluster_row = self.get_all_cluster_rows()[row]
        return {
            "name": self.find_child(cluster_row, row_elements.name).text,
            "bundle": self.find_child(cluster_row, row_elements.bundle).text,
            "description": self.find_child(cluster_row, row_elements.description).text,
            "state": self.find_child(cluster_row, row_elements.state).text,
        }
