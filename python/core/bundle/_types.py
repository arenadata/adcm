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

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal, TypeAlias

from typing_extensions import Self

from core.types import BundleID

BundleVersionTag: TypeAlias = str
ContractVersionTag: TypeAlias = str


class SignatureStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    ABSENT = "absent"


class ContractVersionStatus(str, Enum):
    SUPPORTED = "supported"
    DEPRECATED = "deprecated"
    UNSUPPORTED = "unsupported"


@dataclass(slots=True)
class VersionInfo:
    tag: ContractVersionTag
    status: ContractVersionStatus


AvailableContractVersions: TypeAlias = list[VersionInfo]


@dataclass(slots=True, frozen=True)
class ContractVersionInfo:
    status: ContractVersionStatus
    value: ContractVersionTag


@dataclass(slots=True)
class BundleUnpackingInfo:
    hash: str
    root: Path
    signature: SignatureStatus = SignatureStatus.ABSENT


@dataclass(slots=True)
class BundleInfo:
    contract_version: ContractVersionTag
    hash: str
    root: Path
    signature: SignatureStatus

    @classmethod
    def from_unpacking_info(cls, info: BundleUnpackingInfo, contract_version: ContractVersionTag) -> Self:
        return cls(hash=info.hash, root=info.root, signature=info.signature, contract_version=contract_version)


ComponentKey: TypeAlias = tuple[Literal["component"], str, str]
BundleDefinitionKey: TypeAlias = tuple[str] | tuple[Literal["service"], str] | ComponentKey
BeforeUpgradeData: TypeAlias = dict


@dataclass(slots=True)
class BundleContext:
    id: BundleID
    root: Path
    contract_version: ContractVersionTag


@dataclass(slots=True, frozen=True)
class ExistingBundleInfo:
    name: str
    version: BundleVersionTag
    edition: str


@dataclass(slots=True, frozen=True)
class InstalledBundleVersion:
    id: BundleID
    name: str
    edition: str
    version: BundleVersionTag
    contract_version: ContractVersionTag
    has_created_objects: bool


@dataclass(slots=True)
class BundleCompatibilityReport:
    supported_versions: set[ContractVersionTag]
    deprecated_versions: set[ContractVersionTag]
    unsupported_version_bundles: set[InstalledBundleVersion] = field(default_factory=set)
    deprecated_version_bundles: set[InstalledBundleVersion] = field(default_factory=set)
