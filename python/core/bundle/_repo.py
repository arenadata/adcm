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

from typing import Protocol

from core.bundle._definitions import DefinitionsMap
from core.bundle._types import BundleContext, BundleInfo, ComponentKey, ContractVersionTag, InstalledBundleVersion
from core.types import BundleID, PrototypeID


class BundleRepoI(Protocol):
    def save_definitions(self, definitions: DefinitionsMap, bundle_info: BundleInfo) -> BundleID:
        ...

    def update_prototype_licenses(self, bundle_id: BundleID) -> None:
        ...

    def recollect_categories(self) -> None:
        ...

    def retrieve_component_keys(self, bundle_id: BundleID) -> set[ComponentKey]:
        ...

    def retrieve_bundle_installing_info(self) -> set[InstalledBundleVersion]:
        ...

    def retrieve_bundle_context_from_prototype(self, prototype_id: PrototypeID) -> BundleContext:
        ...

    def update_prototype_license_to_accept(self, license_hash: str) -> None:
        ...

    def retrieve_contract_version(self, bundle_id: BundleID) -> ContractVersionTag:
        ...

    def clear_old_versions_adcm_bundles(self) -> None:
        ...
