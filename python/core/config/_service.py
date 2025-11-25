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
from typing import Callable, Iterable, Literal, Protocol, TypeVar

from core.config import files, operations, spec
from core.config._config import detect_active_groups, nested_to_flat
from core.config._names import is_parameter_file_name_startswith
from core.config._pattern_validators import PossiblyEncryptedPatternValidator
from core.config._repo import ConfigRepoI, ObjectWithoutConfigError
from core.config._secrets import AnsibleSecrets
from core.config._types import (
    ChangeRequest,
    ConfigFlatValues,
    ConfigOwner,
    Configuration,
    ConfigurationWithID,
    Defaults,
    HostGroupConfigOwner,
)
from core.config._validate import (
    AlwaysPassValidator,
    MainConfigVariantResolver,
    Validators,
    VariantValidator,
    Violations,
)
from core.result import Fail, Success, is_fail
from core.types import (
    ActionID,
    ADCMHostGroupType,
    ConfigID,
    CoreObjectDescriptor,
    Descriptor,
    HostGroupDescriptor,
    ObjectOrGroup,
    PrototypeID,
    TaskDescriptor,
)

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


FileOwner = (
    CoreObjectDescriptor
    | tuple[CoreObjectDescriptor, HostGroupDescriptor]
    | TaskDescriptor
    | tuple[Descriptor[Literal["process"]], Descriptor[Literal["step"]]]
)


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


def return_as_is(x: str) -> str:
    return x


