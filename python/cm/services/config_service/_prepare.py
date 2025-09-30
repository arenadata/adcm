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
from typing import Callable, TypeVar

from core import config
from core.result import Fail

from cm.errors import AdcmEx
from cm.services.config_service._secrets import AnsibleSecrets
from cm.services.config_service._validators import MainConfigVariantResolver, PossiblyEncryptedPatternValidator

T = TypeVar("T")


@dataclass(slots=True)
class NewConfigurationResult:
    encrypted_config: config.Configuration
    has_changed: bool


def default_configuration(
    default_values: config.ConfigFlatValues, specification: config.spec.FullSpec
) -> config.Configuration:
    return config.operations.prepare_config_from_defaults(default_values=default_values, specification=specification)


def new_configuration(
    new: config.Configuration,
    previous: config.Configuration,
    specification: config.spec.FullSpec,
    owner: config.ConfigOwner,
) -> NewConfigurationResult:
    """
    Validate config changes from previous to new and encrypt values
    """

    # may be an external dependency since it's sort of "service"
    ansible_secrets = AnsibleSecrets()

    validators = config.Validators(
        variant=MainConfigVariantResolver(owner=owner.descriptor, reference_config=new),
        pattern=PossiblyEncryptedPatternValidator(secrets=ansible_secrets),
    )

    validation_result = config.operations.validate_new_changes_in_main_configuration(
        new=new,
        previous=previous,
        specification=specification,
        owner_info=owner.info,
        validators=validators,
    )
    match validation_result:
        case Fail(value=violations):
            err = _format_validation_violations_to_error(violations)
            raise err

    encryption_result = config.operations.encrypt_secrets(
        values=new.values, specification=specification, encrypt=ansible_secrets.encrypt
    )
    encrypted_values = encryption_result.value

    return NewConfigurationResult(
        encrypted_config=config.Configuration(values=encrypted_values, attributes=new.attributes),
        has_changed=validation_result.value.has_changed,
    )


def updated_configs_of_host_groups(
    main: config.Configuration, groups: dict[T, config.Configuration]
) -> dict[T, config.Configuration]:
    return {
        key: config.operations.update_config_of_host_group(main=main, host_group=config_of_group).value
        for key, config_of_group in groups.items()
    }


def file_parameter_values_on_fs(
    configuration: config.Configuration, specification: config.spec.FullSpec, owner_prefix: str, target_dir: Path
) -> None:
    # have to decrypt, because it's sort of "requirement"
    secrets = AnsibleSecrets()
    write = partial(
        _write_to_files_dir_with_prefix,
        prefix=owner_prefix,
        target_dir=target_dir,
        decrypt=lambda x: secrets.decrypt(x) or "",
    )
    config.operations.store_files(values=configuration.values, specification=specification, write=write)


def _format_validation_violations_to_error(violations: config.Violations) -> AdcmEx:
    violations_list_repr = "\n".join(f"- {v.parameter} [{v.check}]: {v.reason}" for v in violations)
    message = f"Configuration doesn't match specification. Following violations detected:\n{violations_list_repr}"
    return AdcmEx(code="CONFIG_OPERATION_ERROR", msg=message)


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
        config.names.is_parameter_file_name_startswith(
            file_name=parameter_identifier, name="ansible_ssh_private_key_file"
        )
        and content != ""
        and content[-1] == "-"
    ):
        content += "\n"

    decoded_content = decrypt(content)

    filepath.write_text(data=decoded_content, encoding="utf-8")

    return fullname
