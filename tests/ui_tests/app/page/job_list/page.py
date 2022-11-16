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

"""Job List page PageObjects classes"""

from dataclasses import dataclass
from enum import Enum
from typing import List, TypeVar, Union

import allure
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webelement import WebElement
from tests.library.conditional_retriever import DataSource, FromOneOf
from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageFooter,
    PageHeader,
)
from tests.ui_tests.app.page.common.header_locators import AuthorizedHeaderLocators
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.tooltip_links.locator import CommonToolbarLocators
from tests.ui_tests.app.page.job_list.locators import TaskListLocators


class JobStatus(Enum):
    """Available job statuses"""

    ABORTED = 'aborted'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'


@dataclass
class PopupTaskInfo:
    """Info about the job from popup"""

    action_name: str
    status: JobStatus


@dataclass
class TableTaskInfo(PopupTaskInfo):
    """Info about the job from table row"""

    invoker_objects: str
    start_date: str
    finish_date: str


@dataclass
class SubTaskJobInfo:
    """Information about job in task's list of jobs"""

    name: str
    status: JobStatus


TaskInfo = TypeVar('TaskInfo', bound=Union[PopupTaskInfo, TableTaskInfo])


class JobListPage(BasePageObject):
    """Job List Page class"""

    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/task")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url, TaskListLocators.Table)

    def get_task_info_from_table(self, row_num: int = 0, *, full_invoker_objects_link: bool = False) -> TableTaskInfo:
        """
        Get job information from row

        :param row_num: Index of row in table
        :param full_invoker_objects_link: Use it to get full object link (with "parent" objects)
                                          or just object which invoked the action
        """
        row = self.table.get_row(row_num)

        def extract_status(locator):
            return self._get_status_from_class_string(self.find_child(row, locator, timeout=4))

        row_locators = TaskListLocators.Table.Row
        if full_invoker_objects_link:
            invoker_objects = self.find_children(row, row_locators.invoker_objects)
            object_link = '/'.join(obj.text.strip() for obj in invoker_objects)
        else:
            object_link = self.find_child(row, row_locators.invoker_objects).text.strip()
        # if task can be cancelled, then it will need another locator to determine the status
        get_status = FromOneOf(
            [
                DataSource(extract_status, [row_locators.status]),
                DataSource(extract_status, [row_locators.status_under_btn]),
            ],
            (KeyError, TimeoutError),
        )
        get_name_element = FromOneOf(
            [
                DataSource(self.find_child, [row, row_locators.action_name]),
                DataSource(self.find_child, [row, row_locators.task_action_name]),
            ],
            (TimeoutError, TimeoutException),
        )
        return TableTaskInfo(
            action_name=get_name_element().text,
            invoker_objects=object_link,
            start_date=self.find_child(row, row_locators.start_date).text,
            finish_date=self.find_child(row, row_locators.finish_date).text,
            status=get_status(),
        )

    def get_task_info_from_popup(self, row_num: int = 0) -> PopupTaskInfo:
        """Get job information from list in popup"""
        job = self.header.get_single_job_row_from_popup(row_num)
        popup_locators = AuthorizedHeaderLocators.JobPopup
        return PopupTaskInfo(
            action_name=self.find_child(job, popup_locators.JobRow.job_name).text,
            status=self._get_status_from_class_string(self.find_child(job, popup_locators.JobRow.job_status)),
        )

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
                status=self._get_status_from_class_string(self.find_child(job, expand_task_locators.Row.job_status)),
            )
            for job in job_rows
        ]

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

    @allure.step('Click on action name')
    def click_on_action_name_in_row(self, row: WebElement):
        """Click on action name in row"""
        locator = TaskListLocators.Table.Row.action_name
        row.find_element(locator.by, locator.value).click()

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
        raise KeyError(
            'Job status not found in class string: %s' % str(class_string)  # pylint: disable=consider-using-f-string
        )

    def get_selected_filter(self):
        """Get selected filter text"""
        for filter_element in self.find_elements(TaskListLocators.Filter.filter_btn):
            if filter_element.get_attribute("aria-pressed") == "true":
                return filter_element.text
        raise RuntimeError('None of filters are selected')