@dataclass(slots=True)
class ConfigService:
    repo: ConfigRepoI
    secrets: AnsibleSecrets
    settings: Settings
    variant_validators: VariantValidators

    # retrieve

    def retrieve_current_configuration(self, owner: ObjectOrGroup) -> ConfigurationWithID:
        return self.repo.get_config(owner=owner)

    def retrieve_specification(self, owner: CoreObjectDescriptor) -> spec.FullSpec:
        return self.repo.get_spec(owner=owner, action_id=None, defaults=False)

    def retrieve_specification_with_defaults(
        self, owner: CoreObjectDescriptor, *, encrypt_defaults: bool = True
    ) -> tuple[spec.FullSpec, Defaults]:
        encrypt = self.secrets.encrypt if encrypt_defaults else return_as_is
        return self.repo.get_spec(owner=owner, action_id=None, defaults=encrypt)

    def retrieve_partial_specification(
        self,
        owner: CoreObjectDescriptor,
        only_for_types: Iterable[type[spec.p.SimpleParameter] | type[spec.p.ParameterGroup]],
    ) -> spec.FullSpec:
        """
        This is convenience function to "possibly" optimize specification retrieval for cases
        where we don't need full spec or defaults AND don't care if object even has config/spec.
        Don't overuse this function, ensure that you are out of other options and no new mechanism is required.
        Can return "empty" spec.
        """
        return self.repo.get_spec(owner=owner, action_id=None, defaults=False, only_for=only_for_types)

    def retrieve_jsonschema(self, owner: ConfigOwner | HostGroupConfigOwner) -> dict:
        # scenario-like method, may be moved

        specification, defaults = self.retrieve_specification_with_defaults(owner=owner.descriptor)

        match owner:
            case ConfigOwner(descriptor=config_source):
                configuration = self.retrieve_current_configuration(config_source)
                is_host_group = False
            case HostGroupConfigOwner(group=config_source):
                configuration = self.retrieve_current_configuration(config_source)
                is_host_group = True

        variant_resolver = self.variant_validators.main(owner=owner.descriptor, reference_config=configuration)

        return spec.spec_to_jsonschema(
            spec=specification,
            defaults=defaults,
            owner_state=owner.info.state,
            is_group_config=is_host_group,
            resolve_variant=variant_resolver.resolve,
        )

    def retrieve_jsonschema_for_action(
        self,
        action_specification: spec.FullSpec,
        action_config_defaults: Defaults,
        action_owner: ConfigOwner,
    ) -> dict:
        # scenario-like method, may be moved

        try:
            owner_configuration = self.retrieve_current_configuration(owner=action_owner.descriptor)
        except ObjectWithoutConfigError:
            owner_configuration = Configuration()

        variant_resolver = self.variant_validators.main(
            owner=action_owner.descriptor, reference_config=owner_configuration
        )

        return spec.spec_to_jsonschema(
            spec=action_specification,
            defaults=action_config_defaults,
            owner_state=action_owner.info.state,
            is_group_config=False,
            resolve_variant=variant_resolver.resolve,
        )

    def retrieve_specification_with_defaults_for_action(
        self, owner: CoreObjectDescriptor, action_id: ActionID
    ) -> tuple[spec.FullSpec, Defaults]:
        return self.repo.get_spec(owner=owner, action_id=action_id, defaults=self.secrets.encrypt)

    def retrieve_configurations_by_id(self, configurations: Iterable[ConfigID]) -> dict[ConfigID, Configuration]:
        return self.repo.find_configs_by_ids(ids=configurations)

    def retrieve_specifications_by_prototypes(
        self, prototypes: Iterable[PrototypeID], encrypt_defaults: bool = True
    ) -> dict[PrototypeID, spec.FullSpec]:
        encrypt = self.secrets.encrypt if encrypt_defaults else return_as_is
        return {
            id_: spec
            for id_, (spec, _) in self.repo.find_specs_by_prototype_ids(ids=prototypes, encrypt=encrypt).items()
        }

    def retrieve_specifications_by_prototypes_with_defaults(
        self, prototypes: Iterable[PrototypeID], *, encrypt_defaults: bool = True
    ) -> dict[PrototypeID, tuple[spec.FullSpec, Defaults]]:
        encrypt = self.secrets.encrypt if encrypt_defaults else return_as_is
        return self.repo.find_specs_by_prototype_ids(ids=prototypes, encrypt=encrypt)

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
        owner: ObjectOrGroup,
    ) -> ConfigID:
        return self.repo.set_new_config_for_object(owner=owner, config=configuration, description=description)

    def create_initial_configuration_if_required(self, owner: CoreObjectDescriptor) -> ConfigID | None:
        try:
            specification, defaults = self.retrieve_specification_with_defaults(owner=owner)
        except ObjectWithoutConfigError:
            return None

        return self.create_initial_configuration(owner=owner, specification=specification, defaults=defaults)

    def create_initial_configuration(
        self, owner: CoreObjectDescriptor, specification: spec.FullSpec, defaults: Defaults
    ) -> ConfigID:
        default_config = self.prepare_default_configuration(default_values=defaults, specification=specification)

        config_id = self.create_new_configuration_by_descriptor(
            configuration=default_config, description="init", owner=owner
        )

        # bit of strange "leak" that in other cases it'll be outside of service

        self.prepare_file_parameter_values_on_fs(
            configuration=default_config, specification=specification, owner_prefix=files.build_config_prefix(owner)
        )

        return config_id

    def create_initial_configuration_of_host_group(
        self, group: Descriptor[Literal[ADCMHostGroupType.CONFIG]], owner: CoreObjectDescriptor
    ) -> ConfigID:
        # scenario-like case, same as `create_initial_config`, may be moved

        owner_configuration = self.retrieve_current_configuration(owner=owner)
        specification = self.retrieve_specification(owner=owner)

        group_configuration = operations.prepare_initial_config_of_host_group(
            configuration=owner_configuration, specification=specification
        ).value

        config_id = self.create_new_configuration_by_descriptor(
            configuration=group_configuration, description=owner_configuration.description, owner=group
        )

        self.prepare_file_parameter_values_on_fs(
            configuration=group_configuration,
            specification=specification,
            owner_prefix=files.build_config_host_group_prefix(owner, group_id=group.id),
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
        owner: CoreObjectDescriptor,
    ) -> NewConfigurationResult:
        """
        Validate config changes from previous to new and encrypt values
        """
        variant_validator = self.variant_validators.main(owner=owner, reference_config=new)
        validators = Validators(
            variant=variant_validator, pattern=PossiblyEncryptedPatternValidator(secrets=self.secrets)
        )

        active_groups = detect_active_groups(attributes=new.attributes)
        deactivated_parameters = spec.detect_deactivated_parameters(spec=specification, active_groups=active_groups)

        validation_result = operations.validate_new_changes_in_main_configuration(
            new=new,
            previous=previous,
            specification=specification,
            deactivated_parameters=deactivated_parameters,
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

    def prepare_new_configuration_from_changes(
        self,
        changes: list[ChangeRequest],
        configuration: Configuration,
        specification: spec.FullSpec,
        defaults: Defaults,
        owner: CoreObjectDescriptor,
    ) -> NewConfigurationResult:
        result = operations.apply_changes(changes=changes, configuration=configuration, defaults=defaults)
        match result:
            case Success(value=(new_config, changed)) if changed:
                return self.prepare_new_configuration(
                    new=new_config, previous=configuration, specification=specification, owner=owner
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
        owner: CoreObjectDescriptor,
        owner_configuration: Configuration | None,
    ) -> Configuration:
        """
        Validate input action configuration from previous to new, encrypt values
        """
        owner_config = owner_configuration
        if owner_config is None:
            owner_config = Configuration()

        variant_validator = self.variant_validators.main(owner=owner, reference_config=owner_config)
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

    def prepare_configuration_for_ansible(
        self,
        configuration: Configuration,
        specification: spec.FullSpec,
        file_owner: FileOwner,
        *,
        inplace: bool = False,
    ) -> Configuration:
        file_name_constructor = _choose_file_name_builder(file_owner)
        result = operations.prepare_config_for_ansible(
            configuration=configuration,
            specification=specification,
            construct_parameter_path=lambda name: str(self.settings.directories.files / file_name_constructor(name)),
            inplace=inplace,
        )
        return result.value

    # inspect

    def inspect_has_invalid_configuration(self, owner: CoreObjectDescriptor) -> bool:
        try:
            specification = self.retrieve_specification(owner=owner)
        except ObjectWithoutConfigError:
            return False

        configuration = self.retrieve_current_configuration(owner=owner)

        # structure (consistency) violations may be present at this point
        # if stuff like selection groups is in play,
        # buf it it'll be too much, look into values validation used in it
        result = operations.validate_configuration_is_consistent(
            configuration=configuration, specification=specification
        )
        if is_fail(result):
            return True

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


def _choose_file_name_builder(owner: FileOwner) -> Callable[[str], str]:
    match owner:
        case CoreObjectDescriptor():
            return partial(files.construct_parameter_file_name, owner=owner)
        case (CoreObjectDescriptor(), HostGroupDescriptor(id=group_id)):
            return partial(files.construct_parameter_file_name_for_host_group, owner=owner[0], group_id=group_id)
        case Descriptor(id=task_id, type="task"):
            return partial(files.construct_parameter_file_name_for_task, task_id=task_id)
        case (Descriptor(id=process_id, type="process"), Descriptor(id=step_id, type="step")):
            return partial(
                files.construct_parameter_file_name_for_action_process_step, process_id=process_id, step_id=step_id
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
    filepath.chmod(0o0600)

    return fullname
