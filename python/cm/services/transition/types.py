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
from typing import Any, Literal, TypeAlias

from core.types import ComponentName, HostName, HostProviderName, ServiceName
from pydantic import BaseModel

BundleHash: TypeAlias = str
ConfigurationDict: TypeAlias = dict[str, Any]
# we can't handle anything else during restoration
LiteralMM: TypeAlias = Literal["on", "off"]


@dataclass(slots=True)
class BundleExtraInfo:
    name: str
    version: str
    edition: str

    def __str__(self) -> str:
        return f"{self.name} | ver {self.version} ({self.edition})"


@dataclass(slots=True)
class RestorableCondition:
    state: str
    multi_state: list[str]
    config: ConfigurationDict | None = None
    attr: ConfigurationDict | None = None


@dataclass(slots=True)
class HostProviderInfo:
    bundle: BundleHash
    name: HostProviderName
    description: str
    condition: RestorableCondition


@dataclass(slots=True)
class HostInfo:
    hostprovider: HostProviderName
    name: HostName
    condition: RestorableCondition
    maintenance_mode: LiteralMM


@dataclass(slots=True)
class ConfigHostGroupInfo:
    name: str
    description: str
    config: ConfigurationDict = field(default_factory=dict)
    attr: ConfigurationDict = field(default_factory=dict)
    hosts: list[HostName] = field(default_factory=list)


@dataclass(slots=True)
class ComponentInfo:
    name: ComponentName
    condition: RestorableCondition
    maintenance_mode: LiteralMM
    host_groups: list[ConfigHostGroupInfo] = field(default_factory=list)


@dataclass(slots=True)
class ServiceInfo:
    name: ServiceName
    condition: RestorableCondition
    maintenance_mode: LiteralMM
    components: dict[ComponentName, ComponentInfo] = field(default_factory=dict)
    host_groups: list[ConfigHostGroupInfo] = field(default_factory=list)


@dataclass(slots=True)
class NamedMappingEntry:
    host: HostName
    service: ServiceName
    component: ComponentName


@dataclass(slots=True)
class ClusterInfo:
    bundle: BundleHash
    name: str
    description: str
    condition: RestorableCondition
    services: dict[ServiceName, ServiceInfo] = field(default_factory=dict)
    mapping: list[NamedMappingEntry] = field(default_factory=list)
    host_groups: list[ConfigHostGroupInfo] = field(default_factory=list)


class TransitionPayload(BaseModel):
    adcm_version: str
    bundles: dict[BundleHash, BundleExtraInfo]
    cluster: ClusterInfo
    hostproviders: list[HostProviderInfo]
    hosts: list[HostInfo]
