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
"""
Common functions and helpers for testing ADCM
"""
from typing import List, Tuple, Callable, Union

import allure
import pytest

from _pytest.outcomes import Failed
from coreapi.exceptions import ErrorMessage
from adcm_client.base import ObjectNotFound, PagingEnds
from adcm_client.objects import Host, Task, Job, Cluster, Service, Component, Provider
from adcm_pytest_plugin.utils import catch_failed


ADCMObjects = (Cluster, Service, Component, Provider, Host)

ClusterRelatedObject = Union[Cluster, Service, Component]
ProviderRelatedObject = Union[Provider, Host]
AnyADCMObject = Union[ClusterRelatedObject, ProviderRelatedObject]


def get_config(adcm_object: AnyADCMObject):
    """Get config or empty tuple (if config not defined)"""
    try:
        return adcm_object.config()
    except ErrorMessage:
        return ()


def get_objects_via_pagination(
    object_list_method: Callable, pagination_step: int = 20
) -> List[Union[AnyADCMObject, Job, Task]]:
    """Get all objects as a flat list using pagination"""

    def ignore_paging_ends(paging: dict) -> list:
        try:
            return list(object_list_method(paging=paging))
        except PagingEnds:
            # if previous request returned amount of objects equal to pagination_step
            # then request of new objects raises PagingEnds
            return []

    pagination = {'offset': 0, 'limit': pagination_step}
    objects = []
    while objects_on_next_page := ignore_paging_ends(pagination):
        objects.extend(objects_on_next_page)
        pagination['offset'] += pagination_step
        pagination['limit'] += pagination_step
    return objects


def action_in_object_is_present(action: str, obj: AnyADCMObject):
    """Assert action in object is present"""
    with allure.step(f"Assert that action {action} is present in {_get_object_represent(obj)}"):
        with catch_failed(ObjectNotFound, f"Action {action} not found in object {obj}"):
            obj.action(name=action)


def actions_in_objects_are_present(actions_to_obj: List[Tuple[str, AnyADCMObject]]):
    """Assert actions in objects are present"""
    for pair in actions_to_obj:
        action_in_object_is_present(*pair)


def action_in_object_is_absent(action: str, obj: AnyADCMObject):
    """Assert action in object is absent"""
    with allure.step(f"Assert that action {action} is absent in {_get_object_represent(obj)}"):
        with catch_failed(Failed, f"Action {action} is present in {_get_object_represent(obj)}"):
            with pytest.raises(ObjectNotFound):
                obj.action(name=action)


def actions_in_objects_are_absent(actions_to_obj: List[Tuple[str, AnyADCMObject]]):
    """Assert actions in objects are absent"""
    for pair in actions_to_obj:
        action_in_object_is_absent(*pair)


def _get_object_represent(obj: AnyADCMObject) -> str:
    return f"host {obj.fqdn}" if isinstance(obj, Host) else f"{obj.__class__.__name__.lower()} {obj.name}"
