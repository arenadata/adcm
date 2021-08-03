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
        "//mat-expansion-panel-header[.//span[text()='{}']]",
        'Group "{}" button',
    )
    advanced_label = Locator(By.XPATH, "//mat-checkbox//span[text()='Advanced']", "Advanced label")
    search_input = Locator(By.ID, "config_search_input", "Search input")
    description_input = Locator(
        By.XPATH,
        "//input[@data-placeholder='Description configuration']",
        "Config description input",
    )
    save_btn = Locator(By.XPATH, "//button[.//span[text()='Save']]", "Save configuration button")
    history_btn = Locator(By.XPATH, "//button[.//mat-icon[text()='history']]", "History button")

    compare_to_select = Locator(
        By.XPATH, "//mat-select[@placeholder='Compare to']", "Compare to select"
    )
    config_version_option = TemplateLocator(
        By.XPATH, "//mat-option//span[contains(text(), '{}')]", "Config version with text: {}"
    )
    # use it to check config diff existence by finding text entry
    config_diff = TemplateLocator(
        By.XPATH,
        "//app-field[.//div[@adcm_test='{}']]//mat-list-item//span[contains(text(), '{}')]",
        'Config diff of option "{}" with "{}" in text',
    )

    field_input = TemplateLocator(
        By.XPATH,
        "//app-field[.//div[@adcm_test='{}']]//input",
        'Input of option "{}" in group',
    )
    password_inputs = TemplateLocator(
        By.XPATH,
        "//app-field[.//div[@adcm_test='{}']]//app-fields-password/div[not(contains(@style, 'none'))]//input",
        "Password inputs",
    )
    field_error = TemplateLocator(By.XPATH, "//mat-error[contains(text(), '{}')]", 'Error "{}"')
    reset_btn = TemplateLocator(
        By.XPATH,
        "//div[@adcm_test='{}']//mat-icon[text()='refresh']/ancestor::button",
        "Resfresh button of {}",
    )
