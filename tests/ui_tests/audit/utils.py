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

from selenium.webdriver.remote.webelement import WebElement

from tests.ui_tests.app.page.admin.page import LoginAuditPage, OperationsAuditPage


def add_filter(page: OperationsAuditPage | LoginAuditPage, filter_menu_name: str) -> WebElement:
    filter_name = filter_menu_name.replace(" ", "_").lower()
    page.add_filter(filter_menu_name=filter_menu_name)
    assert page.is_filter_visible(filter_name=filter_name), f"Filter for {filter_menu_name} should be visible"
    return page.get_filter_input(filter_name=filter_name)
