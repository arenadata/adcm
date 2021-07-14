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

from tests.ui_tests.app.helpers.locator import Locator


class CommonHeaderLocators:
    """ADCM header locators"""

    block = Locator(By.XPATH, "//app-top/mat-toolbar", "Header block")

    arenadata_logo = Locator(By.XPATH, "//a[./img[@alt='Arenadata cluster manager']]", "Header logo Arenadata")

    clusters = Locator(By.CLASS_NAME, "topmenu_clusters", "Header button Clusters")
    hostproviders = Locator(By.CLASS_NAME, "topmenu_hostproviders", "Header button Hostproviders")
    hosts = Locator(By.CLASS_NAME, "topmenu_hosts", "Header button Hosts")
    jobs = Locator(By.CLASS_NAME, "topmenu_jobs", "Header button Jobs")
    bundles = Locator(By.CLASS_NAME, "topmenu_bundles", "Header button Bundles")


class AuthorizedHeaderLocators(CommonHeaderLocators):
    """ADCM header locators for authorized user"""

    job_block_previous = Locator(By.XPATH, "//app-bell/div", "Header jobs block previous version")
    job_block = Locator(By.CLASS_NAME, "job-status", "Header jobs block")
    job_popup = Locator(By.XPATH, "//app-popover", "Header jobs pop up")

    in_progress_job_button = Locator(By.XPATH, "//button[@mattooltip='Show jobs in progress']",
                                     "Header button for in progress Jobs")
    success_job_button = Locator(By.XPATH, "//button[@mattooltip='Show success jobs']",
                                 "Header button for success Jobs")
    failed_job_button = Locator(By.XPATH, "//button[@mattooltip='Show failed jobs']", "Header button for failed Jobs")
    help_button = Locator(By.XPATH, "//button[@adcm_test='help']", "Header button for help")
    account_button = Locator(By.XPATH, "//button[@adcm_test='account']", "Header button for account settings")

    class HelpPopup:
        """ADCM header popup with help links"""

        block = Locator(By.XPATH, "//div[contains(@class, 'mat-menu-content')]", "Header help popup block")
        ask_link = Locator(By.XPATH, "//a[@adcm_test='ask_for_help']", "Ask for help link")
        doc_link = Locator(By.XPATH, "//a[@adcm_test='dock']", "Documentation link")
