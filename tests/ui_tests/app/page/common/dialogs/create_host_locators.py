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

"""Popup page locators"""

from selenium.webdriver.common.by import By

from tests.ui_tests.core.locators import BaseLocator, TemplateLocator


class CommonPopupLocators:
    """ADCM popup locators"""

    block = BaseLocator(By.CSS_SELECTOR, "app-snack-bar", "Popup block")
    block_by_text = TemplateLocator(By.XPATH, "//app-snack-bar//div[text()='{}']", "Popup block with text {}")
    text = BaseLocator(By.CSS_SELECTOR, "app-snack-bar .message", "Popup info message")
    hide_btn = BaseLocator(By.XPATH, "//button[./span[text()='Hide']]", "Hide pop up button")
    hide_btn_by_text = TemplateLocator(
        By.XPATH,
        "//div[./div/div[text()='{}']]/button",
        "Hide pop up button with text {}",
    )
    verbose_chbx = BaseLocator(By.XPATH, "//mat-checkbox[.//span[text()='Verbose']]", "Verbose checkbox")


class HostCreationLocators:
    """Host creation popup without cluster selection"""

    block = BaseLocator(By.CSS_SELECTOR, "mat-dialog-container", "Host creation popup block")
    fqdn_input = BaseLocator(
        By.CSS_SELECTOR,
        "input[data-placeholder='Fully qualified domain name']",
        "Host FQDN input",
    )
    create_btn = BaseLocator(
        By.XPATH,
        "//app-add-controls//button[./span[contains(text(), 'Create')]]",
        "Create button",
    )
    cancel_btn = BaseLocator(By.XPATH, "//app-add-controls//button[./span[text()='Cancel']]", "Cancel button")

    class Provider:
        """Provider creation and selection section"""

        bundle_select_btn = BaseLocator(By.CSS_SELECTOR, "mat-select[placeholder='Bundle']", "Select bundle")
        select_option = BaseLocator(By.CSS_SELECTOR, "mat-option", "Select option")
        chosen_provider = BaseLocator(
            By.CSS_SELECTOR,
            "mat-select[placeholder*='Hostprovider']",
            "Chosen provider field",
        )
        add_btn = BaseLocator(By.XPATH, "//mat-form-field//mat-icon[text()='add']", "Add host provider button")
        new_provider_block = BaseLocator(By.CSS_SELECTOR, "app-add-provider", "Host provider creation block")
        new_provider_name = BaseLocator(By.CSS_SELECTOR, "input[formcontrolname='name']", "New host provider name")
        upload_bundle_btn = BaseLocator(By.CSS_SELECTOR, "input[value='upload_bundle_file']", "Upload bundle button")
        new_provider_add_btn = BaseLocator(
            By.CSS_SELECTOR,
            "button[mattooltip='Create hostprovider']",
            "Add new provider button",
        )

    class Cluster:
        """
        Cluster selection locators
        ! May not be presented (e.g. create host from cluster) !
        """

        cluster_select = BaseLocator(
            By.CSS_SELECTOR,
            "mat-select[formcontrolname='cluster_id']",
            "Cluster choice select",
        )
        cluster_option = TemplateLocator(
            By.XPATH,
            "//mat-option//span[contains(text(), '{}')]",
            "Cluster select option",
        )
        chosen_cluster = TemplateLocator(By.XPATH, "//span[text()='{}']", "Chosen parent cluster")


class HostAddPopupLocators:
    """Host add popup locators"""

    add_new_host_btn = BaseLocator(
        By.CSS_SELECTOR,
        "div[class*='actions'] button[cdk-describedby-host]",
        "Button to open popup for host creating",
    )


class ListConcernPopupLocators:
    """ADCM popup locators for concerns in list pages"""

    block = BaseLocator(By.CSS_SELECTOR, "app-popover", "list pages popup block")
    link_to_concern_object = BaseLocator(By.CSS_SELECTOR, "app-popover a", "Link to concern")


class PageConcernPopupLocators:
    """ADCM popup locators for concerns in common pages"""

    block = BaseLocator(By.CSS_SELECTOR, "app-popover", "common pages popup block")
    link_to_concern_object = BaseLocator(By.CSS_SELECTOR, "app-concern-item a", "Link to concern")
