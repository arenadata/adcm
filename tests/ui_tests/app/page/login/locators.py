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

"""Login page locators"""

from selenium.webdriver.common.by import By

from tests.ui_tests.core.locators import BaseLocator


class LoginPageLocators:
    """Login page elements locators"""

    login_form_block = BaseLocator(By.CSS_SELECTOR, "*.form-auth", "login block")
    login_input = BaseLocator(By.CSS_SELECTOR, "#login", "login input")
    password_input = BaseLocator(By.CSS_SELECTOR, "#password", "password input")

    login_btn = BaseLocator(By.XPATH, "//button[./span[text()='Login']]", "button Login")

    login_warning = BaseLocator(By.CSS_SELECTOR, ".warn", "warning on login page")
