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

from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)
from tests.ui_tests.app.page.profile.locators import ProfileLocators


class ProfilePage(BasePageObject):
    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/profile")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)

    def get_username(self) -> str:
        """Get username of authorized user"""
        return self.find_element(ProfileLocators.username).text

    def set_new_password(self, password: str):
        """
        Insert password into password and password confirmation fields and click on save button
        """
        self.find_element(ProfileLocators.password).send_keys(password)
        self.find_element(ProfileLocators.confirm_password).send_keys(password)
        self.find_and_click(ProfileLocators.save_password_btn)

    @allure.step('Check required fields are presented on Profile page')
    def check_required_fields_are_presented(self):
        """Check that all fields that should be on page by default are presented"""
        self.assert_displayed_elements(
            [
                ProfileLocators.username,
                ProfileLocators.password,
                ProfileLocators.confirm_password,
                ProfileLocators.save_password_btn,
            ]
        )
