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
from functools import partial
from pathlib import Path
from typing import Callable, Iterable, Protocol, TypeAlias, TypeVar

from core.config import files, operations, spec
from core.config._config import detect_active_groups, nested_to_flat
from core.config._names import is_parameter_file_name_startswith
from core.config._pattern_validators import PossiblyEncryptedPatternValidator
from core.config._repo import ConfigRepoI, ObjectWithoutConfigError
from core.config._secrets import AnsibleSecrets
from core.config._types import (
    ConfigFlatValues,
    ConfigOwner,
    Configuration,
    ConfigurationWithID,
    Defaults,
    FlatConfiguration,
)
from core.config._validate import (
    AlwaysPassValidator,
    MainConfigVariantResolver,
    Validators,
    VariantValidator,
    Violations,
)
from core.result import Fail, Success, is_fail
from core.types import ActionID, ConfigID, CoreObjectDescriptor, HostGroupDescriptor, PrototypeID

T = TypeVar("T")


@dataclass(slots=True)
class NewConfigurationResult:
    encrypted_config: Configuration
    has_changed: bool


class ConfigLogAlike(Protocol):
    id: int
    config: dict
    attr: dict
    description: str


CoreObjectOrGroup: TypeAlias = CoreObjectDescriptor | HostGroupDescriptor


@dataclass(slots=True)
class Directories:
    files: Path


@dataclass(slots=True)
class Settings:
    directories: Directories


@dataclass(slots=True)
class VariantValidators:
    main: type[MainConfigVariantResolver]
    default: type[VariantValidator]


class OperationError(Exception):
    ...


