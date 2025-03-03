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

from typing import TypeVar

from core.bundle_alt.predicates import is_component_key, is_service_key
from core.bundle_alt.types import BundleDefinitionKey, GeneralObjectDescription

T = TypeVar("T")


def make_ref(d: GeneralObjectDescription) -> str:
    return f'{d.type} "{d.name}" {d.version}'


def build_parent_key_safe(key: BundleDefinitionKey) -> BundleDefinitionKey | None:
    if is_component_key(key):
        return ("service", key[1])

    if is_service_key(key):
        return ("cluster",)

    return None


def find_parent(key: BundleDefinitionKey, definitions: dict[BundleDefinitionKey, T]) -> T:
    key = build_parent_key_safe(key)
    if key is None:
        raise RuntimeError(f"No parent for {key}")

    return definitions[key]


def dependency_entry_to_key(entry: dict) -> BundleDefinitionKey:
    if "component" in entry:
        return ("component", entry["service"], entry["component"])

    return ("service", entry["service"])
