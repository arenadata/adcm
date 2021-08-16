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

from tests.ui_tests.app.page.common.base_page import BasePageObject, PageHeader, PageFooter
from tests.ui_tests.app.page.job.locators import JobPageLocators


@dataclass
class DetailedPageJobInfo:
    """Job info from detailed page"""

    # name of action / job
    name: str
    # name of object who invoked this job
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
        invoker_objects = self.find_element(JobPageLocators.subtitle).text.strip()
        return DetailedPageJobInfo(
            name=self.find_element(JobPageLocators.title).text.strip(),
            # format to no space between "/"
            invoker_objects=invoker_objects.replace(' / ', '/'),
            execution_time=self.find_element(JobPageLocators.execution_time).text.strip(),
            start_date=self.find_element(JobPageLocators.start_time).text.strip(),
            finish_date=self.find_element(JobPageLocators.finish_time).text.strip(),
        )
