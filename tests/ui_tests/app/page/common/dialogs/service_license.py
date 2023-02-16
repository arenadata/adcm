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

"""Popup page Service license classes"""
from selenium.webdriver.remote.webdriver import WebDriver, WebElement

from tests.functional.tools import DEFAULT_TIMEOUT
from tests.ui_tests.app.page.common.dialogs.locators import ServiceLicenseDialog
from tests.ui_tests.core.interactors import Interactor


class ServiceLicenseModal(Interactor):
    """Class for manipulating with service license dialog."""

    def __init__(self, element: WebElement, driver: WebDriver):
        super().__init__(driver=driver, default_timeout=1)
        self._view = Interactor(driver=driver, default_timeout=DEFAULT_TIMEOUT)
        self.element = element
        self.driver = driver

    def get_text(self) -> str:
        return self.find_child(self.element, ServiceLicenseDialog.license_text_field).text

    def accept_license(self) -> None:
        self.find_child(self.element, ServiceLicenseDialog.agree_btn).click()

    def reject_license(self) -> None:
        self.find_child(self.element, ServiceLicenseDialog.disagree_btn).click()
