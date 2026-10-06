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

from core import config
from core.config import (
    ConfigOperationError,
    Configuration,
    ConfigurationExtraInfo,
    Defaults,
    ObjectWithoutConfigError,
    operations,
    spec,
)
from core.config.constants import SYSTEM_CONFIG_CREATOR
from core.result import Fail
from core.types import ConfigID, CoreObjectDescriptor, HostGroupDescriptor

SpecWithDefaults = tuple[spec.FullSpec, Defaults]


@dataclass(slots=True)
class ConfigScenarios:
    config_service: config.ConfigService

    def save_encrypted_config(
        self,
        *,
        owner: CoreObjectDescriptor,
        encrypted_main_config: config.Configuration,
        specification: config.spec.FullSpec,
        config_extra_info: config.ConfigurationExtraInfo,
    ) -> ConfigID:
        configs_of_host_groups = self.config_service.retrieve_host_group_configurations(owner=owner)
        return self.save_encrypted_config_with_host_groups(
            owner=owner,
            encrypted_main_config=encrypted_main_config,
            specification=specification,
            config_extra_info=config_extra_info,
            host_group_configs=configs_of_host_groups,
        )

    def save_encrypted_config_with_host_groups(
        self,
        *,
        owner: CoreObjectDescriptor,
        encrypted_main_config: config.Configuration,
        specification: config.spec.FullSpec,
        config_extra_info: config.ConfigurationExtraInfo,
        host_group_configs: dict[HostGroupDescriptor, config.Configuration],
    ) -> ConfigID:
        config_id = self.config_service.create_new_configuration_by_descriptor(
            configuration=encrypted_main_config,
            configuration_extra_info=config_extra_info,
            owner=owner,
        )

        updated_host_group_configs = self.config_service.prepare_updated_configurations_of_host_groups(
            main=encrypted_main_config, groups=host_group_configs, specification=specification
        )

        for owner_group, updated_configuration in updated_host_group_configs.items():
            self.config_service.create_new_configuration_by_descriptor(
                configuration=updated_configuration,
                configuration_extra_info=config_extra_info,
                owner=owner_group,
            )

        prepare_files = self.config_service.prepare_file_parameter_values_on_fs
        file_owner_prefix = config.files.build_config_prefix(owner)
        # since we have no "fallback" mechanism for write failures, have to write files within transaction
        prepare_files(configuration=encrypted_main_config, specification=specification, owner_prefix=file_owner_prefix)

        for owner_group, updated_configuration in updated_host_group_configs.items():
            group_file_prefix = f"{file_owner_prefix}.group.{owner_group.id}"
            # since we have no "fallback" mechanism for write failures, have to write files within transaction
            prepare_files(
                configuration=updated_configuration, specification=specification, owner_prefix=group_file_prefix
            )

        return config_id

    def switch_configuration(
        self, *, owner: CoreObjectDescriptor, old: SpecWithDefaults, new: SpecWithDefaults
    ) -> None:
        """
        Adapts current configuration of owner and its host groups from `old` specification to `new` one.
        If owner has no configuration, initial one is created (only when `new` defaults aren't empty).
        """

        old_spec, old_defaults = old
        new_spec, new_defaults = new

        # empty configuration (spec) may be received in order to "work correctly"
        # when configuration is removed from object
        try:
            configuration = self.config_service.retrieve_current_configuration(owner=owner)
        except ObjectWithoutConfigError:
            # no current config
            if new_defaults:
                # assume it's non-empty config
                self.config_service.create_initial_configuration(
                    owner=owner, specification=new_spec, defaults=new_defaults
                )

            return

        update_for_new_spec = partial(
            operations.adapt_configuration_for_new_specification,
            specification=old_spec,
            defaults=old_defaults,
            new_specification=new_spec,
            new_defaults=new_defaults,
        )

        update_result = update_for_new_spec(configuration=configuration, include_synchronization=False)
        if isinstance(update_result, Fail):
            raise ConfigOperationError(f"Failed to adapt config: {str(update_result.value)}")

        configs_of_host_groups = self.config_service.retrieve_host_group_configurations(owner=owner)
        adaptation_results = {
            group: update_for_new_spec(configuration=config_of_group, include_synchronization=True)
            for group, config_of_group in configs_of_host_groups.items()
        }
        adapted_configs_of_host_groups: dict[HostGroupDescriptor, Configuration] = {}
        for group, result in adaptation_results.items():
            if isinstance(result, Fail):
                raise ConfigOperationError(f"Failed to adapt config of host group: {str(result.value)}")

            adapted_configs_of_host_groups[group] = result.value

        self.save_encrypted_config_with_host_groups(
            owner=owner,
            encrypted_main_config=update_result.value,
            specification=new_spec,
            config_extra_info=ConfigurationExtraInfo(description="upgrade", created_by=SYSTEM_CONFIG_CREATOR),
            host_group_configs=adapted_configs_of_host_groups,
        )
