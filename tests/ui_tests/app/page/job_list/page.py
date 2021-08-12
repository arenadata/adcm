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
from dataclasses import dataclass
from typing import TypedDict, TypeVar, Union, List

import allure

from enum import Enum
from selenium.webdriver.remote.webelement import WebElement

from tests.ui_tests.app.helpers.ui_info import UIEntityInfo, UIField
from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)
from tests.ui_tests.app.page.common.header import AuthorizedHeaderLocators
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.tooltip_links.locator import CommonToolbarLocators
from tests.ui_tests.app.page.job_list.locators import TaskListLocators


class JobStatus(Enum):
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'


@dataclass
class PopupTaskInfo(UIEntityInfo):
    """Info about the job from popup"""

    action_name: str = UIField('Task action name from popup')
    status: JobStatus = UIField('Task status from popup')


@dataclass
class TableTaskInfo(PopupTaskInfo):
    """Info about the task from table row"""

    object: str = UIField('Name of object invoked action')
    start_date: str = UIField('Task start date')
    finish_date: str = UIField('Task finish date')


TaskInfo = TypeVar('TaskInfo', bound=Union[PopupTaskInfo, TableTaskInfo])


class SubTaskJobInfo(TypedDict):
    """Information about job in task's list of jobs"""

    name: str
    status: JobStatus


class JobListPage(BasePageObject):
    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/task")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url, TaskListLocators.Table)

    def get_task_info_from_table(self, row_num: int = 0) -> TableTaskInfo:
        """Get job information from row"""
        row = self.table.get_row(row_num)
        row_locators = TaskListLocators.Table.Row
        return TableTaskInfo(
            action_name=self.find_child(row, row_locators.action_name).text,
            object=self.find_child(row, row_locators.object).text,
            start_date=self.find_child(row, row_locators.start_date).text,
            finish_date=self.find_child(row, row_locators.finish_date).text,
            status=self._get_status_from_class_string(self.find_child(row, row_locators.status)),
        )

    def get_task_info_from_popup(self, row_num: int = 0) -> PopupTaskInfo:
        """Get job information from list in popup"""
        job = self.header.get_single_job_row_from_popup(row_num)
        popup_locators = AuthorizedHeaderLocators.JobPopup
        return PopupTaskInfo(
            action_name=self.find_child(job, popup_locators.job_name).text,
            status=self._get_status_from_class_string(
                self.find_child(job, popup_locators.job_status)
            ),
        )

    @allure.step('Expand task in row {row_num}')
    def expand_task_in_row(self, row_num: int = 0):
        """Click on expand jobs button"""
        table_locators = TaskListLocators.Table
        row = self.table.get_row(row_num)
        self.find_child(row, table_locators.Row.expand_task).click()
        self.wait_element_visible(table_locators.ExpandedTask.block)

    @allure.step("Click on job in task's job list")
    def click_on_job(self, job_num: int = 0):
        """Click on job in expanded first task's job list"""
        expand_task_locators = TaskListLocators.Table.ExpandedTask
        job_rows = self.find_elements(expand_task_locators.row)
        assert job_num < len(job_rows), 'Not enough jobs in this task'
        self.find_child(job_rows[job_num], expand_task_locators.Row.job_name).click()

    def get_all_jobs_info(self) -> List[SubTaskJobInfo]:
        """
        Returns information about all jobs
        from expanded first task's jobs list
        """
        expand_task_locators = TaskListLocators.Table.ExpandedTask
        job_rows = self.find_elements(expand_task_locators.row)
        return [
            SubTaskJobInfo(
                name=self.find_child(job, expand_task_locators.Row.job_name).text,
                status=self._get_status_from_class_string(
                    self.find_child(job, expand_task_locators.Row.job_status)
                ),
            )
            for job in job_rows
        ]

    @allure.step('Select the "All" filter tab')
    def select_filter_all_tab(self):
        """Show all tasks"""
        self._select_filter(TaskListLocators.Filter.all)

    @allure.step('Select the "Running" filter tab')
    def select_filter_running_tab(self):
        """Show only running tasks"""
        self._select_filter(TaskListLocators.Filter.running)

    @allure.step('Select the "Success" filter tab')
    def select_filter_success_tab(self):
        """Show only success tasks"""
        self._select_filter(TaskListLocators.Filter.success)

    @allure.step('Select the "Failed" filter tab')
    def select_filter_failed_tab(self):
        """Show only failed tasks"""
        self._select_filter(TaskListLocators.Filter.failed)

    @allure.step('Click on action name')
    def click_on_action_name_in_row(self, row: WebElement):
        """Click on action name in row"""
        self.find_child_and_click(row, TaskListLocators.Table.Row.action_name)

    def _select_filter(self, filter_locator: Locator):
        """Click on filter tab and wait it is pressed"""
        self.find_and_click(filter_locator)
        self.wait_element_attribute(filter_locator, 'aria-pressed', "true")
        self.wait_element_hide(CommonToolbarLocators.progress_bar)

    @staticmethod
    def _get_status_from_class_string(status_element: WebElement) -> JobStatus:
        """Get JobStatus from @class string"""
        class_string = status_element.get_attribute('class')
        for status in JobStatus:
            if status.value in class_string:
                return status
        raise KeyError('Job status not found in class string: %s' % str(class_string))
