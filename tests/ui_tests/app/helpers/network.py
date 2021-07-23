import time
from contextlib import contextmanager

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.webdriver.remote.webdriver import WebDriver


@allure.step('Wait for requests to stop')
@contextmanager
def wait_all_requests_stop(driver: WebDriver):
    yield

    def is_stopped():
        requests_before = driver.get_log('performance')
        time.sleep(1)
        assert requests_before == driver.get_log('performance')
    wait_until_step_succeeds(is_stopped, period=1, timeout=30)
