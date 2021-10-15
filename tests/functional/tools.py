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
from typing import List, Tuple

import allure
import pytest
from _pytest.outcomes import Failed
from adcm_client.base import ObjectNotFound
from adcm_client.objects import Host
from adcm_pytest_plugin.utils import catch_failed
from tests.functional.plugin_utils import AnyADCMObject


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
