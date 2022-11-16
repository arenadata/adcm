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

"""Common locators"""

from selenium.webdriver.common.by import By
from tests.ui_tests.app.helpers.locator import Locator


class CommonLocators:
    """Locators common to all pages"""

    socket = Locator(By.CSS_SELECTOR, ".socket", "open socket marker")
    profile = Locator(By.CSS_SELECTOR, ".profile", "profile load marker")
    load_marker = Locator(By.CSS_SELECTOR, '.load_complete', "page load marker")
    mat_slide_toggle = Locator(By.CSS_SELECTOR, "mat-slide-toggle", "toggle")


class ObjectPageLocators:
    """Common locators for object's detailed page"""

    title = Locator(By.CSS_SELECTOR, "mat-card-header mat-card-title", "Title")
    subtitle = Locator(By.CSS_SELECTOR, "mat-card-header mat-card-subtitle", "Subtitle")
    text = Locator(By.CSS_SELECTOR, "mat-card-content", "Cluster main page text")


class ObjectPageMenuLocators:
    """Menu elements locators"""

    main_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_main']", "Tab main")
    services_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_service']", "Tab services")
    hosts_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_host']", "Tab hosts")
    components_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_host_component']", "Tab components")
    service_components_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_component']", "Tab service components")
    config_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_config']", "Tab config")
    group_config_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_group_config']", "Tab group config")
    status_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_status']", "Tab status")
    import_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_import']", "Tab import")
    intro_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_intro']", "Tab admin intro")
    settings_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_settings']", "Tab admin settings")
    users_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_users']", "Tab admin users")
    groups_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_groups']", "Tab admin groups")
    roles_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_roles']", "Tab admin roles")
    policies_tab = Locator(By.CSS_SELECTOR, "a[adcm_test='tab_policies']", "Tab admin policies")
    warn_icon = Locator(By.CSS_SELECTOR, "mat-icon[color='warn']", 'Icon "!"')


class CommonActionLocators:
    """Common action page elements locators"""

    action_card = Locator(By.CSS_SELECTOR, "app-action-card", "Action card")
    info_text = Locator(By.CSS_SELECTOR, "app-action-card>p", "Text on action page")

    class ActionCard:
        """Common action page action card elements locators"""

        play_btn = Locator(By.CSS_SELECTOR, "button", "Action run button")
