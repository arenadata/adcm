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

"""Page objects for ConfigurationPage"""

import json

import allure
import requests
from adcm_client.objects import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.locators import Common, ConfigurationLocators
from tests.ui_tests.app.pages import BasePage


def _make_request(adcm_credentials, app_fs, method: str, path: str, **kwargs) -> requests.Response:
    def check_response(response):
        assert response.status_code == 200

    token = requests.post(f'{app_fs.adcm.url}/api/v1/token/', json=adcm_credentials)
    check_response(token)
    header = {'Authorization': f'Token {token.json()["token"]}'}
    response = requests.request(method=method, url=app_fs.adcm.url + path, headers=header, **kwargs)
    check_response(response)
    return response


class Configuration(BasePage):  # pylint: disable=too-many-public-methods
    """Class for configuration page"""

    def __init__(self, driver, url=None):
        super().__init__(driver)
        self.url = url
        if self.url:
            self.get(self.url, "config")
        self._wait_for_page_loaded()

    @staticmethod
    def from_service(app: ADCMTest, service: Service):
        """Init object based on service passed"""
        return Configuration(
            app.driver,
            f"{app.adcm.url}/cluster/{service.cluster_id}/service/{service.service_id}/config",
        )

    def _wait_for_page_loaded(self):
        self._wait_element_present(ConfigurationLocators.app_conf_form, 15)
        # 30 seconds timeout here is caused by possible long load of config page
        self._wait_element_present(ConfigurationLocators.load_marker, 30)

    @allure.step('Assert that we can edit field or not')
    def assert_field_is_editable(self, field_element, editable=True) -> None:
        """Assert that we can edit field or not"""
        assert (
            self.is_element_editable(field_element) == editable
        ), f"Field {field_element} should {'be editable' if editable else 'not be editable'}"

    def get_api_value(self, adcm_credentials, app_fs, field: str):
        """Gets field value by api"""

        current_config = _make_request(
            adcm_credentials, app_fs, "GET", f"/api/v1/{self.driver.current_url.replace(app_fs.adcm.url, '')}/current"
        ).text
        current_config_dict = json.loads(current_config)['config']
        try:
            if 'group' in current_config_dict:
                if field in current_config_dict['group']:
                    return current_config_dict['group'][field]
                else:
                    return current_config_dict['group']['structure_property'][field]
            else:
                if field in current_config_dict:
                    return current_config_dict[field]
                else:
                    return current_config_dict['structure_property'][field]
        except KeyError:
            raise AssertionError(f"No parameter {field} found by api")

    # pylint:disable=too-many-arguments
    @allure.step('Assert field: {field} to have value: {expected_value}')
    def assert_field_content_equal(self, adcm_credentials, app_fs, field_type, field, expected_value):
        """Assert field value based on field type and name"""

        current_value = self.get_field_value_by_type(field, field_type)
        current_api_value = self.get_api_value(adcm_credentials, app_fs, field.text.split(":")[0])
        if field_type in ('password', 'secrettext'):
            # In case of password we have no raw password in API after writing.
            if expected_value is not None and expected_value != "":
                assert current_value is not None, "Password field expected to be filled"
                assert current_api_value is not None, "Password field expected to be filled"
            else:
                assert current_value is None or current_value == "", "Password have to be empty"
                assert current_api_value is None or current_api_value == "", "Password have to be empty"
        else:
            if field_type == 'file':
                expected_value = 'test'
            if field_type == 'map':
                map_config = self.get_map_field_config(field)
                assert set(map_config.keys()) == set(map_config.keys())
                assert set(map_config.values()) == set(map_config.values())
            else:
                assert current_value == expected_value, f"Field value with type {field_type} doesn't equal expected"
                assert current_api_value == expected_value, f"Field value with type {field_type} doesn't equal expected"

    @allure.step('Assert frontend errors presence and text')
    def assert_alerts_presented(self, field_type):
        """Assert frontend errors presence and text"""
        errors = self.get_frontend_errors()
        assert errors
        if field_type == 'password':
            assert len(errors) == 2
            error_text = f"Field [{field_type}] is required!"
            error_texts = [error.text for error in errors]
            assert error_text in error_texts

    @allure.step('Assert that group is active or not')
    def assert_group_status(self, group_element, status=True):
        """Assert that group is active or not"""
        if status:
            assert self.group_is_active_by_element(group_element), "Group element should be active"
        else:
            assert not self.group_is_active_by_element(group_element), "Group element should not be active"

    @allure.step('Assert that form field text have expected value: {expected_text}')
    def assert_form_field_text_equal(self, form_field_element: WebElement, expected_text: str):
        """Check that mat form field text have expected value"""
        field_text = self.get_form_field_text(form_field_element)
        err_msg = f"Actual field text: {field_text}. Expected field text: {expected_text}"
        assert field_text == expected_text, err_msg

    @allure.step('Assert that form field text contains: {expected_text}')
    def assert_form_field_text_in(self, form_field_element: WebElement, expected_text: str):
        """Assert that form field text contains substring"""
        field_text = self.get_form_field_text(form_field_element)
        err_msg = f"Actual field text: {field_text}. Expected part of text: {expected_text}"
        assert expected_text in field_text, err_msg

    @allure.step('Assert that expected text in form field: {expected_text}')
    def assert_text_in_form_field_element(self, element: WebElement, expected_text: str):
        """Assert that expected text in form field"""
        result = self._wait_text_element_in_element(element, Common.mat_form_field, text=expected_text)
        err_msg = f"Expected text not presented: {expected_text}."
        assert result, err_msg

    @staticmethod
    def get_map_key(item_element):
        """Get config element key"""
        form_field = item_element.find_element(*ConfigurationLocators.map_key_field)
        inp = form_field.find_element(*Common.mat_input_element)
        return inp.get_attribute("value")

    @staticmethod
    def get_map_value(item_element):
        """Get config element value"""
        form_field = item_element.find_element(*ConfigurationLocators.map_value_field)
        inp = form_field.find_element(*Common.mat_input_element)
        return inp.get_attribute("value")

    def get_map_field_config(self, map_field):
        """Get config fields from UI as dict"""
        items = map_field.find_elements(*Common.item)
        result = {}
        for item in items:
            _key = self.get_map_key(item)
            _value = self.get_map_value(item)
            result[_key] = _value
        return result

    def get_field_value_by_type(self, field_element: WebElement, field_type: str):
        """Get config field value by type"""
        if field_type == 'boolean':
            element_with_value = field_element.find_element(*Common.mat_checkbox_class)
            current_value = self.get_checkbox_element_status(element_with_value)
        elif field_type == 'option':
            element_with_value = field_element.find_element(*Common.mat_select)
            current_value = self.get_field_value(element_with_value)
        elif field_type == 'list':
            elements_with_value = field_element.find_elements(*Common.mat_input_element)
            current_value = [self.get_field_value(element) for element in elements_with_value]
        elif field_type == 'structure':
            return self.get_structure_values(field_element)
        else:
            element_with_value = field_element.find_element(*Common.mat_input_element)
            current_value = self.get_field_value(element_with_value)
        if field_type == 'integer':
            current_value = int(current_value)
        elif field_type == 'float':
            current_value = float(current_value)
        elif field_type == 'json':
            current_value = json.loads(current_value)
        return current_value

    @staticmethod
    def get_structure_values(field) -> list:
        """Get value of config field with structure type"""
        schemes = field.find_elements(*ConfigurationLocators.app_root_scheme)[1:]
        config = []
        for scheme in schemes:
            fields_in_scheme = scheme.find_elements(*Common.mat_form_field)
            structure_element = {}
            for mat_field in fields_in_scheme:
                input_element = mat_field.find_element(*Common.mat_input_element)
                name = mat_field.text
                structure_element[name] = input_element.get_attribute("value")
            config.append(structure_element)
        return config

    @staticmethod
    def get_field_value(input_field):
        """Get config field value"""
        return input_field.get_attribute("value")

    @staticmethod
    def get_field_input(field):
        """Get config field element"""
        return field.find_element(*Common.mat_input_element)

    @staticmethod
    def get_field_checkbox(field):
        """Get config field checkbox element"""
        return field.find_element(*Common.mat_checkbox)

    def get_field_groups(self):
        """Get config field group elements"""
        return self.driver.find_elements(*ConfigurationLocators.field_group)

    @allure.step('Get save button status')
    def save_button_status(self):
        """Get save button status"""
        self._wait_element(ConfigurationLocators.config_save_button)
        button = self.driver.find_element(*ConfigurationLocators.config_save_button)
        class_el = button.get_attribute("disabled")
        if class_el == 'true':
            result = False
        else:
            result = True
        return result

    @allure.step('Get app fields')
    def get_app_fields(self):
        """Get app field elements"""
        return self.driver.find_elements(*ConfigurationLocators.app_field)

    @allure.step('Find element by name: {name}')
    def _get_group_element_by_name(self, name):
        self._wait_element_present(Common.mat_expansion_panel)
        config_groups = self.driver.find_elements(*Common.mat_expansion_panel)
        for group in config_groups:
            if name in group.text:
                return group
        return False

    @staticmethod
    def group_is_active_by_element(group_element):
        """Get group activity state by element"""
        toggle = group_element.find_element(*Common.mat_slide_toggle)
        if 'mat-checked' in toggle.get_attribute("class"):
            return True
        return False

    def group_is_active_by_name(self, group_name):
        """Get group activity state"""
        group = self._get_group_element_by_name(group_name)
        toogle = group.find_element(*Common.mat_slide_toggle)
        if 'mat-checked' in toogle.get_attribute("class"):
            return True
        return False

    @allure.step('Activate group by name: {group_name}')
    def activate_group_by_name(self, group_name):
        """Activate group by name"""
        group = self._get_group_element_by_name(group_name)
        toogle = group.find_element(*Common.mat_slide_toggle)
        if 'mat-checked' not in toogle.get_attribute("class"):
            toogle.click()

    def get_group_by_name(self, group_name):
        """Get group by name"""
        return self._get_group_element_by_name(group_name)

    @allure.step('Save configuration')
    def save_configuration(self):
        """Click on save button"""
        self._getelement(ConfigurationLocators.config_save_button).click()

    @allure.step('Click advanced')
    def click_advanced(self):
        """Toggle on advanced checkbox"""
        self._click_element(Common.mat_checkbox, name="Advanced")

    @allure.step('Show advanced')
    def show_advanced(self):
        """Enable advanced if disabled"""
        if not self.advanced:
            self.click_advanced()

    @allure.step('Hide advanced')
    def hide_advanced(self):
        """Disable advanced if enabled"""
        if self.advanced:
            self.click_advanced()

    def get_form_field_text(self, form_field_element):
        """Get form field text"""
        self._wait_element_present_in_sublement(form_field_element, Common.mat_form_field)
        form_field = form_field_element.find_elements(*Common.mat_form_field)[0]
        return form_field.get_attribute("textContent").strip()

    def get_form_field(self, field_element):
        """Get form field element"""
        self._wait_element_present_in_sublement(field_element, Common.mat_form_field)
        return field_element.find_elements(*Common.mat_form_field)[0]

    @property
    def advanced(self):
        """Get advanced checkbox status"""
        self._wait_element(Common.mat_checkbox)
        buttons = self.driver.find_elements(*Common.mat_checkbox)
        for button in buttons:
            if button.get_attribute("textContent").strip() == 'Advanced':
                return "checked" in button.get_attribute("class")
        return None

    @staticmethod
    def _get_tooltip_el_for_field(field):
        try:
            return field.find_element(*Common.info_icon)
        except NoSuchElementException:
            return False

    @staticmethod
    def check_tooltip_for_field(field):
        """Return tooltip element of false if element not found"""
        try:
            return field.find_element(*Common.info_icon)
        except NoSuchElementException:
            return False

    def get_tooltip_text_for_element(self, element):
        """Get tooltip text for element"""
        tooltip_icon = self._get_tooltip_el_for_field(element)
        # Hack for firefox because of move_to_element does not scroll to the element
        # https://github.com/mozilla/geckodriver/issues/776
        if self.driver.capabilities['browserName'] == 'firefox':
            self.driver.execute_script('arguments[0].scrollIntoView(true)', element)
        action = ActionChains(self.driver)
        action.move_to_element(tooltip_icon).perform()
        return self.driver.find_element(*Common.tooltip).text

    def get_textboxes(self):
        """Get textbox elements from the page"""
        return self.driver.find_elements(*ConfigurationLocators.app_fields_text_boxes)

    def get_password_elements(self):
        """Get password type elements from the page"""
        base_password_fields = self.driver.find_elements(*ConfigurationLocators.app_fields_password)
        return base_password_fields[0].find_elements(*ConfigurationLocators.displayed_password_fields)

    def get_display_names(self):
        """Get display names of the current config fields"""
        self._wait_element_present(Common.display_names, timer=15)
        return {name.text for name in self.driver.find_elements(*Common.display_names)}

    @allure.step('Set search field: {search_pattern}')
    def set_search_field(self, search_pattern):
        """Put a value inside a search field"""
        self._wait_element(ConfigurationLocators.search_field)
        element = self.driver.find_element(*ConfigurationLocators.search_field)
        self.clear_element(element)
        self._set_field_value(ConfigurationLocators.search_field, search_pattern)

    def get_group_elements(self):
        """Wait for group elements to be displayed and get them"""
        try:
            self._wait_element_present(Common.display_names)
        except TimeoutException:
            return []
        return self.driver.find_elements(*Common.display_names)

    @staticmethod
    def is_element_read_only(element) -> bool:
        """Check if app-field element is read-only by checking 'read-only' class presence"""
        return 'read-only' in str(element.get_attribute("class"))

    def is_element_editable(self, element) -> bool:
        """Check if app-field element is editable (not read-only)"""
        return not self.is_element_read_only(element)

    @allure.step('Check that fields and group are invisible')
    def check_that_fields_and_group_are_invisible(self):
        """Check that fields and group are invisible"""
        fields = self.get_field_groups()
        for field in fields:
            assert not field.is_displayed(), field.get_attribute("class")
        group_names = self.get_group_elements()
        assert not group_names, group_names

    @allure.step('Refresh configuration page')
    def refresh(self):
        """Refresh configuration page"""
        self.driver.refresh()
        self._wait_for_page_loaded()
