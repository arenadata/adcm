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

"""DEPRECATED! Some basic ServiceDetails PageObject"""

# Since this module is deprecated we will not fix docstrings here
# pylint: disable=missing-function-docstring, missing-class-docstring

from tests.ui_tests.app.configuration import Configuration
from tests.ui_tests.app.pages import Details, ListPage
from tests.ui_tests.app.locators import Service


class ServiceDetails(Details, ListPage):
    @property
    def main_tab(self):
        self._getelement(Service.main_tab).click()
        return ListPage(self.driver)

    @property
    def configuration_tab(self):
        self._getelement(Service.configuration_tab).click()
        return Configuration(self.driver)

    @property
    def status_tab(self):
        self._getelement(Service.status_tab).click()
        return ListPage(self.driver)

    def click_main_tab(self):
        return self._click_tab("Main")

    def click_configuration_tab(self):
        return self._click_tab("Configuration")
