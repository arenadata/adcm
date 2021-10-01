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

"""Service page locators"""

from selenium.webdriver.common.by import By

from tests.ui_tests.app.helpers.locator import Locator


class ServiceImportLocators:
    """Service import page elements locators"""

    import_item_block = Locator(By.CSS_SELECTOR, ".items>div", "Import item block")
