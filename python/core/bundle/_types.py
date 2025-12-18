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

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal, TypeAlias


class SignatureStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    ABSENT = "absent"


@dataclass(slots=True)
class BundleUnpackingInfo:
    hash: str
    root: Path
    signature: SignatureStatus = SignatureStatus.ABSENT


# This is target implementation of definition keys,
# but for simplicity of transition old implementation is used
#
# CT = TypeVar("CT", bound=Literal[ADCMCoreType.CLUSTER, ADCMCoreType.PROVIDER, ADCMCoreType.HOST, ADCMCoreType.ADCM])
# @dataclass(slots=True, frozen=True)
# class UniqueKey(Generic[CT]):
#    type: CT
#
#
# @dataclass(slots=True, frozen=True)
# class ServiceKey:
#    type: Literal[ADCMCoreType.SERVICE]
#    name: str
#
#
# @dataclass(slots=True, frozen=True)
# class ComponentKey:
#    type: Literal[ADCMCoreType.COMPONENT]
#    name: str
#    service: str
#
#
# ClusterBundleDefinitionKey: TypeAlias = UniqueKey[Literal[ADCMCoreType.CLUSTER]] | ServiceKey | ComponentKey
# ProviderBundleDefinitionKey: TypeAlias = UniqueKey[Literal[ADCMCoreType.PROVIDER, ADCMCoreType.HOST]]
# ADCMBundleDefinitionKey: TypeAlias = UniqueKey[Literal[ADCMCoreType.ADCM]]
#
# BundleDefinitionKey: TypeAlias = ClusterBundleDefinitionKey | ProviderBundleDefinitionKey | ADCMBundleDefinitionKey
BundleDefinitionKey: TypeAlias = tuple[str] | tuple[Literal["service"], str] | tuple[Literal["component"], str, str]
