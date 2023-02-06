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

"""Job page PageObjects classes"""

from dataclasses import dataclass
from typing import Literal

import allure
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.common_locators import ObjectPageLocators
from tests.ui_tests.app.page.common.tooltip_links.locator import CommonToolbarLocators
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar
from tests.ui_tests.app.page.job.locators import JobPageLocators
from tests.ui_tests.core.locators import BaseLocator


@dataclass
class DetailedPageJobInfo:
    """Job info from detailed page"""

    # name of action / job
    name: str
    # name of object(s) which invoked this job
    invoker_objects: str
    execution_time: str
    start_date: str
    finish_date: str


class JobPageMixin(BasePageObject):
    """Helpers for working with job page"""

    MAIN_ELEMENTS: list
    job_id: int
    toolbar: CommonToolbar

    def __init__(self, driver, base_url, job_id: int):
        super().__init__(driver, base_url, "/job/{job_id}", job_id=job_id)
        self.job_id = job_id
        self.toolbar = CommonToolbar(self.driver, self.base_url)

    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
        JobPageLocators.start_date,
        JobPageLocators.finish_date,
        JobPageLocators.duration,
    ]

    @allure.step("Check title on the page")
    def check_title(self, expected_title: str):
        """Check title on the page"""
        self.wait_element_visible(ObjectPageLocators.title)
        current_title = self.find_element(ObjectPageLocators.title).text
        assert current_title == expected_title, f"Title should be '{expected_title}', but was {current_title}''"

    def get_job_info(self) -> DetailedPageJobInfo:
        """Get information about job from detail page"""
        invoker_objects = self.find_element(JobPageLocators.subtitle).text.strip().replace(" / ", "/")
        return DetailedPageJobInfo(
            name=self.find_element(JobPageLocators.title).text.strip(),
            invoker_objects=invoker_objects,
            execution_time=self.find_element(JobPageLocators.duration).text.strip(),
            start_date=self.find_element(JobPageLocators.start_date).text.strip(),
            finish_date=self.find_element(JobPageLocators.finish_date).text.strip(),
        )

    @allure.step("Open stdout menu")
    def open_stdout_menu(self):
        """Open menu with stdout logs"""
        self._open_menu(JobPageLocators.Menu.stdout_tab)

    @allure.step("Open stderr menu")
    def open_stderr_menu(self):
        """Open menu with stderr logs"""
        self._open_menu(JobPageLocators.Menu.stderr_tab)

    @allure.step("Click on {log_type} download button")
    def click_on_log_download(self, log_type: Literal["stderr", "stdout"]):
        """Click on log download button"""
        locator = getattr(JobPageLocators.Menu, f"{log_type}_download_btn")
        self.find_and_click(locator)

    def _open_menu(self, locator: BaseLocator):
        self.find_and_click(locator)
        self.wait_element_attribute(locator, "class", "active", exact_match=False)
        self.wait_element_hide(CommonToolbarLocators.progress_bar)

    def check_jobs_toolbar(self, action_name: str):
        self.toolbar.check_toolbar_elements(["JOBS", action_name])


class JobPageStdout(JobPageMixin):
    """Job Page Stdout log"""

    @allure.step("Check text on the job log page")
    def check_text(self, success_task: bool = True):
        """Check text on the page"""
        task_result = "Success" if success_task else "Fail"
        headings = [
            "PLAY [SeeMeInAction]",
            "TASK [Gathering Facts] ",
            f"TASK [{task_result}] ***",
            "PLAY RECAP",
            "Gathering Facts ---",
            f"{task_result} ---",
        ]
        job_log = self.find_element(JobPageLocators.job_log).text
        for header in headings:
            assert header in job_log, f"There are no header '{header}' on the page"


class JobPageStderr(JobPageMixin):
    """Job Page Stderr log"""
