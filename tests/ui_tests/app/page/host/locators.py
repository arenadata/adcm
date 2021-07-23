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
from selenium.webdriver.common.by import By

from tests.ui_tests.app.helpers.locator import Locator, TemplateLocator


class HostLocators:
    """Host main page elements locators"""

    class Header:
        fqdn = Locator(
            By.XPATH,
            "//mat-drawer-content/mat-card/mat-card-header/div/mat-card-title",
            "Host FQDN",
        )
        provider = Locator(
            By.XPATH,
            "//mat-drawer-content/mat-card/mat-card-header/div/mat-card-subtitle",
            "Host provider",
        )

    class MenuNavigation:
        main = Locator(By.XPATH, "//a[@adcm_test='tab_main']", "Main link in side menu")
        config = Locator(
            By.XPATH, "//a[@adcm_test='tab_config']", "Configuration link in side menu"
        )
        status = Locator(By.XPATH, "//a[@adcm_test='tab_status']", "Status in side menu")
        actions = Locator(By.XPATH, "//a[@adcm_test='tab_action']", "Actions in side menu")

    class Actions:
        action_name = Locator(
            By.XPATH, "//app-action-card//mat-card-title", "Action title in Actions menu"
        )
        action_btn = TemplateLocator(
            By.XPATH,
            "//mat-card-title[text()='{}']/ancestor::mat-card-header//button",
            "Action in Actions menu",
        )
        action_run_btn = Locator(By.XPATH, "//app-action-list/button", "Action run button")
