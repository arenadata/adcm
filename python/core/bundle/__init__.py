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

from core.bundle import _constants as constants
from core.bundle import _definitions as d
from core.bundle import _operations as operations
from core.bundle import _parsing as parsing
from core.bundle._contract_version import (
    check_contract_version_supported,
    is_contract_version_supported,
)
from core.bundle._definitions import PrototypeMetaInfo
from core.bundle._errors import (
    BundleOperationError,
    BundleParsingError,
    BundleProcessingError,
    BundleSignatureVerificationError,
    BundleValidationError,
    LicenseError,
    UnsupportedBundleError,
)
from core.bundle._files import get_hash_safe, untar_safe
from core.bundle._predicates import is_component_key
from core.bundle._repo import BundleRepoI
from core.bundle._representation import build_parent_key_safe
from core.bundle._service import BundleService
from core.bundle._types import (
    AvailableContractVersions,
    BundleCompatibilityReport,
    BundleContext,
    BundleDefinitionKey,
    BundleInfo,
    BundleUnpackingInfo,
    BundleVersionTag,
    ComponentKey,
    ContractVersionStatus,
    ContractVersionTag,
    ExistingBundleInfo,
    InstalledBundleVersion,
    SignatureStatus,
    VersionInfo,
)
from core.bundle._unpacking import (
    UploadedFileLike,
    cleanup,
    save_bundle_file_from_request_to_downloads,
    unpack_bundle,
    verify_signature,
)
from core.bundle._validate import ConvertConfigDefinition, check_config_defaults

__all__ = [
    "AvailableContractVersions",
    "BundleCompatibilityReport",
    "BundleContext",
    "BundleDefinitionKey",
    "BundleInfo",
    "BundleOperationError",
    "BundleParsingError",
    "BundleProcessingError",
    "BundleRepoI",
    "BundleService",
    "BundleSignatureVerificationError",
    "BundleUnpackingInfo",
    "BundleValidationError",
    "BundleVersionTag",
    "ComponentKey",
    "ContractVersionStatus",
    "ContractVersionTag",
    "ConvertConfigDefinition",
    "ExistingBundleInfo",
    "InstalledBundleVersion",
    "LicenseError",
    "PrototypeMetaInfo",
    "SignatureStatus",
    "UnsupportedBundleError",
    "UploadedFileLike",
    "VersionInfo",
    "build_parent_key_safe",
    "check_config_defaults",
    "check_contract_version_supported",
    "cleanup",
    "constants",
    "d",
    "get_hash_safe",
    "is_component_key",
    "is_contract_version_supported",
    "operations",
    "parsing",
    "save_bundle_file_from_request_to_downloads",
    "unpack_bundle",
    "untar_safe",
    "verify_signature",
]
