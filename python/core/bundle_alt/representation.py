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

from core.bundle_alt.predicates import is_component_key, is_service_key
from core.bundle_alt.types import BundleDefinitionKey, Definition, DefinitionsMap, GeneralObjectDescription


def make_ref(d: GeneralObjectDescription) -> str:
    return f'{d.type} "{d.name}" {d.version}'


def find_parent(key: BundleDefinitionKey, definitions: DefinitionsMap) -> Definition:
    if is_component_key(key):
        return definitions[("service", key[1])]

    if is_service_key(key):
        return definitions[("cluster",)]

    raise RuntimeError(f"No parent for {key}")


def dependency_entry_to_key(entry: dict) -> BundleDefinitionKey:
    if "component" in entry:
        return ("component", entry["service"], entry["component"])

    return ("service", entry["service"])
