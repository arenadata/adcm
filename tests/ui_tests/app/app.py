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
from selenium import webdriver
from selenium.webdriver import (ChromeOptions, FirefoxOptions)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW
from selenium.webdriver.common.keys import Keys

from tests.library import steps
from tests.ui_tests.app.pages import Ui, ClustersList
from tests.ui_tests.app.helpers import urls

from adcm_client.wrappers.docker import ADCM


class ADCMTest:

    __slots__ = ('opts', 'capabilities', 'driver', 'ui', 'adcm', '_client', 'selenoid')

    def __init__(self, browser='Chrome'):
        self.opts = FirefoxOptions() if browser == 'Firefox' else ChromeOptions()
        self.opts.headless = True
        self.opts.add_argument('--no-sandbox')
        self.opts.add_argument('--disable-extensions')
        self.opts.add_argument('--ignore-certificate-errors')
        self.opts.add_argument('--disable-gpu')
        self.opts.add_argument("--start-maximized")
        self.opts.add_argument("--enable-logging")
        self.opts.add_argument("--enable-automation")
        self.capabilities = self.opts.capabilities.copy()
        self.capabilities['acceptSslCerts'] = True
        self.capabilities['acceptInsecureCerts'] = True
        self.capabilities['goog:loggingPrefs'] = {'browser': 'ALL', 'performance': 'ALL'}
        self.selenoid = {'host': os.environ.get("SELENOID_HOST"),
                         'port': os.environ.get("SELENOID_PORT", "4444")}
        self.driver = None
        self.ui = None
        self.adcm = None
        self._client = None

    def create_driver(self):
        if self.selenoid['host']:
            self.driver = webdriver.Remote(
                command_executor=f"http://{self.selenoid['host']}:{self.selenoid['port']}/wd/hub",
                options=self.opts,
                desired_capabilities=self.capabilities)
        else:
            self.driver = webdriver.Firefox(options=self.opts,
                                            desired_capabilities=self.capabilities) \
                if self.capabilities['browserName'] == 'firefox' \
                else webdriver.Chrome(options=self.opts,
                                      desired_capabilities=self.capabilities)
        self.driver.set_window_size(1800, 1000)
        self.driver.implicitly_wait(1)
        self.ui = Ui(self.driver)

    def attache_adcm(self, adcm: ADCM):
        self.adcm = adcm
        self._client = adcm.api.objects

    def navigate_to(self, page: urls):
        self.driver.get(page)
        # return ?Page()

    def clusters_page(self):
        return ClustersList(self)

    def create_cluster(self):
        return steps.create_cluster(self._client)['name']

    def create_host(self, fqdn):
        steps.create_host_w_default_provider(self._client, fqdn)
        return fqdn

    def create_provider(self):
        return steps.create_hostprovider(self._client)['name']

    def wait_for(self, condition: EC, locator: tuple, timer=5):
        def get_element(el):
            return WDW(self.driver, timer).until(condition(el))
        return get_element(locator)

    def wait_element_present(self, locator: tuple):
        return self.wait_for(EC.presence_of_element_located, locator)

    def contains_url(self, url: str, timer=5):
        return WDW(self.driver, timer).until(EC.url_contains(url))

    def base_page(self):
        self.driver.get(self.adcm.url)

    def new_tab(self):
        body = self.driver.find_element_by_tag_name("body")
        body.send_keys(Keys.CONTROL + 't')

    def close_tab(self):
        body = self.driver.find_element_by_tag_name("body")
        body.send_keys(Keys.CONTROL + 'w')

    def destroy(self):
        self.driver.quit()
