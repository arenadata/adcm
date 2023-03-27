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

"""Some useful methods"""
import random
import socket
import string
from dataclasses import dataclass
from itertools import repeat
from json import JSONEncoder
from time import sleep

import allure
import ifaddr
import requests
from requests_toolbelt.utils import dump

PARAMETRIZED_BY_LIST = ["cluster", "service", "component", "provider", "host"]


class NotSet:
    """Dummy class for no field value"""


@dataclass
class NotEqual:
    """Class for check that actual value is not equal this"""

    value: object

    class Encoder(JSONEncoder):
        """Decoder for NotEqual class"""

        def default(self, o):
            if isinstance(o, NotEqual):
                return o.value
            return JSONEncoder.default(self, o)


not_set = NotSet()


def wait_for_url(url: str, timeout=120) -> None:
    """Wait until url becomes available"""
    for _ in range(timeout):
        try:
            requests.get(url)
            return
        except requests.exceptions.ConnectionError:
            sleep(1)


def random_string(strlen=10):
    """Generating a random string of a certain length"""
    return "".join([random.choice(string.ascii_letters) for _ in range(strlen)])


def split_tag(image_name):
    """Split docker image by image name and tag"""
    image = image_name.split(":", maxsplit=1)
    if len(image) > 1:
        image_repo = image[0]
        image_tag = image[1]
    else:
        image_repo = image[0]
        image_tag = None
    return image_repo, image_tag


def get_connection_ip(remote_host):
    """
    Try to open connection to remote and get ip address of the interface used.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect((remote_host, 1))
    ip_ = sock.getsockname()[0]
    sock.close()
    return ip_


def get_if_name_by_ip(if_ip):
    """Get interface name by interface IP"""
    for adapter in ifaddr.get_adapters():
        for ip_ in adapter.ips:
            if ip_.ip == if_ip:
                return adapter.name
    raise ValueError(f"IP {if_ip} does not match any network interface!")


def get_if_type(if_ip):
    """
    Get interface type from /sys/class/net/{if_name}/type
    """
    if_name = get_if_name_by_ip(if_ip)
    with open(f"/sys/class/net/{if_name}/type", encoding="utf_8") as file:
        return file.readline().strip()


def fill_lists_by_longest(lists):
    """
    Fills each list by the longest one, thereby aligning them in length
    Last element is used as the fill value
    """
    max_len = len(max(lists, key=len))
    for current_list in lists:
        current_list.extend(repeat(current_list[-1], max_len - len(current_list)))


def nested_set(dictionary: dict, keys: list, value):
    """Set value to dict for list of nested keys

    >>> nested_set({'key': {'nested_key': None}}, keys=['key', 'nested_key'], value=123)
    {'key': {'nested_key': 123}}
    """
    nested_dict = dictionary
    for key in keys[:-1]:
        nested_dict = nested_dict[key]
    nested_dict[keys[-1]] = value
    return dictionary


def nested_get(dictionary: dict, keys: list):
    """Set value to dict for list of nested keys

    >>> nested_get({'key': {'nested_key': 123}}, keys=['key', 'nested_key'])
    123
    """
    nested_dict = dictionary
    for key in keys[:-1]:
        nested_dict = nested_dict[key]
    return nested_dict.get(keys[-1])


def create_dicts_by_chain(keys_chain: list):
    """
    Create nested dicts by keys chain
    >>> create_dicts_by_chain(['some', 'keys'])
    {'some': {'keys': {}}}
    """
    result = {}
    current_dict = result
    for key in keys_chain:
        current_dict[key] = {}
        current_dict = current_dict[key]
    return result


def attach_request_log(response):
    """Attach full HTTP request dump to Allure report"""
    allure.attach(dump.dump_all(response).decode("utf-8"), name="Full request log", extension="txt")
