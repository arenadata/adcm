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

"""Utils for UI ADCM tests"""

# pylint: disable=too-many-ancestors
import os
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional, Sized, Tuple, TypeVar, Union

import allure
import requests
from adcm_client.objects import ADCMClient, Cluster, Component, Provider, Service
from adcm_pytest_plugin.utils import random_string, wait_until_step_succeeds
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW

from tests.ui_tests.app.app import ADCMTest

T = TypeVar("T")
F = TypeVar("F")


def _prepare_cluster(sdk_client: ADCMClient, path) -> Cluster:
    bundle = sdk_client.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-1:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    return cluster


@allure.step("Wait for a new window after action")
@contextmanager
def wait_for_new_window(driver: WebDriver, wait_time: int = 10):
    """Wait a new window is opened after some action"""

    tabs = driver.window_handles
    yield
    WDW(driver, wait_time).until(EC.new_window_is_opened(tabs))
    tabs = driver.window_handles
    driver.switch_to.window(tabs[len(tabs) - 1])


@allure.step("Close current tab")
def close_current_tab(driver: WebDriver):
    """Close current tab and switch to first tab"""

    tabs = driver.window_handles
    driver.close()
    driver.switch_to.window(tabs[0])


def check_rows_amount(page, expected_amount: int, table_page_num: int):
    """
    Check rows count is equal to expected
    :param page: Page object with table attribute
    :param expected_amount: Expected amount of rows in table on that page
    :param table_page_num: Number of the current page (for assertion error message)
    """
    assert (
        row_count := page.locators.row_count
    ) == expected_amount, f"Page #{table_page_num} should contain {expected_amount}, not {row_count}"


