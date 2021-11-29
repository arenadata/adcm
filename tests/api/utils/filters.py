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

"""Filters for endpoints"""


def is_business_role(item: dict) -> bool:
    """Checks if item is a business role"""
    return (role_type := item.get("type", False)) and role_type == "business"


def is_not_business_role(item: dict) -> bool:
    """Checks if item is not a business role"""
    return not is_business_role(item)


def is_not_hidden_role(item: dict) -> bool:
    """Checks if item is not a hidden role"""
    return (role_type := item.get("type", False)) and role_type != "hidden"


def is_built_in(item: dict) -> bool:
    """Checks if item is a built_in role/policy"""
    return item.get("built_in", False)


def is_not_built_in(item: dict) -> bool:
    """Checks if item is not a built_in role/policy"""
    return not is_built_in(item)
