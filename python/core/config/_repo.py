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

from typing import Iterable, Literal, Protocol, TypeAlias

from core.config import spec
from core.config._types import Configuration, ConfigurationWithID, Defaults
from core.types import (
    ActionID,
    ADCMHostGroupType,
    ConfigID,
    CoreObjectDescriptor,
    Descriptor,
    HostGroupDescriptor,
    PrototypeID,
)

# todo improve


class RepoError(Exception):
    ...


class NoConfigError(RepoError):
    ...


class ObjectWithoutConfigError(RepoError):
    ...


class ObjectDiscoveryError(RepoError):
    ...


ObjectOrGroup: TypeAlias = CoreObjectDescriptor | HostGroupDescriptor | Descriptor[Literal[ADCMHostGroupType.CONFIG]]


class ConfigRepoI(Protocol):
    # retrieve

    def get_config(self, owner: ObjectOrGroup) -> ConfigurationWithID:
        ...

    def get_spec_and_defaults(
        self, owner: CoreObjectDescriptor, action_id: ActionID | None
    ) -> tuple[spec.FullSpec, Defaults]:
        ...

    def find_configs_by_ids(self, ids: Iterable[ConfigID]) -> dict[ConfigID, Configuration]:
        ...

    def find_specs_by_prototype_ids(
        self, ids: Iterable[PrototypeID]
    ) -> dict[PrototypeID, tuple[spec.FullSpec, Defaults]]:
        ...

    # todo: shouldn't be here, see service for more info
    def find_host_group_configurations(self, owner: CoreObjectDescriptor) -> dict[HostGroupDescriptor, Configuration]:
        ...

    # change

    def set_new_config_for_object(self, config: Configuration, description: str, owner: ObjectOrGroup) -> ConfigID:
        ...
