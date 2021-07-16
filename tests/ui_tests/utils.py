# pylint: disable=too-many-ancestors
import time
from collections import UserDict
from contextlib import contextmanager

import allure
from adcm_client.objects import ADCMClient, Cluster
from adcm_pytest_plugin.utils import random_string
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW

from tests.ui_tests.app.configuration import Configuration


def prepare_cluster(sdk_client: ADCMClient, path) -> Cluster:
    bundle = sdk_client.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-1:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    return cluster


@allure.step("Prepare cluster and get config")
def prepare_cluster_and_get_config(sdk_client: ADCMClient, path, app):
    cluster = prepare_cluster(sdk_client, path)
    time.sleep(5)
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
    tabs = driver.window_handles
    yield
    WDW(driver, wait_time).until(EC.new_window_is_opened(tabs))
    tabs = driver.window_handles
    driver.switch_to.window(tabs[len(tabs) - 1])


@allure.step('Close current tab')
def close_current_tab(driver: WebDriver):
    tabs = driver.window_handles
    driver.close()
    driver.switch_to.window(tabs[0])
