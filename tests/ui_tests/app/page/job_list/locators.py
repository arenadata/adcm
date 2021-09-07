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
from tests.ui_tests.app.page.common.table.locator import CommonTable


class TaskListLocators:
    class Filter:
        all = Locator(By.CSS_SELECTOR, "mat-button-toggle[value=''] button", "All jobs filter button")
        running = Locator(By.CSS_SELECTOR, "mat-button-toggle[value='running'] button", "Running filter button")
        success = Locator(By.CSS_SELECTOR, "mat-button-toggle[value='success'] button", "Success filter button")
        failed = Locator(By.CSS_SELECTOR, "mat-button-toggle[value='failed'] button", "Failed filter button")

    class Table(CommonTable):
        class Row:
            action_name = Locator(By.CSS_SELECTOR, "app-task-name a", "Action name in row")
            invoker_objects = Locator(By.CSS_SELECTOR, "app-task-objects a", "Object that invoked action in row")
            start_date = Locator(By.CSS_SELECTOR, "mat-cell.action_date:nth-child(4)", "Start date in row")
            finish_date = Locator(By.CSS_SELECTOR, "mat-cell.action_date:nth-child(5)", "Finish date in row")
            # span for done_all and mat-icon for running
            # but in both cases we can identify status by class
            status = Locator(By.CSS_SELECTOR, "app-task-status-column *", "Status span in row")

            expand_task = Locator(By.XPATH, ".//mat-icon[contains(text(), 'expand_more')]", "Expand task button")

        class ExpandedTask:
            block = Locator(By.CSS_SELECTOR, "app-jobs", "Expanded task block")
            row = Locator(By.CSS_SELECTOR, "app-jobs mat-row", "Job row in expanded Task")

            class Row:
                job_name = Locator(By.CSS_SELECTOR, "app-job-name a", "Job name")
                job_start_date = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", "Job start date")
                job_finish_date = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(3)", "Job finish date")
                job_status = Locator(By.CSS_SELECTOR, "app-job-status-column mat-icon", "Job status")
