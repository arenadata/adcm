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

"""Common utils for ADCM tests"""

import json
import random
import time
from operator import attrgetter
from typing import Callable, Iterable, TypeVar

import requests
from adcm_client.objects import Cluster, Component, Host, Provider, Service, Task
from adcm_pytest_plugin.params import ADCMVersionParam
from adcm_pytest_plugin.plugin import parametrized_by_adcm_version

T = TypeVar("T")

name_of = attrgetter("name")


class ConfigError(Exception):
    """Tests are configured incorrectly"""


class RequestFailedException(Exception):
    """Request to ADCM API has status code >= 400"""


def get_action_by_name(client, cluster, name):
    """
    Get action by name from some object

    Args:
        client: ADCM client API objects
        cluster: cluster object
        name: action name

    Returns:
        (action object): Action object by name

    Raises:
        :py:class:`ValueError`
            If action is not found

    """
    action_list = client.cluster.action.list(cluster_id=cluster["id"])
    for action in action_list:
        if action["name"] == name:
            return action
    raise ValueError(f"Action with name '{name}' is not found in cluster '{cluster}'")


def filter_action_by_name(actions, name):
    """
    Filter action list by name and return filtered list
    """
    return list(filter(lambda x: x["name"] == name, actions))


def get_random_service(client):
    """
    Get random service object from ADCM

    :param client: ADCM client API objects

    """
    service_list = client.stack.service.list()
    return random.choice(service_list)


def get_service_id_by_name(client, service_name: str) -> int:
    """
    Get service id by name from ADCM

    Args:
        client: ADCM client API objects
        service_name: service name

    Returns:
        (int): Service id by name

    Raises:
        :py:class:`ValueError`
            If service is not found

    """
    service_list = client.stack.service.list()
    for service in service_list:
        if service["name"] == service_name:
            return service["id"]
    raise ValueError(f"Service with name '{service_name}' is not found")


def get_random_cluster_prototype(client) -> dict:
    """
    Get random cluster prototype object from ADCM

    :param client: ADCM client API objects

    """
    return random.choice(client.stack.cluster.list())


def get_random_host_prototype(client) -> dict:
    """
    Get random host prototype object from ADCM

    :param client: ADCM client API objects

    """
    return random.choice(client.stack.host.list())


def get_random_cluster_service_component(client, cluster, service) -> dict:
    """
    Get random cluster service component

    Args:
        client: ADCM client API objects
        cluster: some cluster object
        service: some service object in cluster

    Raises:
        :py:class:`ValueError`
            If service is not found
    """
    components = client.cluster.service.component.list(cluster_id=cluster["id"], service_id=service["id"])
    if components:
        return random.choice(components)
    raise ValueError("Service has not components")


def get_host_by_fqdn(client, fqdn):
    """
    Get host object by fqdn from ADCM

    Args:
        client: ADCM client API objects
        fqdn: host's fqdn

    Returns:
        (host object): Host object by fqdn

    Raises:
        :py:class:`ValueError`
            If host is not found
    """

    host_list = client.host.list()
    for host in host_list:
        if host["fqdn"] == fqdn:
            return host
    raise ValueError(f"Host with fqdn '{fqdn}' is not found in a host list")


def wait_until(client, task, interval=1, timeout=30):
    """
    Wait until task status becomes either success or failed

    Args:
        client: ADCM client API objects
        task: some task for wait its status
        interval: interval with which task status will be requested
        timeout: time during which status success or failed is expected

    """
    start = time.time()
    while not (task["status"] == "success" or task["status"] == "failed") and time.time() - start < timeout:
        time.sleep(interval)
        task = client.task.read(task_id=task["id"])


def get_json_or_text(response: requests.Response):
    """
    Try to get JSON or text if JSON can't be parsed from requests.Response.
    Use this function to provide more info on ADCM API Error.
    """
    try:
        return response.json()
    except json.JSONDecodeError:
        return response.text


def previous_adcm_version_tag() -> ADCMVersionParam:
    """Get tag of previous ADCM version"""
    return parametrized_by_adcm_version(adcm_min_version="2021.03.10")[0][-1]


def lower_class_name(obj: object) -> str:
    """Return lower class name"""
    return obj.__class__.__name__.lower()


def get_hosts_fqdn_representation(hosts: Iterable[Host]):
    """Return string with host FQDNs separated by ','"""
    return ", ".join(host.fqdn for host in hosts)


def get_or_raise(collection: Iterable[T], predicate: Callable[[T], bool]) -> T:
    suitable_object = next(filter(predicate, iter(collection)), None)
    if suitable_object:
        return suitable_object

    raise AssertionError("Failed to get object by given params")


# !===== Bulk Log Download =====!


def build_full_archive_name(
    adcm_object: Cluster | Service | Component | Provider,
    task: Task,
    action_name_in_archive_name: str,
) -> str:
    """Build expected archive name for general object action's task (without extension)"""
    top_level_object = adcm_object if not isinstance(adcm_object, (Service, Component)) else adcm_object.cluster()
    return "_".join(
        map(
            lambda p: p.replace(" ", "-").replace("_", "").lower(),
            (
                top_level_object.name,
                adcm_object.prototype().display_name,
                action_name_in_archive_name,
                str(task.id),
            ),
        )
    )
