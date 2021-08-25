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
    search_input_clear_btn = Locator(By.XPATH, "//app-search//button[@aria-label='Clear']", "Clear search input button")
    description_input = Locator(
        By.XPATH,
        "//input[@data-placeholder='Description configuration']",
        "Config description input",
    )
    save_btn = Locator(By.XPATH, "//button[.//span[text()='Save']]", "Save configuration button")
    history_btn = Locator(By.XPATH, "//button[.//mat-icon[text()='history']]", "History button")

    compare_version_select = Locator(By.XPATH, "//mat-select[@placeholder='History']", "Base version to compare")
    compare_to_select = Locator(By.XPATH, "//mat-select[@placeholder='Compare to']", "Compare to version select")
    config_version_option = TemplateLocator(
        By.XPATH, "//mat-option//span[contains(text(), '{}')]", "Config version with text: {}"
    )
    # use it to check config diff existence by finding text entry
    config_diff = TemplateLocator(
        By.XPATH,
        "//app-field[.//div[@adcm_test='{}']]//mat-list-item//span[contains(text(), '{}')]",
        'Config diff of option "{}" with "{}" in text',
    )
    config_row = Locator(By.XPATH, "//app-field", "Configuration row")

    field_error = TemplateLocator(By.XPATH, "//mat-error[contains(text(), '{}')]", 'Error "{}"')
    loading_text = Locator(By.XPATH, "//span[text()='Loading...']", "Loading text")

    class ConfigRow:
        name = Locator(By.XPATH, ".//label", "Row name")
        value = Locator(By.XPATH, ".//input", "Row value")
        password = Locator(
            By.XPATH,
            "(.//app-fields-password/div[not(contains(@style, 'none'))]//input)[1]",
            "Password input",
        )
        confirm_password = Locator(
            By.XPATH,
            "(.//app-fields-password/div[not(contains(@style, 'none'))]//input)[2]",
            "Confirm password input",
        )
        history = Locator(By.XPATH, ".//mat-list-item//span[2]", "Row history")
        reset_btn = Locator(By.XPATH, ".//button[@mattooltip='Reset to default']", "Reset button")

    class ConfigGroup:
        name = Locator(By.XPATH, ".//mat-panel-title/span", "Group name")
        expansion_btn = Locator(By.XPATH, ".//mat-expansion-panel-header", "Expansion button")

    class HistoryRow:
        history_select = Locator(By.XPATH, "//mat-select[@placeholder='History']", "History select")
        compare_select = Locator(By.XPATH, "//mat-select[@placeholder='Compare to']", "Compare select")
        option = Locator(By.XPATH, "//mat-option", "Option in select")
