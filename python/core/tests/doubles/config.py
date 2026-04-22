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
from pathlib import Path
from typing import ClassVar, Iterable, Literal, TypeAlias, overload

from core.config import ConfigRepoI, ConfigService, VariantValidators, spec
from core.config._secrets import AnsibleSecrets
from core.config._types import Configuration, ConfigurationExtraInfo, ConfigurationWithInfo, Defaults, EncryptFunc
from core.config._validate import AlwaysPassValidator, MainConfigVariantResolver
from core.settings import Directories
from core.types import (
    ActionDescriptor,
    ADCMHostGroupType,
    ConfigID,
    CoreObjectDescriptor,
    Descriptor,
    HostGroupDescriptor,
    PrototypeID,
)


class FakeSecrets(AnsibleSecrets):
    """
    Secrets without vault.
    Encrypt = secret\nreversed_value.
    Decrypt = reversed back value without header.
    """

    def __init__(self, secret: str = "!!!===!!!") -> None:
        self._encrypted_header = secret

    def is_encrypted(self, value: str) -> bool:
        return value.startswith(self._encrypted_header)

    def decrypt(self, value: str) -> str:
        if not self.is_encrypted(value):
            return value

        _, decrypted_reversed = value.split("\n", maxsplit=1)
        return "".join(reversed(decrypted_reversed))

    def encrypt(self, value: str) -> str:
        if self.is_encrypted(value):
            return value

        return f"{self._encrypted_header}\n{''.join(reversed(value))}"


@dataclass(slots=True)
class FakeMainConfigVariantResolver(MainConfigVariantResolver):
    return_tuple: ClassVar = ()

    def resolve(self, parameter: spec.p.VariantParameter) -> tuple:
        _ = parameter
        return self.return_tuple


ObjectOrGroup: TypeAlias = CoreObjectDescriptor | HostGroupDescriptor | Descriptor[Literal[ADCMHostGroupType.CONFIG]]


@dataclass(slots=True)
class FakeRepoData:
    configs: dict[int, Configuration] = field(default_factory=dict)
    specs: dict[int, spec.FullSpec] = field(default_factory=dict)


@dataclass(slots=True)
class FakeRepo(ConfigRepoI):
    data: FakeRepoData = field(default_factory=FakeRepoData)

    def get_config(self, owner: ObjectOrGroup) -> ConfigurationWithInfo:
        _ = owner
        raise NotImplementedError

    @overload
    def get_spec(
        self,
        owner: CoreObjectDescriptor | ActionDescriptor,
        *,
        defaults: Literal[False],
        only_for: Iterable[type[spec.p.SimpleParameter] | type[spec.p.ParameterGroup]] | None = None,
    ) -> spec.FullSpec:
        ...

    @overload
    def get_spec(
        self,
        owner: CoreObjectDescriptor | ActionDescriptor,
        *,
        defaults: EncryptFunc,
        only_for: Iterable[type[spec.p.SimpleParameter] | type[spec.p.ParameterGroup]] | None = None,
    ) -> tuple[spec.FullSpec, Defaults]:
        ...

    def get_spec(
        self,
        owner: CoreObjectDescriptor | ActionDescriptor,
        *,
        defaults: Literal[False] | EncryptFunc = False,
        only_for: Iterable[type[spec.p.SimpleParameter] | type[spec.p.ParameterGroup]] | None = None,
    ) -> spec.FullSpec | tuple[spec.FullSpec, Defaults]:
        _ = owner, defaults, only_for
        raise NotImplementedError

    def find_configs_by_ids(self, ids: Iterable[ConfigID]) -> dict[ConfigID, Configuration]:
        requested_ids = set(ids)
        present_ids = requested_ids.intersection(self.data.configs.keys())
        return {id_: self.data.configs[id_] for id_ in present_ids}

    @overload
    def find_specs_by_prototype_ids(
        self, ids: Iterable[PrototypeID], with_defaults: Literal[False], encrypt: None = None
    ) -> dict[PrototypeID, spec.FullSpec]:
        ...

    @overload
    def find_specs_by_prototype_ids(
        self, ids: Iterable[PrototypeID], with_defaults: Literal[True], encrypt: EncryptFunc
    ) -> dict[PrototypeID, tuple[spec.FullSpec, Defaults]]:
        ...

    def find_specs_by_prototype_ids(
        self, ids: Iterable[PrototypeID], with_defaults: bool, encrypt: EncryptFunc | None = None
    ) -> dict[PrototypeID, spec.FullSpec] | dict[PrototypeID, tuple[spec.FullSpec, Defaults]]:
        if with_defaults or encrypt is not None:
            raise NotImplementedError

        requested_ids = set(ids)
        present_ids = requested_ids.intersection(self.data.specs.keys())
        return {id_: self.data.specs[id_] for id_ in present_ids}

    def find_host_group_configurations(self, owner: CoreObjectDescriptor) -> dict[HostGroupDescriptor, Configuration]:
        _ = owner
        raise NotImplementedError

    def set_new_config_for_object(
        self, config: Configuration, config_extra_info: ConfigurationExtraInfo, owner: ObjectOrGroup
    ) -> ConfigID:
        _ = config, config_extra_info, owner
        raise NotImplementedError


def build_config_service_with_fakes() -> tuple[ConfigService, FakeRepo]:
    repo = FakeRepo()
    path = Path()
    directories = Directories(
        base=path,
        stack=path,
        bundles=path,
        downloads=path,
        files=path,
        code=path,
        secrets=path,
        data=path,
        run=path,
        logs=path,
        temp=path,
    )
    cs = ConfigService(
        repo=repo,
        secrets=FakeSecrets(),
        directories=directories,
        variant_validators=VariantValidators(main=FakeMainConfigVariantResolver, default=AlwaysPassValidator),
        yspec_schema={},
    )
    return cs, repo
