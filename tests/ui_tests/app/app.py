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

# Created by a1wen at 27.02.19

# pylint: disable=E0401, E0611, W0611, W0621

import os

import allure
from adcm_client.wrappers.docker import ADCM
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import ChromeOptions, FirefoxOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW

from tests.ui_tests.app.pages import Ui, ClustersList


class ADCMTest:

    __slots__ = ("opts", "capabilities", "driver", "ui", "adcm", "selenoid")

    def __init__(self, browser="Chrome"):
        self.opts = FirefoxOptions() if browser == "Firefox" else ChromeOptions()
        self.opts.headless = True
        self.opts.add_argument("--no-sandbox")
        self.opts.add_argument("--disable-extensions")
        self.opts.add_argument("--ignore-certificate-errors")
        self.opts.add_argument("--disable-gpu")
        self.opts.add_argument("--start-maximized")
        self.opts.add_argument("--enable-logging")
        self.opts.add_argument("--enable-automation")
        if browser == "Chrome":
            self.opts.add_argument("--window-size=1366,768")
        else:
            self.opts.add_argument("--width=1366")
            self.opts.add_argument("--height=768")
        self.capabilities = self.opts.capabilities.copy()
        self.capabilities["acceptSslCerts"] = True
        self.capabilities["acceptInsecureCerts"] = True
        self.capabilities["goog:loggingPrefs"] = {"browser": "ALL", "performance": "ALL"}
        self.selenoid = {
            "host": os.environ.get("SELENOID_HOST"),
            "port": os.environ.get("SELENOID_PORT", "4444"),
        }
        self.driver = None
        self.ui = None
        self.adcm = None

    @allure.step("Init driver")
    def create_driver(self):
        if self.selenoid["host"]:
            self.driver = webdriver.Remote(
                command_executor=f"http://{self.selenoid['host']}:{self.selenoid['port']}/wd/hub",
                options=self.opts,
                desired_capabilities=self.capabilities,
            )
        else:
            self.driver = (
                webdriver.Firefox(options=self.opts, desired_capabilities=self.capabilities)
                if self.capabilities["browserName"] == "firefox"
                else webdriver.Chrome(options=self.opts, desired_capabilities=self.capabilities)
            )
        self.driver.implicitly_wait(1)
        self.ui = Ui(self.driver)

    @allure.step("Attache ADCM")
    def attache_adcm(self, adcm: ADCM):
        self.adcm = adcm

    @allure.step("Get Clusters List")
    def clusters_page(self):
        return ClustersList(self)

    def wait_for(self, condition: EC, locator: tuple, timer=5):
        def get_element(el):
            return WDW(self.driver, timer).until(condition(el))

        return get_element(locator)

    @allure.step("Wait for element displayed")
    def wait_element_present(self, locator: tuple):
        return self.wait_for(EC.presence_of_element_located, locator)

    @allure.step("Wait for contains url: {url}")
    def contains_url(self, url: str, timer=5):
        return WDW(self.driver, timer).until(EC.url_contains(url))

    @allure.step("Open base page")
    def base_page(self):
        self.driver.get(self.adcm.url)

    @allure.step("Open a new tab")
    def new_tab(self):
        self.driver.execute_script("window.open('');")
        # close all tabs
        for tab in self.driver.window_handles[:-1]:
            self.driver.switch_to.window(tab)
            self.driver.close()
        # set focus to the newly created window
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.driver.delete_all_cookies()
        try:
            self.driver.execute_script("window.localStorage.clear();")
        except WebDriverException:
            # we skip JS error here since we have no simple way to detect localStorage availability
            pass

    def destroy(self):
        self.driver.quit()
