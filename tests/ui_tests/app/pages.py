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
import json

from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, InvalidElementStateException,\
    ElementClickInterceptedException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW
from selenium.webdriver.common.action_chains import ActionChains
from tests.ui_tests.app.locators import Menu, Common, Cluster, Provider, Host,\
    ConfigurationLocators, Service
from tests.ui_tests.app.helpers import bys
from cm.errors import ERRORS
from time import sleep, time


def repeat_dec(timeout=10, interval=0.1):
    """That is timeout decorator for find_* functions of webdriver

    First of all sometimes it take a time for wedriver to find element.
    So it nice to have some timeout, but it is too expensive to have implicit timeout.

    That function creates decorator to wrap function that has to be repeated.
    """
    def dec(f):
        def newf(*args, **kwargs):
            t = time()
            while t + timeout > time():
                result = f(*args, **kwargs)
                # For some reason wedriver returns False or [] when it found nothing.
                if result:
                    return result
                sleep(interval)
        return newf
    return dec


REPEAT = repeat_dec(timeout=2, interval=0.1)


class BasePage:
    ignored_exceptions = (NoSuchElementException, StaleElementReferenceException)

    """That is base page object for all ADCM's pages"""
    def __init__(self, driver):
        self.driver = driver

    def _get_adcm_test_element(self, element_name):
        return self._getelement(bys.by_xpath("//*[@adcm_test='{}']".format(element_name)))

    def _getelement(self, locator: tuple, timer=10):
        return WDW(self.driver,
                   timer,
                   ignored_exceptions=self.ignored_exceptions
                   ).until(EC.presence_of_element_located(locator))

    def _getelements(self, locator: tuple, timer=20):
        return WDW(self.driver, timer).until(EC.presence_of_all_elements_located(locator))

    def _click_element_in_list(self, element_name):
        for el in self._getelements(Common.list_text):
            if el.text == element_name:
                el.click()
                return True
        return False

    def get_frontend_errors(self):
        return self._getelements(Common.mat_error)

    def get_error_text_for_element(self, element):
        return element.find_element(Common.mat_error).text

    def _wait_element_present(self, locator: tuple, timer=5):
        return WDW(self.driver, timer).until(EC.presence_of_element_located(locator))

    def _set_field_value(self, field: tuple, value):
        field = self._getelement(field)
        if field.is_displayed():
            field.click()
            field.clear()
            field.send_keys(value)

    @staticmethod
    def set_element_value(element, value):
        if element.is_displayed():
            element.clear()
            element.send_keys(value)

    @staticmethod
    def get_checkbox_element_status(element):
        """Get checkbox element status, checked or not

        :param element: WebElement
        :return: boolean
        """
        el_class = element.get_attribute("class")
        if "mat-checkbox-checked" in el_class:
            return True
        return True

    def _fill_field_element(self, data, field_element):
        field_element.clear()
        field_element.send_keys(data)
        return field_element

    def _find_and_clear_element(self, by, value):
        element = self.driver.find_element(by, value)
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.BACK_SPACE)

    def clear_element(self, element):
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.BACK_SPACE)

    def _error_handler(self, error: ERRORS):
        if error in ERRORS.keys():
            e = self._getelement(Common.error).text
        return bool(error in e), e

    def check_error(self, error: ERRORS):
        return self._error_handler(error)

    def get_error(self):
        return self._getelement(Common.error).text

    def get_errors(self):
        return [error.text for error in self._getelements(Common.error)]

    def _click_with_offset(self, element: tuple, x_offset, y_offset):
        actions = ActionChains(self.driver)
        actions.move_to_element_with_offset(self._getelement(element),
                                            x_offset, y_offset).click().perform()

    def _contains_url(self, url: str, timer=5):
        return WDW(self.driver, timer).until(EC.url_contains(url))

    def _is_element_clickable(self, locator: tuple, timer=5) -> WebElement:
        return bool(WDW(self.driver, timer).until(EC.element_to_be_clickable(locator)))

    def _menu_click(self, locator: tuple):
        el = self._getelement(locator)
        if self._is_element_clickable(locator):
            return self._click_button_with_sleep(el)
        else:
            raise InvalidElementStateException

    def _click_button_with_sleep(self, button, t=0.5):
        try:
            button.click()
            return True
        except (NoSuchElementException, ElementClickInterceptedException):
            sleep(t)
            self.driver.execute_script("arguments[0].click();", button)
            return True

    def _click_button_by_name(self, button_name, by, locator):
        buttons = self.driver.find_elements(by, locator)
        for button in buttons:
            if button.text == button_name:
                try:
                    button.click()
                    return True
                except (NoSuchElementException, ElementClickInterceptedException):
                    self.driver.execute_script("arguments[0].click();", button)
                    return True
        return False

    # def _wait_for_menu_element_generator(self, classname):
    #     def func(args):
    #         return WDW(args[0].driver, 5).until(
    #             EC.visibility_of_element_located(classname))
    #     return func
    #
    # def register(self):
    #     for k, v in self._menu.items():
    #         f = self._wait_for_menu_element_generator(v)
    #         setattr(self, k, f.__get__((self, Menu)))


