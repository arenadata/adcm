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

from tests.ui_tests.app.helpers.locator import Locator, TemplateLocator


class CommonConfigMenu:
    """Configuration menu locators"""

    group_btn = TemplateLocator(
        By.XPATH,
        "//span[text()='{}']/ancestor::mat-expansion-panel-header",
        'Group "{}" button',
    )
    advanced_label = Locator(By.XPATH, "//mat-checkbox//span[text()='Advanced']", "Advanced label")
    search_input = Locator(By.ID, "config_search_input", "Search input")
    description_input = Locator(
        By.XPATH,
        "//input[@data-placeholder='Description configuration']",
        "Config description input",
    )
    save_btn = Locator(
        By.XPATH, "//span[text()='Save']/ancestor::button", "Save configuration button"
    )
    history_btn = Locator(
        By.XPATH, "//mat-icon[text()='history']/ancestor::button", "History button"
    )

    compare_to_select = Locator(
        By.XPATH, "//mat-select[@placeholder='Compare to']", "Compare to select"
    )
    config_version_option = TemplateLocator(
        By.XPATH, "//mat-option//span[contains(text(), '{}')]", "Config version with text: {}"
    )
    # use it to check config diff existence by finding text entry
    config_diff = TemplateLocator(
        By.XPATH,
        "//div[@adcm_test='{}']/ancestor::app-field//mat-list-item//span[contains(text(), '{}')]",
        'Config diff of option "{}" with "{}" in text'
    )

    field_input = TemplateLocator(
        By.XPATH,
        "//div[@adcm_test='{}']/ancestor::app-field//input",
        'Input of option "{}" in group',
    )
    password_inputs = TemplateLocator(
        By.XPATH,
        "//div[@adcm_test='{}']/ancestor::app-field//app-fields-password/div[not(contains(@style, 'none'))]//input",
        "Password inputs",
    )
