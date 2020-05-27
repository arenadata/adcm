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
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, InvalidElementStateException,\
    ElementClickInterceptedException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW
from selenium.webdriver.common.action_chains import ActionChains
from tests.ui_tests.app.locators import Menu, Common, Cluster, Provider, Host, Service
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
        WDW(self.driver, timer).until(EC.presence_of_element_located(locator))
        return self.driver.find_element(*locator)

    def _wait_element_present_in_sublement(self, subel, locator: tuple, timer=5):
        WDW(subel, timer).until(EC.presence_of_element_located(locator))
        return subel.find_element(*locator)

    def _wait_text_element_in_element(self, element, locator: tuple, timer=5, text=""):
        WDW(element, timer).until(EC.text_to_be_present_in_element(locator, text))
        return element.find_element(*locator)

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
        return element

    def set_element_value_in_input(self, element, value):
        self._wait_element_present_in_sublement(element, Common.mat_input_element)
        input_element = element.find_element(*Common.mat_input_element)
        self.set_element_value(input_element, value)
        return element

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
        return element

    def clear_input_element(self, element):
        self._wait_element_present_in_sublement(element, Common.mat_input_element)
        input_element = element.find_element(*Common.mat_input_element)
        self.clear_element(input_element)
        return element

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
        WDW(self.driver, timer).until(EC.url_contains(url))
        return self.driver.current_url

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

    def _click_button_element(self, button):
        """Click element
        :param button:
        :return: bool
        """
        try:
            button.click()
            return True
        except (NoSuchElementException, ElementClickInterceptedException):
            self.driver.execute_script("arguments[0].click();", button)
            return True

    def _click_button_by_name(self, button_name, by, locator):
        self._wait_element_present(by, locator)
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
        self._contains_url('admin', 15)
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