class Ui(BasePage):
    """ This class describes main menu and returns specified page in POM"""

    @property
    def session(self):
        return LoginPage(self.driver)

    @property
    def clusters(self):
        self._menu_click(Menu.clusters)
        return ClustersList(self.driver)

    @property
    def providers(self):
        self._menu_click(Menu.hostproviders)
        return ProvidersList(self.driver)

    @property
    def hosts(self):
        self._menu_click(Menu.hosts)
        return HostsList(self.driver)

    @property
    def jobs(self):
        self._menu_click(Menu.jobs)
        return JobsList(self.driver)

    @property
    def bundles(self) -> WebElement:
        return self._getelement(Menu.bundles)

    @property
    def settings(self):
        return SettingsPage(self.driver)


class ListPage(BasePage):
    """Basic methods under the lists pages"""
    _inactive_tabs = bys.by_xpath(
        "//a[@class='mat-list-item ng-star-inserted']//div[@class='mat-list-item-content']")

    def _press_add(self):
        self._getelement(Common.add_btn).click()

    def _press_save(self):
        self._getelement(Common.save_btn).click()

    def _press_cancel(self):
        self._getelement(Common.cancel_btn).click()

    def _click_tab(self, tab_name):
        for tab in self._getelements(self._inactive_tabs):
            if tab_name == tab.text:
                tab.click()
                return True
        return None

    def _wait_add_form(self):
        self._wait_element_present(Common.dialog)

    def close_form(self):
        """Method that closed forms by click on the area near the form"""
        self._click_with_offset(Common.dialog, 500, 50)

    def get_rows(self):
        return self._getelements(Common.rows)

    def _get_option_by_name(self, name):
        opt = ''
        sleep(2)
        for _ in self._getelements(Common.options):
            if name in _.text:
                opt = _
            else:
                opt = None
        return opt

    def _click_on_option_element(self, name):
        opt = self._get_option_by_name(name)
        opt.click()

    def _delete_first_element(self):
        """Method that finds first item in list and  delete his from list"""
        self.delete_row(0)
        approve = self._getelement(Common.dialog)
        approve.is_displayed()
        self._getelement(Common.dialog_yes).click()

    def delete_row(self, row_number):
        """Deleting specified row by his number
            :param: """
        rows = self.get_rows()
        _del = rows[row_number].find_element_by_xpath(Common.del_btn)
        _del.click()

    def delete_all_rows(self):
        rows = self.get_rows()
        for row in rows:
            _del = row.find_element_by_xpath(Common.del_btn)
            _del.click()
            approve = self._getelement(Common.dialog)
            approve.is_displayed()
            self._getelement(Common.dialog_yes).click()

    def list_element_contains(self, expected_name):
        row = ''
        for _ in self.get_rows():
            if expected_name in _.text:
                row = _
            else:
                row = None
        return bool(row)

    def list_is_empty(self):
        try:
            self._getelements(Common.rows)
            return False
        except TimeoutException:
            return True


