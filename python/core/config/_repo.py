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

from typing import Iterable, Literal, Protocol, TypeAlias, overload

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

    @overload
    def get_spec(
        self,
        owner: CoreObjectDescriptor,
        action_id: ActionID | None,
        *,
        with_defaults: Literal[False],
        only_for: Iterable[type[spec.p.SimpleParameter] | type[spec.p.ParameterGroup]] | None = None,
    ) -> spec.FullSpec:
        ...

    @overload
    def get_spec(
        self,
        owner: CoreObjectDescriptor,
        action_id: ActionID | None,
        *,
        with_defaults: Literal[True],
        only_for: Iterable[type[spec.p.SimpleParameter] | type[spec.p.ParameterGroup]] | None = None,
    ) -> tuple[spec.FullSpec, Defaults]:
        ...

    def get_spec(
        self,
        owner: CoreObjectDescriptor,
        action_id: ActionID | None,
        *,
        with_defaults: bool = False,
        only_for: Iterable[type[spec.p.SimpleParameter] | type[spec.p.ParameterGroup]] | None = None,
    ) -> spec.FullSpec | tuple[spec.FullSpec, Defaults]:
        """
        Retrieve specification for owner or action of this owner (owner-action relation may not be checked).
        If specification is missing, an error will be raised (except some cases, see `only_for`).

        Specifying `with_defaults` will resolve defaults for specification.

        Specifying `only_for` allows to retrieve partial spec (with parameters/groups only matching ones specified),
        BUT it's not guaranteed that only them will be included
        (implementation may ignore that optimization for some or all types)
        AND specifying this argument as non empty iterable will silence object configuration missing error.
        """
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
