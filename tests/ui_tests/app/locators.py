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

# Created by a1wen at 05.03.19

from tests.ui_tests.app.helpers import bys


class Menu:
    """Top menu locators"""

    clusters = bys.by_class("topmenu_clusters")
    hostproviders = bys.by_class("topmenu_hostproviders")
    hosts = bys.by_class("topmenu_hosts")
    jobs = bys.by_class("topmenu_jobs")
    bundles = bys.by_class("topmenu_bundles")


class Common:
    """List page elements locators"""

    # Addition form common elements
    add_btn = bys.by_xpath("//*[@adcm_test='create-btn']")
    options = bys.by_xpath("//*[@role='option']")
    description = bys.by_xpath("//*[@placeholder='Description']")
    save_btn = bys.by_xpath("//span[contains(., 'Save')]/parent::button")
    cancel_btn = bys.by_xpath("//span[contains(., 'Cancel')]/parent::button")

    # List elements common elements
    rows = bys.by_class('mat-row')
    del_btn = "//span[contains(., 'delete')]/parent::button"
    list_text = bys.by_class("mat-list-text")

    # Dialog form common elements
    dialog = bys.by_class('mat-dialog-container')
    dialog_yes = bys.by_xpath("//span[contains(text(),'Yes')]/parent::button")
    dialog_run = bys.by_xpath("//span[contains(text(),'Run')]/parent::button")
    dialog_no = bys.by_xpath("//span[contains(text(),'No')]/parent::button")

    # Error dialog elemetns
    error = bys.by_class('snack-bar-error')
    hide_err = ''

    # Action elements
    action = bys.by_xpath("//*[@adcm_test='action_btn']")

    # Configuration elements
    mat_error = bys.by_class("mat-error")
    mat_checkbox = bys.by_tag("mat-checkbox")
    mat_icon = bys.by_class("mat-icon")
    mat_input_element = bys.by_class("mat-input-element")
    display_names = bys.by_class("title.mat-expansion-panel-header-title")
    mat_expansion_panel = bys.by_class("mat-expansion-panel")
    textarea = bys.by_tag("textarea")
    item = bys.by_class("item")
    group_field = bys.by_class("app-group-fields")
    tooltip = bys.by_tag("app-tooltip")
    mat_slide_toggle = bys.by_class("mat-slide-toggle")
    mat_raised_button = bys.by_class("mat-raised-button")
    mat_form_field = bys.by_tag("mat-form-field")

    # Comon elements
    all_childs = bys.by("*")


class Cluster:
    """Cluster elements locators"""

    name = bys.by_xpath("//*[@placeholder='Cluster name']")
    prototype = bys.by_xpath("//*[@placeholder='Bundle']")
    host_tab = bys.by_xpath("//*[@adcm_test='tab_host']")
    service_tab = bys.by_xpath("//*[@test='tab_service']")


class Provider:
    """Provider elements locators"""

    name = bys.by_xpath("//*[@placeholder='Hostprovider name']")
    prototype = bys.by_xpath("//*[@placeholder='Bundle']")


class Host:
    """Host elements locators"""

    name = bys.by_xpath("//*[@placeholder='Fully qualified domain name']")
    prototype = bys.by_xpath("//*[@placeholder='Hostprovider']")
    cluster_id = bys.by_xpath("//*[@formcontrolname='cluster_id']")


class Service:
    """Service elements locators"""

    name = bys.by_class("mat-card-title")
    main_tab = bys.by_xpath("//*[@test='tab_main']")
    configuration_tab = bys.by_xpath("//*[@test='tab_configuration']")
    status_tab = bys.by_xpath("//*[@test='tab_status']")
    config_column = bys.by_class("mat-column-config")


class ConfigurationLocators:
    description = bys.by_xpath("//*[@placeholder='Description configuration']")
    search_field = bys.by_xpath("//*[@placeholder='Search field']")
    config_save_button = bys.by_class("form_config_button_save")
    app_fields_text_boxes = bys.by_tag("app-fields-textbox")
    app_fields_labels = bys.by_tag("app-fields-label")
    app_fields_map = bys.by_tag("app-fields-map")
    app_fields_password = bys.by_tag("app-fields-password")
    app_fields_textarea = bys.by_tag("app-fields-textarea")
    app_fields_json = bys.by_tag("app-fields-json")
    app_fields_list = bys.by_tag("app-fields-list")
    app_field = bys.by_tag("app-field")
    map_key = bys.by_xpath("//*[@formcontrolname='key']")
    map_value = bys.by_xpath("//*[@formcontrolname='value']")
    app_conf_fields = bys.by_tag("app-config-fields")
    field_group = bys.by_class("field-group")
    group_title = bys.by_tag("mat-panel-title")