@dataclass(slots=True)
class ConfigService:
    repo: ConfigRepoI
    secrets: AnsibleSecrets
    settings: Settings
    variant_validators: VariantValidators

    # retrieve

    def retrieve_current_configuration(self, owner: CoreObjectOrGroup) -> ConfigurationWithID:
        return self.repo.get_config(owner=owner)

    def retrieve_specification(self, owner: CoreObjectDescriptor) -> tuple[spec.FullSpec, Defaults]:
        return self.repo.get_spec_and_defaults(owner=owner, action_id=None)

    def retrieve_specification_for_action(
        self, owner: CoreObjectDescriptor, action_id: ActionID
    ) -> tuple[spec.FullSpec, Defaults]:
        return self.repo.get_spec_and_defaults(owner=owner, action_id=action_id)

    def retrieve_configurations_by_id(self, configurations: Iterable[ConfigID]) -> dict[ConfigID, Configuration]:
        return self.repo.find_configs_by_ids(ids=configurations)

    def retrieve_specifications_by_prototypes(
        self, prototypes: Iterable[PrototypeID]
    ) -> dict[PrototypeID, spec.FullSpec]:
        return {id_: spec for id_, (spec, _) in self.repo.find_specs_by_prototype_ids(ids=prototypes).items()}

    def retrieve_specifications_by_prototypes_with_defaults(
        self, prototypes: Iterable[PrototypeID]
    ) -> dict[PrototypeID, tuple[spec.FullSpec, Defaults]]:
        return self.repo.find_specs_by_prototype_ids(ids=prototypes)

    # todo: bad, should accept host groups or direct ids,
    # host groups retrieval should be in separate service/repo
    def retrieve_host_group_configurations(
        self, owner: CoreObjectDescriptor
    ) -> dict[HostGroupDescriptor, Configuration]:
        return self.repo.find_host_group_configurations(owner=owner)

    # create

    def create_new_configuration_by_descriptor(
        self,
        configuration: Configuration,
        description: str,
        owner: CoreObjectOrGroup,
    ) -> ConfigID:
        return self.repo.set_new_config_for_object(owner=owner, config=configuration, description=description)

    def create_initial_configuration_if_required(self, owner: CoreObjectDescriptor) -> ConfigID | None:
        try:
            specification, defaults = self.repo.get_spec_and_defaults(owner=owner, action_id=None)
        except ObjectWithoutConfigError:
            return None

        default_config = self.prepare_default_configuration(default_values=defaults, specification=specification)

        config_id = self.create_new_configuration_by_descriptor(
            configuration=default_config, description="init", owner=owner
        )

        # bit of strange "leak" that in other cases it'll be outside of service

        self.prepare_file_parameter_values_on_fs(
            configuration=default_config, specification=specification, owner_prefix=files.build_config_prefix(owner)
        )

        return config_id

    # prepare

    def prepare_default_configuration(
        self, default_values: ConfigFlatValues, specification: spec.FullSpec
    ) -> Configuration:
        return operations.prepare_config_from_defaults(default_values=default_values, specification=specification)

    def prepare_new_configuration(
        self,
        new: Configuration,
        previous: Configuration,
        specification: spec.FullSpec,
        owner: ConfigOwner,
    ) -> NewConfigurationResult:
        """
        Validate config changes from previous to new and encrypt values
        """
        active_groups = detect_active_groups(attributes=new.attributes)
        stateful_parameters = spec.detect_stateful_parameters(
            spec=specification, owner_state=owner.info.state, active_groups=active_groups
        )

        return self._prepare_configuration(
            new=new,
            previous=previous,
            specification=specification,
            stateful_parameters=stateful_parameters,
            owner=owner.descriptor,
        )

    def prepare_new_configuration_from_changes(
        self,
        changes: FlatConfiguration,
        configuration: Configuration,
        specification: spec.FullSpec,
        owner_descriptor: CoreObjectDescriptor,
    ) -> NewConfigurationResult:
        match operations.apply_changes(changes=changes, configuration=configuration):
            case Success(value=(new_config, changed)) if changed:
                active_groups = detect_active_groups(attributes=new_config.attributes)
                deactivated_parameters = spec.detect_deactivated_parameters(
                    spec=specification, active_groups=active_groups
                )
                stateful_parameters = spec.StatefulParameters(deactivated=deactivated_parameters)
                return self._prepare_configuration(
                    new=new_config,
                    previous=configuration,
                    specification=specification,
                    stateful_parameters=stateful_parameters,
                    owner=owner_descriptor,
                )

            case Success():
                return NewConfigurationResult(encrypted_config=configuration, has_changed=False)

            case Fail(value=violations):
                err = _format_validation_violations_to_error(violations)
                raise err

    def prepare_action_configuration(
        self,
        configuration: Configuration,
        specification: spec.FullSpec,
        owner_descriptor: CoreObjectDescriptor,
        owner_configuration: Configuration | None,
    ) -> Configuration:
        """
        Validate input action configuration from previous to new, encrypt values
        """
        owner_config = owner_configuration
        if owner_config is None:
            owner_config = Configuration()

        variant_validator = self.variant_validators.main(owner=owner_descriptor, reference_config=owner_config)
        validators = Validators(
            variant=variant_validator, pattern=PossiblyEncryptedPatternValidator(secrets=self.secrets)
        )

        validation_result = operations.validate_action_configuration(
            configuration=configuration, specification=specification, validators=validators
        )
        match validation_result:
            case Fail(value=violations):
                err = _format_validation_violations_to_error(violations)
                raise err

        encryption_result = operations.encrypt_secrets(
            values=configuration.values, specification=specification, encrypt=self.secrets.encrypt
        )
        encrypted_values = encryption_result.value

        return Configuration(values=encrypted_values, attributes=configuration.attributes)

    def prepare_updated_configurations_of_host_groups(
        self, main: Configuration, groups: dict[T, Configuration]
    ) -> dict[T, Configuration]:
        return {
            key: operations.update_config_of_host_group(main=main, host_group=config_of_group).value
            for key, config_of_group in groups.items()
        }

    def prepare_file_parameter_values_on_fs(
        self, configuration: Configuration, specification: spec.FullSpec, owner_prefix: str
    ) -> None:
        write = partial(
            _write_to_files_dir_with_prefix,
            prefix=owner_prefix,
            target_dir=self.settings.directories.files,
            decrypt=lambda x: self.secrets.decrypt(x) or "",
        )
        operations.store_files(values=configuration.values, specification=specification, write=write)

    # inspect

    def inspect_has_invalid_configuration(self, owner: CoreObjectDescriptor) -> bool:
        try:
            specification, _ = self.retrieve_specification(owner=owner)
        except ObjectWithoutConfigError:
            return False

        configuration = self.retrieve_current_configuration(owner=owner)
        flat_configuration = nested_to_flat(configuration=configuration, specification=specification)

        # for issues we sort of rely on defaults validation,
        # so aren't interested in variant/pattern violations
        # => may as well skip them
        always_pass_validator = AlwaysPassValidator()

        result = operations.validate_values(
            configuration=flat_configuration,
            specification=specification,
            validators=Validators(variant=always_pass_validator, pattern=always_pass_validator),
            check_inside_deactivated_groups=False,
        )

        return is_fail(result)

    # configurable implementations

    def _prepare_configuration(
        self,
        new: Configuration,
        previous: Configuration,
        specification: spec.FullSpec,
        owner: CoreObjectDescriptor,
        stateful_parameters: spec.StatefulParameters,
    ) -> NewConfigurationResult:
        variant_validator = self.variant_validators.main(owner=owner, reference_config=new)
        validators = Validators(
            variant=variant_validator, pattern=PossiblyEncryptedPatternValidator(secrets=self.secrets)
        )

        validation_result = operations.validate_new_changes_in_main_configuration(
            new=new,
            previous=previous,
            specification=specification,
            stateful_parameters=stateful_parameters,
            validators=validators,
        )
        match validation_result:
            case Fail(value=violations):
                err = _format_validation_violations_to_error(violations)
                raise err

        encryption_result = operations.encrypt_secrets(
            values=new.values, specification=specification, encrypt=self.secrets.encrypt
        )
        encrypted_values = encryption_result.value

        return NewConfigurationResult(
            encrypted_config=Configuration(values=encrypted_values, attributes=new.attributes),
            has_changed=validation_result.value.has_changed,
        )


def _format_validation_violations_to_error(violations: Violations) -> OperationError:
    violations_list_repr = "\n".join(f"- {v.parameter} [{v.check}]: {v.reason}" for v in violations)
    message = f"Configuration doesn't match specification. Following violations detected:\n{violations_list_repr}"
    return OperationError(message)


def _write_to_files_dir_with_prefix(
    parameter_identifier: str, content: str, prefix: str, target_dir: Path, decrypt: Callable[[str], str]
) -> str:
    fullname = f"{prefix}.{parameter_identifier}"
    filepath = target_dir / fullname

    # This patch is moved from `save_file_type`, it is deeply based on `parameter_identifier` format
    # which is not nice, yet I have no adequate solution for now.
    #
    # There is a trouble between openssh 7.9 and register function of Ansible.
    # Register function does rstrip of string, while openssh 7.9 not working
    # with private key files without \n at the end.
    # So when we create that key from playbook and save it in ADCM we get
    # "Load key : invalid format" on next connect to host.
    if (
        is_parameter_file_name_startswith(file_name=parameter_identifier, name="ansible_ssh_private_key_file")
        and content != ""
        and content[-1] == "-"
    ):
        content += "\n"

    decoded_content = decrypt(content)

    filepath.write_text(data=decoded_content, encoding="utf-8")

    return fullname
