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

from core import config
from core.types import ConfigID, CoreObjectDescriptor, HostGroupDescriptor


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
