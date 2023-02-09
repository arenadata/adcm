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

"""Job List page locators"""

from selenium.webdriver.common.by import By

from tests.ui_tests.app.page.common.table.locator import CommonTable
from tests.ui_tests.core.locators import BaseLocator


class TaskListLocators:
    """Task List page elements locators"""

    class Filter:
        """Task List page filter elements locators"""

        all = BaseLocator(By.CSS_SELECTOR, "mat-button-toggle[value=''] button", "All jobs filter button")
        running = BaseLocator(By.CSS_SELECTOR, "mat-button-toggle[value='running'] button", "Running filter button")
        success = BaseLocator(By.CSS_SELECTOR, "mat-button-toggle[value='success'] button", "Success filter button")
        failed = BaseLocator(By.CSS_SELECTOR, "mat-button-toggle[value='failed'] button", "Failed filter button")
        filter_btn = BaseLocator(By.CSS_SELECTOR, "mat-button-toggle button", "Filter button")

    class Table(CommonTable):
        """Task List page table elements locators"""

        class Row:
            """Task List page row elements locators"""

            action_name = BaseLocator(By.CSS_SELECTOR, "app-task-name a", "Action name in row")
            # task (a.k.a. multi-job) have another element storing the name
            task_action_name = BaseLocator(By.CSS_SELECTOR, "app-task-name * span", "Action name in row")
            invoker_objects = BaseLocator(By.CSS_SELECTOR, "app-task-objects a", "Object that invoked action in row")
            start_date = BaseLocator(By.CSS_SELECTOR, "mat-cell.action_date:nth-child(4)", "Start date in row")
            finish_date = BaseLocator(By.CSS_SELECTOR, "mat-cell.action_date:nth-child(5)", "Finish date in row")
            download_log = BaseLocator(By.TAG_NAME, "app-download-button-column", "Log download button")
            # span for done_all and mat-icon for running
            # but in both cases we can identify status by class
            status = BaseLocator(By.CSS_SELECTOR, "app-task-status-column *", "Status span in row")

            # when running (and cancel is allowed, then we should take another element to get status)
            status_under_btn = BaseLocator(By.CSS_SELECTOR, "app-task-status-column button * mat-icon", "Status in row")

            expand_task = BaseLocator(By.XPATH, ".//mat-icon[contains(text(), 'expand_more')]", "Expand task button")

        class ExpandedTask:
            """Task List page expanded task elements locators"""

            block = BaseLocator(By.CSS_SELECTOR, "app-jobs", "Expanded task block")
            row = BaseLocator(By.CSS_SELECTOR, "app-jobs mat-row", "Job row in expanded Task")

            class Row:
                """Task List page row elements locators"""

                job_name = BaseLocator(By.CSS_SELECTOR, "app-job-name a", "Job name")
                job_start_date = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", "Job start date")
                job_finish_date = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(3)", "Job finish date")
                job_status = BaseLocator(By.CSS_SELECTOR, "app-job-status-column mat-icon", "Job status")
