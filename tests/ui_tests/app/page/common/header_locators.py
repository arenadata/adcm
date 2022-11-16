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

"""Header locators"""

from selenium.webdriver.common.by import By
from tests.ui_tests.app.helpers.locator import Locator


class CommonHeaderLocators:
    """ADCM header locators"""

    block = Locator(By.CSS_SELECTOR, "app-top mat-toolbar", "Header block")

    arenadata_logo = Locator(By.XPATH, "//a[./img[@alt='Arenadata cluster manager']]", "Header logo Arenadata")

    clusters = Locator(By.CSS_SELECTOR, ".topmenu_clusters", "Header button Clusters")
    hostproviders = Locator(By.CSS_SELECTOR, ".topmenu_hostproviders", "Header button Hostproviders")
    hosts = Locator(By.CSS_SELECTOR, ".topmenu_hosts", "Header button Hosts")
    jobs = Locator(By.CSS_SELECTOR, ".topmenu_jobs", "Header button Jobs")
    bundles = Locator(By.CSS_SELECTOR, ".topmenu_bundles", "Header button Bundles")


class AuthorizedHeaderLocators(CommonHeaderLocators):
    """ADCM header locators for authorized user"""

    job_block = Locator(By.CSS_SELECTOR, "app-bell div", "Header jobs block previous version")
    job_popup = Locator(By.CSS_SELECTOR, "app-popover", "Header jobs pop up")

    help_button = Locator(By.CSS_SELECTOR, "button[adcm_test='help']", "Header button for help")
    account_button = Locator(By.CSS_SELECTOR, "button[adcm_test='account']", "Header button for account settings")
    popup_block = Locator(By.CSS_SELECTOR, "*.mat-menu-content", "Header popup block")
    bell_icon = Locator(By.CSS_SELECTOR, "div.circle", "Bell icon")

    in_progress_job_button = Locator(
        By.XPATH,
        "//button[@mattooltip='Show jobs in progress']",
        "Header button for in progress Jobs",
    )
    success_job_button = Locator(
        By.XPATH, "//button[@mattooltip='Show success jobs']", "Header button for success Jobs"
    )
    failed_job_button = Locator(By.XPATH, "//button[@mattooltip='Show failed jobs']", "Header button for failed Jobs")

    class JobPopup:
        """ADCM header popup with jobs"""

        block = Locator(By.CSS_SELECTOR, "app-popover", "Popup block with jobs")

        success_jobs = Locator(By.CSS_SELECTOR, "div[mattooltip='Show success jobs']", "Success jobs")
        in_progress_jobs = Locator(By.CSS_SELECTOR, "div[mattooltip='Show jobs in progress']", "In progress jobs")
        failed_jobs = Locator(By.CSS_SELECTOR, "div[mattooltip='Show failed jobs']", "Failed jobs")
        job_row = Locator(By.CSS_SELECTOR, "div>div[class*='notification']", "Job row in popup list")

        show_all_link = Locator(By.CSS_SELECTOR, "app-popover a[href='/task']", "Link to task page")
        empty_text = Locator(By.CSS_SELECTOR, "app-notifications *.empty-label", "Text in popup")
        acknowledge_btn = Locator(By.CSS_SELECTOR, "a.acknowledge", "Acknowledge button")

        class JobRow:
            """ADCM header popup job row with jobs"""

            job_status = Locator(By.CSS_SELECTOR, "mat-icon", "Job status in job row")
            job_name = Locator(By.CSS_SELECTOR, "a", "Job row name in popup list")

    class HelpPopup:
        """ADCM header popup with help links"""

        ask_link = Locator(By.CSS_SELECTOR, "a[adcm_test='ask_for_help']", "Ask for help link")
        doc_link = Locator(By.CSS_SELECTOR, "a[adcm_test='dock']", "Documentation link")

    class AccountPopup:
        """ADCM header popup with account settings"""

        settings_link = Locator(By.CSS_SELECTOR, "a[adcm_test='settings']", "Settings link")
        profile_link = Locator(By.CSS_SELECTOR, "button[adcm_test='profile']", "Profile link")
        logout_button = Locator(By.CSS_SELECTOR, "button[adcm_test='logout']", "logout button")
