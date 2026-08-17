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

from core.bundle._errors import UnsupportedBundleError
from core.bundle._types import AvailableContractVersions, ContractVersionStatus, ContractVersionTag


def check_contract_version_supported(
    current_version: ContractVersionTag, available_contract_versions: AvailableContractVersions
) -> None:
    if not is_contract_version_supported(current_version, available_contract_versions):
        raise UnsupportedBundleError("Unsupported bundle's prototype usage")


def is_contract_version_supported(
    current_version: ContractVersionTag, available_contract_versions: AvailableContractVersions
) -> bool:
    return any(
        info.tag == current_version and info.status != ContractVersionStatus.UNSUPPORTED
        for info in available_contract_versions
    )
