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

"""Profile page locators"""

from selenium.webdriver.common.by import By
from tests.ui_tests.app.helpers.locator import Locator


class ProfileLocators:
    """Profile page elements locators"""

    username = Locator(By.XPATH, "//p[contains(text(), 'You are authorized as')]/b", "Authorized user name")
    password = Locator(By.CSS_SELECTOR, "input[formcontrolname='password']", "New password input field")
    confirm_password = Locator(By.CSS_SELECTOR, "input[formcontrolname='cpassword']", "New password confirmation field")
    save_password_btn = Locator(By.XPATH, "//button[./span[text()= 'Save']]", "Save password button")
