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

"""Profile page PageObjects classes"""

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.profile.locators import ProfileLocators
from tests.ui_tests.core.checks import check_elements_are_displayed


class ProfilePage(BasePageObject):
    """Profile Page class"""

    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/profile")

    def get_username(self) -> str:
        """Get username of authorized user"""
        return self.find_element(ProfileLocators.username).text

    def set_new_password(self, password: str):
        """
        Insert password into password and password confirmation fields and click on save button
        """
        self.send_text_to_element(ProfileLocators.password, password)
        self.send_text_to_element(ProfileLocators.confirm_password, password)
        self.find_and_click(ProfileLocators.save_password_btn)

    @allure.step("Check required fields are presented on Profile page")
    def check_required_fields_are_presented(self):
        check_elements_are_displayed(
            self,
            [
                ProfileLocators.username,
                ProfileLocators.password,
                ProfileLocators.confirm_password,
                ProfileLocators.save_password_btn,
            ],
        )

    @allure.step("Check that username is {expected_username}")
    def check_username(self, expected_username: str):
        """Wait for username to be what it is expected on opened profile page"""

        def _check_username_on_profile_page():
            assert (
                username := self.get_username()
            ) == expected_username, f"Expected username is {expected_username}, got {username} instead"

        wait_until_step_succeeds(_check_username_on_profile_page, timeout=5, period=0.5)
