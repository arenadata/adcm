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
from typing import Literal

import allure

from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.common.base_page import BasePageObject, PageHeader, PageFooter
from tests.ui_tests.app.page.common.tooltip_links.locator import CommonToolbarLocators
from tests.ui_tests.app.page.job.locators import JobPageLocators


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


class JobPage(BasePageObject):
    """Job detailed page"""

    def __init__(self, driver, base_url, job_id: int):
        super().__init__(driver, base_url, f"/job/{job_id}")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)

    def get_job_info(self) -> DetailedPageJobInfo:
        """Get information about job from detail page"""
        invoker_objects = self.find_element(JobPageLocators.subtitle).text.strip().replace(' / ', '/')
        return DetailedPageJobInfo(
            name=self.find_element(JobPageLocators.title).text.strip(),
            invoker_objects=invoker_objects,
            execution_time=self.find_element(JobPageLocators.execution_time).text.strip(),
            start_date=self.find_element(JobPageLocators.start_time).text.strip(),
            finish_date=self.find_element(JobPageLocators.finish_time).text.strip(),
        )

    def open_stdout_menu(self):
        """Open menu with stdout logs"""
        self._open_menu(JobPageLocators.Menu.stdout_tab)

    def open_stderr_menu(self):
        """Open menu with stderr logs"""
        self._open_menu(JobPageLocators.Menu.stderr_tab)

    @allure.step('Click on {log_type} download button')
    def click_on_log_download(self, log_type: Literal['stderr', 'stdout']):
        """Click on log download button"""
        locator = getattr(JobPageLocators.Menu, f'{log_type}_download_btn')
        self.find_and_click(locator)

    def _open_menu(self, locator: Locator):
        self.find_and_click(locator)
        self.wait_element_attribute(locator, 'class', 'active', exact_match=False)
        self.wait_element_hide(CommonToolbarLocators.progress_bar)
