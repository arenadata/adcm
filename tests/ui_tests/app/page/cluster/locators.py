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

"""Cluster page locators"""

from selenium.webdriver.common.by import By
from tests.ui_tests.app.page.host_list.locators import HostListLocators
from tests.ui_tests.core.locators import BaseLocator


class ClusterMainLocators:
    """Cluster main page elements locators"""

    text = BaseLocator(By.CSS_SELECTOR, ".mat-card-content", "Cluster main page text")


class ClusterServicesLocators:
    """Cluster main page elements locators"""

    add_services_btn = BaseLocator(By.CSS_SELECTOR, "button[adcm_test='create-btn']", "Add services button")
    service_row = BaseLocator(By.CSS_SELECTOR, ".mat-row", "Service row")

    class AddServicePopup:
        """Popup for adding services"""

        block = BaseLocator(By.CSS_SELECTOR, ".mat-dialog-container", "Popup block")
        service_row = BaseLocator(By.CSS_SELECTOR, ".mat-list-option", "Service row")
        create_btn = BaseLocator(By.CSS_SELECTOR, "app-add-service button:last-child", "Add button")
        cancel_btn = BaseLocator(By.CSS_SELECTOR, "app-add-service button:first-child", "Cancel button")

        class ServiceRow:
            """Locators for services row"""

            text = BaseLocator(By.CSS_SELECTOR, ".mat-list-text", "Service name")

    class ServiceTableRow:
        """Services table roe locators"""

        name = BaseLocator(By.CSS_SELECTOR, "mat-cell:first-of-type", "Service name")
        version = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", "Service version")
        state = BaseLocator(By.CSS_SELECTOR, "app-state-column", "Service state")
        status = BaseLocator(By.CSS_SELECTOR, "app-status-column button", "Service status")
        actions = BaseLocator(By.CSS_SELECTOR, "app-actions-button button", "Service actions")
        service_import = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(6) button", "Service import")
        config = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(7) button", "Service config")
        maintenance_mode = BaseLocator(By.CLASS_NAME, "mm-button", "Maintenance mode button")
        delete_btn = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(9) button", "Row delete button")


class ClusterHostLocators:
    """Cluster host page elements locators"""

    add_host_btn = BaseLocator(By.CSS_SELECTOR, "button[adcm_test='create-btn']", "Add host button")

    class HostTable(HostListLocators.HostTable):
        """Cluster host page host table elements locators"""


class ClusterActionLocators:
    """Cluster action page elements locators"""

    action_card = BaseLocator(By.CSS_SELECTOR, "app-action-card", "Action card")
    info_text = BaseLocator(By.CSS_SELECTOR, "app-action-card p", "Text on action page")

    class ActionCard:
        """Cluster action page action card elements locators"""

        play_btn = BaseLocator(By.CSS_SELECTOR, "button", "Action run button")
