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

# Created by a1wen at 28.02.19
# Stolen from Selene
from selenium.webdriver.common.by import By


def by(css_selector):
    return by_css(css_selector)


def by_css(css_selector):
    return By.CSS_SELECTOR, css_selector


def by_name(name):
    return By.NAME, name


def by_class(name):
    return By.CLASS_NAME, name


def by_link_text(text):
    return By.LINK_TEXT, text


def by_partial_link_text(partial_text):
    return By.PARTIAL_LINK_TEXT, partial_text


def by_xpath(xpath):
    return By.XPATH, xpath


def by_tag(tag):
    return By.TAG_NAME, tag
