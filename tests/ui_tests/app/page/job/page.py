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

import allure

from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)
from tests.ui_tests.app.page.common.common_locators import (
    ObjectPageLocators,
)
from tests.ui_tests.app.page.job.locators import JobPageLocators


class JobPageMixin(BasePageObject):

    MENU_SUFFIX: str
    MAIN_ELEMENTS: list
    job_id: int

    def __init__(self, driver, base_url, job_id: int):
        if self.MENU_SUFFIX is None:
            raise AttributeError('You should explicitly set MENU_SUFFIX in class definition')
        super().__init__(driver, base_url, "/cluster/{job_id}/" + self.MENU_SUFFIX, job_id=job_id)
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.job_id = job_id

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
        assert self.find_element(ObjectPageLocators.title).text == expected_title


class JobPageStdout(JobPageMixin):
    """Job Page Stdout log"""

    MENU_SUFFIX = '1'

    @allure.step("Check text on the page")
    def check_text(self, success_task: bool = True):
        task_result = 'Success' if success_task else 'Fail'
        headings = [
            "PLAY [SeeMeInAction]",
            "TASK [Gathering Facts] ",
            f"TASK [{task_result}] ***",
            "PLAY RECAP",
            "Gathering Facts ---",
            f"{task_result} ---",
        ]
        page_text = self.find_element(ObjectPageLocators.text).text
        for header in headings:
            assert header in page_text, f"There are no header '{header}' on the page"


class JobPageStderr(JobPageMixin):
    """Job Page Stderr log"""

    MENU_SUFFIX = '2'