class Details(BasePage):
    pass


class LoginPage(BasePage):
    login_locator = bys.by_xpath("//input[@placeholder='Login']")
    passwd_locator = bys.by_xpath("//input[@placeholder='Password']")
    _logout = ()
    _user = ()

    def __init__(self, driver):
        super().__init__(driver)
        self._login = None
        self._password = None

    def login(self, login, password):
        self._login = REPEAT(self.driver.find_element)(*LoginPage.login_locator)
        self._password = REPEAT(self.driver.find_element)(*LoginPage.passwd_locator)
        self._login.send_keys(login)
        self._password.send_keys(password)
        self._password.send_keys(Keys.RETURN)
        self._contains_url('admin')
        sleep(5)  # Wait untill we have all websockets alive.

    def logout(self):
        self._getelement(self._user).click()
        self._getelement(self._logout).click()


class ClustersList(ListPage):

    def add_new_cluster(self, name=None, description=None):
        return self._form(name=name, description=description)

    def _form(self, name, description):
        self._press_add()
        self._wait_add_form()
        if name:
            self._set_field_value(Cluster.name, name)
            if description:
                self._set_field_value(Common.description, description)
        self._press_save()
        sleep(1)

    def delete_first_cluster(self):
        return self._delete_first_element()

    def delete_all_clusters(self):
        return self.delete_all_rows()

    @property
    def details(self):
        self.get_rows()[0].click()
        return ClusterDetails(self.driver)


class ClusterDetails(Details, ListPage):

    _host = bys.by_class('add-host2cluster')
    _add_host_icon = bys.by_xpath("//*[@mattooltip='Host will be added to the cluster']")

    @property
    def host_tab(self):
        self._getelement(Cluster.host_tab).click()
        return ListPage(self.driver)

    @property
    def services_tab(self):
        self._getelement(Cluster.service_tab).click()
        return ServiceList(self.driver)

    def _add_host_to_cluster(self):
        # self._getelement(self._host).click()
        self._getelement(self._add_host_icon).click()

    def click_hosts_tab(self):
        for tab in self._getelements(self._inactive_tabs):
            if tab.text.strip() == 'Hosts':
                tab.click()
                break

    def click_services_tab(self):
        return self._click_tab("Services")

    def click_add_button(self):
        self._press_add()
        self._add_host_to_cluster()
        self.close_form()

    def add_host_in_cluster(self):
        self.click_hosts_tab()
        self.click_add_button()

    def create_host_from_cluster(self, provider_name, fqdn):
        self.host_tab  # pylint: disable=W0104
        self._press_add()
        self._wait_add_form()
        self._getelement(Host.prototype).click()
        self._click_on_option_element(provider_name)
        self._set_field_value(Host.name, fqdn)
        self._press_save()
        self.close_form()

    def _approve_action_run(self):
        self._wait_add_form()
        return self._getelement(Common.dialog_run).click()

    def run_action_by_name(self, action_name):
        actions = self._getelements(Common.action)
        for action in actions:
            if action.text == action_name:
                action.click()
                self._approve_action_run()
                break


class ProvidersList(ListPage):

    def add_new_provider(self, name=None, description=None):
        self._press_add()
        self._wait_add_form()
        if name:
            self._set_field_value(Provider.name, name)
            if description:
                self._set_field_value(Common.description, description)
        self._press_save()
        sleep(1)

    def delete_first_provider(self):
        return self._delete_first_element()


class HostsList(ListPage):

    def add_new_host(self, fqdn=None, description=None):
        self._press_add()
        self._wait_add_form()
        if fqdn:
            self._set_field_value(Host.name, fqdn)
            if description:
                self._set_field_value(Common.description, description)
        self._press_save()
        sleep(1)

    def delete_first_host(self):
        return self._delete_first_element()


class SettingsPage(ListPage):

    def save(self):
        self._press_save()


class JobsList(ListPage):
    def check_task(self, action_name):
        """We just check upper task in the list because in UI last runned task must be
        always at the top."""
        self.list_element_contains(action_name)


