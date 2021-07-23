import json
import time
from contextlib import contextmanager

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.webdriver.remote.webdriver import WebDriver


class NetworkItem:
    """Web page network request."""

    def __init__(self, path, domain, method, status, status_text, duration, type, url, referer):
        self.path = path
        self.domain = domain
        self.method = method
        self.status = status
        self.status_text = status_text
        self.duration = duration
        self.type = type
        self.url = url
        self.referer = referer


def fetch_requests(browser: WebDriver, is_response=True) -> [dict]:
    network_responses = list()
    performance_logs = browser.get_log('performance')
    for log in performance_logs:
        if is_response:
            if '"method":"Network.responseReceived"' in log.get('message'):
                network_responses.append(log)
        else:
            network_responses.append(log)
    return network_responses


def transform_network_log(network_log_items: [dict]):
    result = []
    for item in network_log_items:
        message_raw = item.get('message')
        message = json.loads(message_raw)['message']
        params = message['params']
        path, domain, method, referer, duration, status_text, status = \
            None, None, None, None, None, None, None

        url = params.get('documentURL')
        type = params.get('type')

        result.append(NetworkItem(
            path=path,
            domain=domain,
            method=method,
            status=status,
            status_text=status_text,
            duration=duration,
            type=type,
            url=url,
            referer=referer
        ))
    return result


def get_network_log(browser: WebDriver, is_web_doc=True) -> list:
    network_data = fetch_requests(browser, is_web_doc)
    return transform_network_log(network_data)


@allure.step('Wait for requests to stop')
@contextmanager
def wait_all_requests_stop(browser: WebDriver):
    yield

    def is_stopped():
        requests_before = get_network_log(browser)
        time.sleep(1)
        assert requests_before == get_network_log(browser)
    wait_until_step_succeeds(is_stopped, period=1, timeout=30)
