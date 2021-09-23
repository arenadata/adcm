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

from tests.ui_tests.app.helpers.locator import (
    Locator,
)


class JobPageLocators:
    class Menu:
        stdout_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_1']", "Job stdout tab")
        stderr_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_2']", "Job stderr tab")

    start_date = Locator(By.CSS_SELECTOR, ".time-info>div:first-child>span", "Start date")
    finish_date = Locator(By.CSS_SELECTOR, ".time-info>div:last-child>span", "Finish date")
    duration = Locator(By.CSS_SELECTOR, ".time-info>div:nth-child(2)>span", "Task duration")