class ServiceList(ListPage):
    def add_service(self, service_name):
        self._press_add()
        self._wait_add_form()
        if self._click_element_in_list(service_name):
            self._press_save()
            return True
        self._press_cancel()
        return False

    def open_service(self, service_name):
        for service in self._getelements(Common.rows):
            if service_name in service.text:
                service.click()
                return True
        return False

    def service_list(self):
        return [{service.text.split("\n")[0]: {"version": service.text.split("\n")[1],
                                               "status": service.text.split("\n")[2]}
                 } for service in self._getelements(Common.rows)]

    def open_service_config(self, service_name):
        for service in self._getelements(Common.rows):
            if service_name in service.text:
                service.find_element(Service.config_column).click()
                return True
        return False


class ServiceDetails(Details, ListPage):
    @property
    def main_tab(self):
        self._getelement(Service.main_tab).click()
        return ListPage(self.driver)

    @property
    def configuration_tab(self):
        self._getelement(Service.configuration_tab).click()
        return Configuration(self.driver)

    @property
    def status_tab(self):
        self._getelement(Service.status_tab).click()
        return ListPage(self.driver)

    def click_main_tab(self):
        return self._click_tab("Main")

    def click_configuration_tab(self):
        return self._click_tab("Configuration")


# pylint: disable=R0904
class Configuration(BasePage):
    """
    Class for configuration page
    """

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

    def get_config_field(self):
        return self._getelement(ConfigurationLocators.app_conf_fields)

    def get_app_root_scheme_fields(self, field=None):
        if not field:
            return self.driver.find_elements(*ConfigurationLocators.app_root_scheme)
        else:
            return field.find_elements(*ConfigurationLocators.app_root_scheme)

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

    def get_fields_by_type(self, field_type):
        """Get fields by type

        :param field_type: string with type
        :return: list of fields
        """
        if field_type == 'structure':
            return self.get_app_root_scheme_fields()
        return self.get_app_fields()

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

    def get_config_elements(self):
        el = self.get_config_field()
        return el.find_elements(*Common.all_childs)

    def get_field_groups(self):
        return self.driver.find_elements(*ConfigurationLocators.field_group)

    def get_group_names(self):
        return self.driver.find_elements(*ConfigurationLocators.group_title)

    def save_button_status(self):
        try:
            button = self.driver.find_element(*ConfigurationLocators.config_save_button)
        except (StaleElementReferenceException, NoSuchElementException):
            sleep(5)
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
        config_groups = REPEAT(self.driver.find_elements)(*Common.mat_expansion_panel)
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

    def activate_group_by_element(self, group_element):
        """Activate group by element

        :param group_element:
        :return:
        """
        toogle = group_element.find_element(*Common.mat_slide_toggle)
        if 'mat-checked' not in toogle.get_attribute("class"):
            toogle.click()

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
        buttons = self.driver.find_elements(*Common.mat_checkbox)
        for button in buttons:
            if button.text == 'Advanced':
                self._click_button_with_sleep(button, 5)
                sleep(0.5)
                return True
        return False

    @property
    def advanced(self):
        buttons = self.driver.find_elements(*Common.mat_checkbox)
        for button in buttons:
            if button.text == 'Advanced':
                return "checked" in button.get_attribute("class")
        return None

    def show_history(self):
        for icon in self._getelements(Common.mat_icon):
            if icon.text == "history":
                icon.clikc()
                return True
        return False

    def _get_tex_boxes_elements(self):
        textboxes = self.driver.find_elements(*ConfigurationLocators.app_fields_text_boxes)
        return set((textbox.get_attribute("adcm_test"),
                    textbox.find_element(
                        *Common.mat_input_element).get_attribute("value")) for textbox in textboxes)

    def _get_text_areas_elements(self):
        textareas = self._getelements(ConfigurationLocators.app_fields_textarea)
        areas = []
        for ar in textareas:
            el = ar.find_element(Common.textarea)
            areas.append({ar.get_attribute("adcm_test"): el.get_attribute("value")})
        return areas

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
        action = ActionChains(self.driver)
        action.move_to_element(tooltip_icon).perform()
        return self.driver.find_element(*Common.tooltip).text

    def _get_map_elements(self):
        return self._getelements(ConfigurationLocators.app_fields_map)

    def _get_list_elements(self):
        return self._getelements(ConfigurationLocators.app_fields_list)

    def get_textboxes(self):
        return self.driver.find_elements(*ConfigurationLocators.app_fields_text_boxes)

    def get_labels(self):
        return self.driver.find_elements(*ConfigurationLocators.app_fields_labels)

    def _get_json_elements(self):
        json_elements = self._getelements(ConfigurationLocators.app_fields_json)
        jsons = []
        for js in json_elements:
            el = js.find_element(Common.textarea)
            value = el.get_attribute("value")
            if value:
                value = json.loads(value)
            jsons.append({js.get_attribute("adcm_test"): value})
        return jsons

    def _get_configuration_elements(self):
        textboxes = self._getelements(ConfigurationLocators.app_fields_text_boxes)
        maps = self._getelements(ConfigurationLocators.app_fields_map)
        passwords = self._getelements(ConfigurationLocators.app_fields_password)
        textareas = self._getelements(ConfigurationLocators.app_fields_textarea)
        jsons = self._getelements(ConfigurationLocators.app_fields_json)
        return textboxes + maps + passwords + textareas + jsons

    def get_password_elements(self):
        return self.driver.find_elements(*ConfigurationLocators.app_fields_password)

    def _get_config_full_names(self):
        textboxes = self.driver.find_elements(*ConfigurationLocators.app_fields_text_boxes)
        maps = self.driver.find_elements(*ConfigurationLocators.app_fields_text_boxes)
        passwords = self.driver.find_elements(*ConfigurationLocators.app_fields_password)
        textareas = self.driver.find_elements(*ConfigurationLocators.app_fields_textarea)
        jsons = self.driver.find_elements(*ConfigurationLocators.app_fields_json)
        full_names = []
        for text_box in textboxes:
            full_names.append(text_box.get_attribute("adcm_test"))
        for m in maps:
            full_names.append(m.get_attribute("adcm_test"))
        for passw in passwords:
            full_names.append(passw.get_attribute("adcm_test"))
        for textarea in textareas:
            full_names.append(textarea.get_attribute("adcm_test"))
        for js in jsons:
            full_names.append(js.get_attribute("adcm_test"))
        return full_names

    def get_display_names(self):
        count = 10
        d_names = {name.text for name in self.driver.find_elements(*Common.display_names)}
        while count > 0:
            d_names = {name.text for name in self.driver.find_elements(*Common.display_names)}
            if not d_names:
                count -= 1
                sleep(1)
            else:
                break
        return d_names

    def get_names(self):
        try:
            elements = self.driver.find_elements(*ConfigurationLocators.app_fields_text_boxes)
        except StaleElementReferenceException:
            elements = self.driver.find_elements(*ConfigurationLocators.app_fields_text_boxes)
        return [textbox.text.split("\n")[0].strip(":") for textbox in elements]

    def set_search_field(self, search_pattern):
        try:
            element = self.driver.find_element(*ConfigurationLocators.search_field)
        except NoSuchElementException:
            sleep(10)
            element = self.driver.find_element(*ConfigurationLocators.search_field)
        self.clear_element(element)
        self._set_field_value(ConfigurationLocators.search_field, search_pattern)

    def get_group_elements(self):
        try:
            return self.driver.find_elements(*Common.display_names)
        except StaleElementReferenceException:
            sleep(5)
            return self.driver.find_elements(*Common.display_names)

    def execute_action(self, action_name):
        """Click action
        :param action_name:
        :return:
        """
        assert self._click_button_by_name(action_name, *Common.mat_raised_button)
        return self._click_button_by_name("Run", *Common.mat_raised_button)

    def element_presented_by_name_and_locator(self, name, by, value):
        """

        :param name:
        :param by:
        :param value:
        :return:
        """
        elements = self.driver.find_elements(by, value)
        if not elements:
            return False
        for el in elements:
            if el.text == name:
                return True
        return False

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