def ignore_flaky_errors(func: Callable):
    """
    Use it as decorator to catch flaky exceptions and raise Assertion messages instead.
    Use it only with `wait_until_step_succeeds` or something similar.
    """

    def wrapped(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except (StaleElementReferenceException, NoSuchElementException) as e:
            raise AssertionError(f"Got a flaky error: {e}") from e

    return wrapped


# !===== UI Information Comparator Function =====!


def is_equal(first_value: T, second_value: T) -> bool:
    """Check if two values are equal (==)"""
    return first_value == second_value


def is_empty(first_value: T) -> bool:
    """Check if first value is empty (=='')"""
    return first_value == ""


def is_not_empty(first_value: T) -> bool:
    """Check if first value is not empty (!='')"""
    return first_value != ""


def wait_and_assert_ui_info(
    expected_values: Dict[
        str,
        Union[
            Union[T, Callable[[T], bool]],
            Tuple[T, Callable[[T, T], bool]],
        ],
    ],
    get_info_func: Union[Callable[[Any], F]],
    get_info_kwargs: Optional[dict] = None,
    timeout: Union[int, float] = 5,
    period: Union[int, float] = 0.5,
):
    """
    Wait for some information on UI to be correct.
    Use it to avoid getting data from UI a bit earlier than it is fully loaded.

    As dict value for `expected_values` argument you can provide:

    - simple value to pass it to "is_equal" function as expected value;
    - tuple with expected value and callable that takes two arguments;
    - callable that takes exactly 1 argument (actual value).
    Callable should return bool and in case only callable is provided
    it's name is used in assertion message.

    :param expected_values: Dictionary with values that are expected to be found
                            in UI information object.
    :param get_info_func: Function to get UI information object.
    :param get_info_kwargs: Dictionary with keyword arguments to pass to `get_info_func`.
    :param timeout: Timeout for retries.
    :param period: Period between retries.
    """
    get_info_kwargs = get_info_kwargs or {}
    human_key_names = {k: k.replace("_", " ").capitalize() for k in expected_values.keys()}

    @ignore_flaky_errors
    def _check_info_from_ui():
        ui_info: F = get_info_func(**get_info_kwargs)
        # to make assertion message more verbal
        ui_info_classname = ui_info.__class__.__name__
        for key, value in expected_values.items():
            actual_value = ui_info[key] if isinstance(ui_info, dict) else getattr(ui_info, key)
            # we may want if out of loop someday
            if callable(value):
                # expected callable with 1 argument like 'is_empty', etc.
                compare_func = value
                assert compare_func(actual_value), (
                    f"{human_key_names[key]} in {ui_info_classname} "
                    f'failed to pass check "{compare_func.__name__}", '
                    f"actual value is {actual_value}"
                )
                return
            if isinstance(value, tuple):
                expected_value, compare_func = value
            else:
                expected_value = value
                compare_func = is_equal
            assert compare_func(actual_value, expected_value), (
                f"{human_key_names[key]} in {ui_info_classname} " f"should be {expected_value}, not {actual_value}"
            )

    with allure.step("Check information is correct on UI"):
        wait_until_step_succeeds(_check_info_from_ui, timeout=timeout, period=period)


def wrap_in_dict(key: str, function: Callable) -> Callable:
    """
    Helper to use `wait_and_assert_ui_info` with functions that doesn't return dict-like value.

    It "changes" return type of function by creating lambda returning dict
    """
    return lambda *args, **kwargs: {key: function(*args, **kwargs)}


# !===== Helpful stuff =====!


def check_host_value(key: str, actual_value, expected_value):
    """
    Assert that actual value equals to expected value
    Argument `key` is used in failed assertion message
    """
    assert actual_value == expected_value, f"Host {key} should be {expected_value}, not {actual_value}"


def assert_enough_rows(required_row_num: int, row_count: int):
    """
    Assert that row "is presented" by comparing row index and amount of rows
    Provide row as index (starting with 0)
    """
    assert (
        required_row_num + 1 <= row_count
    ), f"Table has only {row_count} rows when row #{required_row_num} was requested"


@allure.step("Wait file {filename} was downloaded to {dirname} or directly to selenium")
def wait_file_is_presented(
    filename: str,
    app_fs: ADCMTest,
    dirname: os.PathLike,
    timeout: Union[int, float] = 30,
    period: Union[int, float] = 1,
):
    """Checks if file is presented in directory"""
    if app_fs.selenoid["host"]:
        dir_url = f'http://{app_fs.selenoid["host"]}:{app_fs.selenoid["port"]}/download/{app_fs.driver.session_id}'
        file_url = f"{dir_url}/{filename}"

        def _check_file_is_presented():
            response = requests.get(file_url)
            assert (
                response.status_code < 400
            ), f"Request for file ended with {response.status_code}, file request text: {response.text}."

    else:

        def _check_file_is_presented():
            assert filename in os.listdir(dirname), f"File {filename} not found in {dirname}"

    wait_until_step_succeeds(_check_file_is_presented, timeout=timeout, period=period)


@contextmanager
def expect_rows_amount_change(get_all_rows: Callable[[], Sized]):
    """Waits for row count to be changed"""
    current_amount = len(get_all_rows())

    yield

    @ignore_flaky_errors
    def _check_rows_amount_is_changed():
        assert len(get_all_rows()) != current_amount, "Amount of rows on the page hasn't changed"

    wait_until_step_succeeds(_check_rows_amount_is_changed, period=1, timeout=10)


# common steps


@allure.step("Prepare cluster and open config page")
def prepare_cluster_and_open_config_page(sdk_client: ADCMClient, path: os.PathLike, app):
    """Upload bundle, create cluster and open config page"""
    from tests.ui_tests.app.page.cluster.page import (  # pylint: disable=import-outside-toplevel
        ClusterConfigPage,
    )

    bundle = sdk_client.upload_from_fs(path)
    cluster = bundle.cluster_create(name=f"Test cluster {random_string()}")
    config = ClusterConfigPage(app.driver, app.adcm.url, cluster.cluster_id).open()
    config.wait_page_is_opened()
    return cluster, config


@allure.step("Create 11 group configs")
def create_few_groups(client: ADCMClient, adcm_object: Cluster | Service | Component | Provider):
    for i in range(11):
        response = requests.post(
            f"{client.url}/api/v1/group-config/",
            json={
                "name": f"Test name_{i}",
                "object_type": adcm_object.__class__.__name__.lower(),
                "object_id": adcm_object.id,
                "description": "Test description",
            },
            headers={"Authorization": f"Token {client.api_token()}"},
        )
        response.raise_for_status()
