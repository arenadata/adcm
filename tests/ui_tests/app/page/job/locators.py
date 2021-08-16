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
from tests.ui_tests.app.page.common.common_locators import (
    ObjectPageLocators,
)


class JobPageLocators(ObjectPageLocators):
    """Locators for detailed job page"""

    job_info = Locator(By.TAG_NAME, "app-job-info", "Job info section")
    start_time = Locator(By.XPATH, "//div[@class='time-info']/div[1]/span", "Job start time")
    execution_time = Locator(
        By.XPATH, "//div[@class='time-info']/div[2]/span", "Job execution time"
    )
    finish_time = Locator(By.XPATH, "//div[@class='time-info']/div[3]/span", "Job finish time")

    class Menu:
        # keep stdout(-err) prefix in naming
        stdout_tab = Locator(
            By.XPATH, "//a[.//span[text()='ansible [ stdout ]']]", "stdout menu tab"
        )
        stdout_download_btn = Locator(
            By.XPATH, "//a[.//span[text()='ansible [ stdout ]']]//button", "Download stdout button"
        )
        stderr_tab = Locator(
            By.XPATH, "//a[.//span[text()='ansible [ stderr ]']]", "stdout err tab"
        )
        stderr_download_btn = Locator(
            By.XPATH, "//a[.//span[text()='ansible [ stderr ]']]//button", "Download stdout button"
        )
