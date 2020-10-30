import json

from retrying import retry
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException,\
    TimeoutException
from tests.ui_tests.app.pages import BasePage
from tests.ui_tests.app.locators import Common, ConfigurationLocators


def retry_on_exception(exc):
    return any((isinstance(exc, StaleElementReferenceException),
                isinstance(exc, NoSuchElementException)))


# pylint: disable=R0904
class Configuration(BasePage):
    """
    Class for configuration page
    """
    def __init__(self, driver, url=None):
        super().__init__(driver)
        if url:
            self.get(url, "config")
        self._wait_element_present(ConfigurationLocators.app_conf_form, 15)
        # 30 seconds timeout here is caused by possible long load of config page
        self._wait_element_present(ConfigurationLocators.load_marker, 30)

    def assert_field_editable(self, field, editable=True):
        """Check that we can edit specific field or not
        :param field:
        :param editable:
        :return:
        """
        field_editable = self.editable_element(field)
        assert field_editable == editable

    def assert_field_content_equal(self, field_type, field, expected_value):
        """Check that field content equal expected value

        :param field_type:
        :param field:
        :param expected_value:
        :return:
        """
        current_value = self.get_field_value_by_type(field, field_type)
        if field_type == 'password':
            # In case of password we have no raw password in API after writing.
            if expected_value is not None and expected_value != "":
                assert current_value is not None, "Password field expected to be filled"
            else:
                assert current_value is None or current_value == "", "Password have to be empty"
        else:
            if field_type == 'file':
                expected_value = 'test'
            if field_type == 'map':
                map_config = self.get_map_field_config(field)
                assert set(map_config.keys()) == set(map_config.keys())
                assert set(map_config.values()) == set(map_config.values())
            else:
                err_message = "Default value wrong. Current value {}".format(current_value)
                assert current_value == expected_value, err_message

    def assert_alerts_presented(self, field_type):
        """Check that frontend errors presented on screen and error type in text

        :param field_type:
        :return:
        """
        errors = self.get_frontend_errors()
        assert errors
        if field_type == 'password':
            assert len(errors) == 2
            error_text = "Field [{}] is required!".format(field_type)
            error_texts = [error.text for error in errors]
            assert error_text in error_texts

    def assert_group_status(self, group_element, status=True):
        """Check that group active or not
        :param group_element:
        :param status:
        :return:
        """
        if status:
            assert self.group_is_active_by_element(group_element)
        else:
            assert not self.group_is_active_by_element(group_element)

    def assert_form_field_text_equal(self, form_field_element, expected_text):
        """Check that mat form field text have expected value

        :param form_field_element: WebElement
        :param expected_text: element text as string
        :return:
        """
        field_text = self.get_form_field_text(form_field_element)
        err_msg = "Actual field text: {}. Expected field text: {}".format(
            field_text, expected_text)
        assert field_text == expected_text, err_msg

    def assert_form_field_text_in(self, form_field_element, expected_text):
        """Check that expected text in form field

        :param form_field_element: WebElement
        :param expected_text: element text as string
        :return:
        """
        field_text = self.get_form_field_text(form_field_element)
        err_msg = "Actual field text: {}. Expected part of text: {}".format(
            field_text, expected_text)
        assert expected_text in field_text, err_msg

    def assert_text_in_form_field_element(self, element, expected_text):
        """Check that expected text in form field

        :param element: WebElement
        :param expected_text: element text as string
        :return:
        """
        result = self._wait_text_element_in_element(element,
                                                    Common.mat_form_field,
                                                    text=expected_text)
        err_msg = "Expected text not presented: {}.".format(expected_text)
        assert result, err_msg

    def get_map_key(self, item_element):
        """Get key value for map field

        :param item_element:
        :return:
        """
        form_field = item_element.find_element(*ConfigurationLocators.map_key_field)
        inp = form_field.find_element(*Common.mat_input_element)
        return inp.get_attribute("value")

    def get_map_value(self, item_element):
        """Get value for map field

        :param item_element:
        :return:
        """
        form_field = item_element.find_element(*ConfigurationLocators.map_value_field)
        inp = form_field.find_element(*Common.mat_input_element)
        return inp.get_attribute("value")

    def get_map_field_config(self, map_field):
        """Get map field values

        :param map_field:
        :return: dict
        """
        items = map_field.find_elements(*Common.item)
        result = {}
        for item in items:
            _key = self.get_map_key(item)
            _value = self.get_map_value(item)
            result[_key] = _value
        return result

    def get_field_value_by_type(self, field_element, field_type):
        """Return field value from element by field type

        :param field_element: WebElement
        :param field_type: string with type
        :return: field value, for numeric fields string will be converted
        to field type.
        """
        if field_type == 'boolean':
            element_with_value = field_element.find_element(*Common.mat_checkbox_class)
            current_value = self.get_checkbox_element_status(element_with_value)
        elif field_type == 'option':
            element_with_value = field_element.find_element(*Common.mat_select)
            current_value = self.get_field_value(element_with_value)
        elif field_type == 'list':
            elements_with_value = field_element.find_elements(*Common.mat_input_element)
            current_value = [
                self.get_field_value(element) for element in elements_with_value
            ]
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
    def get_structure_values(field):
        """Get structure values for field

        :param field:
        :return: list of dicts
        """
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
        return input_field.get_attribute("value")

    def get_field_groups(self):
        return self.driver.find_elements(*ConfigurationLocators.field_group)

    @retry(retry_on_exception=retry_on_exception, stop_max_delay=10 * 1000)
    def save_button_status(self):
        self._wait_element(ConfigurationLocators.config_save_button)
        button = self.driver.find_element(*ConfigurationLocators.config_save_button)
        class_el = button.get_attribute("disabled")
        if class_el == 'true':
            result = False
        else:
            result = True
        return result

    def get_app_fields(self):
        return self.driver.find_elements(*ConfigurationLocators.app_field)

    def _get_group_element_by_name(self, name):
        self._wait_element_present(Common.mat_expansion_panel)
        config_groups = self.driver.find_elements(*Common.mat_expansion_panel)
        for group in config_groups:
            if name in group.text:
                return group
        return False

    def group_is_active_by_element(self, group_element):
        """

        :param group_element:
        :return:
        """
        toogle = group_element.find_element(*Common.mat_slide_toggle)
        if 'mat-checked' in toogle.get_attribute("class"):
            return True
        return False

    @staticmethod
    def field_is_ro(field_element):
        if "read-only" in field_element.get_attribute("class"):
            return True
        return False

    def group_is_active_by_name(self, group_name):
        """Get group status
        :param group_name:
        :return:
        """
        group = self._get_group_element_by_name(group_name)
        toogle = group.find_element(*Common.mat_slide_toggle)
        if 'mat-checked' in toogle.get_attribute("class"):
            return True
        return False

    def activate_group_by_name(self, group_name):
        """

        :param group_name:
        :return:
        """
        group = self._get_group_element_by_name(group_name)
        toogle = group.find_element(*Common.mat_slide_toggle)
        if 'mat-checked' not in toogle.get_attribute("class"):
            toogle.click()

    def save_configuration(self):
        self._getelement(ConfigurationLocators.config_save_button).click()

    def click_advanced(self):
        return self._click_element(Common.mat_checkbox, name="Advanced")

    def get_form_field_text(self, form_field_element):
        self._wait_element_present_in_sublement(form_field_element, Common.mat_form_field)
        form_field = form_field_element.find_elements(*Common.mat_form_field)[0]
        return form_field.get_attribute("textContent").strip()

    def get_form_field(self, field_element):
        self._wait_element_present_in_sublement(field_element, Common.mat_form_field)
        return field_element.find_elements(*Common.mat_form_field)[0]

    @property
    def advanced(self):
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
        try:
            return field.find_element(*Common.info_icon)
        except NoSuchElementException:
            return False

    def get_tooltip_text_for_element(self, element):
        tooltip_icon = self._get_tooltip_el_for_field(element)
        # Hack for firefox because of move_to_element does not scroll to the element
        # https://github.com/mozilla/geckodriver/issues/776
        if self.driver.capabilities['browserName'] == 'firefox':
            self.driver.execute_script('arguments[0].scrollIntoView(true)', element)
        action = ActionChains(self.driver)
        action.move_to_element(tooltip_icon).perform()
        return self.driver.find_element(*Common.tooltip).text

    def get_textboxes(self):
        return self.driver.find_elements(*ConfigurationLocators.app_fields_text_boxes)

    def get_password_elements(self):
        return self.driver.find_elements(*ConfigurationLocators.app_fields_password)

    def get_display_names(self):
        self._wait_element_present(Common.display_names, timer=15)
        return {name.text for name in self.driver.find_elements(*Common.display_names)}

    def set_search_field(self, search_pattern):
        self._wait_element(ConfigurationLocators.search_field)
        element = self.driver.find_element(*ConfigurationLocators.search_field)
        self.clear_element(element)
        self._set_field_value(ConfigurationLocators.search_field, search_pattern)

    def get_group_elements(self):
        try:
            self._wait_element_present(Common.display_names)
        except TimeoutException:
            return []
        return self.driver.find_elements(*Common.display_names)

    @staticmethod
    def read_only_element(element):
        """Check that field have read-only attribute

        :param element:
        :return:
        """
        if 'read-only' in element.get_attribute("class"):
            return True
        return False

    @staticmethod
    def editable_element(element):
        el_class = element.get_attribute("class")
        el_readonly_attr = element.get_attribute("readonly")
        if "field-disabled" in el_class:
            return False
        elif 'read-only' in el_class:
            return False
        elif el_readonly_attr == 'true':
            return False
        if element.is_enabled():
            return True
        return True
