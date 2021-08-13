# pylint: disable=too-many-ancestors
from collections import UserDict
from contextlib import contextmanager
from typing import Callable, TypeVar, Any, Union, Optional

import allure

from adcm_client.objects import ADCMClient, Cluster
from adcm_pytest_plugin.utils import random_string, wait_until_step_succeeds
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW

from tests.ui_tests.app.configuration import Configuration

T = TypeVar('T')
D = TypeVar('D')


def prepare_cluster(sdk_client: ADCMClient, path) -> Cluster:
    bundle = sdk_client.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-1:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    return cluster


@allure.step("Prepare cluster and get config")
def prepare_cluster_and_get_config(sdk_client: ADCMClient, path, app):
    cluster = prepare_cluster(sdk_client, path)
    config = Configuration(app.driver, f"{app.adcm.url}/cluster/{cluster.cluster_id}/config")
    return cluster, config


class BundleObjectDefinition(UserDict):
    def __init__(self, obj_type=None, name=None, version=None):
        super().__init__()
        self["type"] = obj_type
        self["name"] = name
        if version is not None:
            self["version"] = version

    def _set_ui_option(self, option, value):
        if "ui_options" not in self:
            self["ui_options"] = {}
        self["ui_options"][option] = value

    def set_advanced(self, value):
        self._set_ui_option("advanced", value)

    @classmethod
    def to_dict(cls, obj) -> dict:
        if isinstance(obj, cls):
            obj = cls.to_dict(obj.data)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                obj[i] = cls.to_dict(v)
        elif isinstance(obj, dict):
            for k in obj:
                obj[k] = cls.to_dict(obj[k])
        return obj


class ClusterDefinition(BundleObjectDefinition):
    def __init__(self, name=None, version=None):
        super().__init__(obj_type="cluster", name=name, version=version)


class ServiceDefinition(BundleObjectDefinition):
    def __init__(self, name=None, version=None):
        super().__init__(obj_type="service", name=name, version=version)


class ProviderDefinition(BundleObjectDefinition):
    def __init__(self, name=None, version=None):
        super().__init__(obj_type="provider", name=name, version=version)


class HostDefinition(BundleObjectDefinition):
    def __init__(self, name=None, version=None):
        super().__init__(obj_type="host", name=name, version=version)


class GroupDefinition(BundleObjectDefinition):
    def __init__(self, name=None):
        super().__init__(obj_type="group", name=name)
        self["activatable"] = True
        self["subs"] = []

    def add_fields(self, *fields):
        for t in fields:
            self["subs"].append(t)
        return self


class FieldDefinition(BundleObjectDefinition):
    def __init__(self, prop_type, prop_name=None):
        super().__init__(obj_type=prop_type, name=prop_name)
        self["required"] = False


@allure.step('Wait for a new window after action')
@contextmanager
def wait_for_new_window(driver: WebDriver, wait_time: int = 10):
    """Wait a new window is opened after some action"""

    tabs = driver.window_handles
    yield
    WDW(driver, wait_time).until(EC.new_window_is_opened(tabs))
    tabs = driver.window_handles
    driver.switch_to.window(tabs[len(tabs) - 1])


@allure.step('Close current tab')
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
        row_count := page.table.row_count
    ) == expected_amount, (
        f'Page #{table_page_num} should contain {expected_amount}, not {row_count}'
    )


def wait_and_assert_ui_info(
    get_info_func: Union[Callable[[Any], T]],
    assert_info_func: Callable[[T, D, Any], Any],
    expected_values: D,
    timeout: Union[int, float] = 5,
    period: Union[int, float] = 0.5,
    get_info_kwargs: Optional[dict] = None,
    assert_info_kwargs: Optional[dict] = None,
):
    """
    Wait for some information on UI to be correct.
    Use it to avoid getting data from UI a bit earlier than it is fully loaded.

    :param get_info_func: Function that gets data from UI
                          and composes it into some object of type T
    :param assert_info_func: Function that takes object of type T as first argument,
                             expected values of type D as second argument
                             and asserts that fields are exactly as they're expected to be
    :param expected_values: Expected values to pass as second
    :param timeout: Timeout for wait_until_step_succeeds
    :param period: Period for wait_until_step_succeeds
    :param get_info_kwargs: Keyword arguments to pass into get_info_func
    :param assert_info_kwargs: Keyword arguments to pass into assert_info_func
    """
    get_info_kwargs = get_info_kwargs or {}
    assert_info_kwargs = assert_info_kwargs or {}

    def check_info_from_ui():
        ui_info = get_info_func(**get_info_kwargs)
        assert_info_func(ui_info, expected_values, **assert_info_kwargs)

    with allure.step('Check information is correct on UI'):
        wait_until_step_succeeds(check_info_from_ui, timeout=timeout, period=period)
