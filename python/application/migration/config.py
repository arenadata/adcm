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


from functools import partial
from typing import Protocol, TypeVar

from cm import converters
from cm.models import ADCM, ConcernCause, ConfigHostGroup, ConfigLog, MainObject
from cm.services import config_service as config
from cm.services.concern import delete_issue
from cm.status_api import notify_about_new_concern, send_config_creation_event
from django.conf import settings
from django.db.transaction import atomic
from rbac.roles import apply_policy_for_new_config
import core

T = TypeVar("T", contravariant=True)


class InputConfigConverter(Protocol[T]):
    def __call__(self, configuration: T, specification: core.config.spec.FullSpec, /) -> core.config.Configuration:
        ...


def update_configuration_of_object(
    *,
    owner: MainObject | ADCM,
    input_config: T,
    convert: InputConfigConverter[T],
    description: str = "",
) -> ConfigLog:
    from cm.api import raise_outdated_config_flag_if_required

    concern_id, related_objects = None, {}

    config_source = owner
    owner_descriptor = converters.orm_object_to_core_descriptor(owner)
    config_owner = core.config.ConfigOwner(
        descriptor=owner_descriptor, info=core.config.ConfigOwnerObjectInfo(state=owner.state)
    )
    file_owner_prefix = core.config.files.build_config_prefix(owner_descriptor)

    with atomic():
        specification, _ = config.retrieve.get_specification(owner=config_owner.descriptor)
        new_config = convert(input_config, specification)
        current_config = config.retrieve.get_current_configuration(owner=config_source)

        result = config.prepare.new_configuration(
            new=new_config, previous=current_config, specification=specification, owner=config_owner
        )

        main_config_log = config.create.new_config_by_descriptor(
            configuration=result.encrypted_config, description=description, owner=owner_descriptor
        )

        configs_of_host_groups = config.retrieve.get_configurations_of_host_groups(owner=owner_descriptor)
        updated_host_group_configs = config.prepare.updated_configs_of_host_groups(
            main=result.encrypted_config, groups=configs_of_host_groups
        )

        for owner_group, updated_configuration in updated_host_group_configs.items():
            config.create.new_config_by_descriptor(
                configuration=updated_configuration, description=description, owner=owner_group
            )

        # related configs should be updated

        delete_issue(owner=owner_descriptor, cause=ConcernCause.CONFIG)
        # flag on ADCM can't be raised
        if not isinstance(owner, ADCM) and result.has_changed:
            concern_id, related_objects = raise_outdated_config_flag_if_required(object_=owner)
        apply_policy_for_new_config(config_object=owner, config_log=main_config_log)

        prepare_files = partial(
            config.prepare.file_parameter_values_on_fs, target_dir=settings.FILE_DIR, specification=specification
        )

        # since we have no "fallback" mechanism for write failures, have to write files within transaction
        prepare_files(configuration=new_config, owner_prefix=file_owner_prefix)

        for owner_group, updated_configuration in updated_host_group_configs.items():
            group_file_prefix = f"{file_owner_prefix}.group.{owner_group.id}"
            # since we have no "fallback" mechanism for write failures, have to write files within transaction
            prepare_files(configuration=updated_configuration, owner_prefix=group_file_prefix)

    send_config_creation_event(object_=owner)
    if concern_id:
        notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

    return main_config_log


def update_configuration_of_host_group(
    *,
    owner: MainObject | ADCM,
    input_config: T,
    convert: InputConfigConverter[T],
    description: str = "",
    group: ConfigHostGroup,
) -> ConfigLog:
    from cm.api import raise_outdated_config_flag_if_required

    concern_id, related_objects = None, {}

    config_source = group
    owner_descriptor = converters.orm_object_to_core_descriptor(owner)
    config_owner = core.config.ConfigOwner(
        descriptor=owner_descriptor, info=core.config.ConfigOwnerObjectInfo(state=owner.state)
    )
    file_owner_prefix = f"{owner_descriptor.type.value.lower()}.{owner_descriptor.id}.group.{group.pk}"

    with atomic():
        specification, _ = config.retrieve.get_specification(owner=config_owner.descriptor)
        new_config = convert(input_config, specification)
        current_config = config.retrieve.get_current_configuration(owner=config_source)

        result = config.prepare.new_configuration(
            new=new_config, previous=current_config, specification=specification, owner=config_owner
        )

        # sync with changes from main config
        updated_configuration = config.prepare.updated_configs_of_host_groups(
            main=current_config, groups={0: result.encrypted_config}
        )[0]

        config_log = config.create.new_config(
            configuration=updated_configuration, description=description, owner=config_source
        )

        delete_issue(owner=owner_descriptor, cause=ConcernCause.CONFIG)
        # flag on ADCM can't be raised
        if not isinstance(owner, ADCM) and result.has_changed:
            concern_id, related_objects = raise_outdated_config_flag_if_required(object_=owner)
        apply_policy_for_new_config(config_object=owner, config_log=config_log)

        # see why it's in here in main config save
        config.prepare.file_parameter_values_on_fs(
            configuration=updated_configuration,
            specification=specification,
            owner_prefix=file_owner_prefix,
            target_dir=settings.FILE_DIR,
        )

    send_config_creation_event(object_=owner)
    if concern_id:
        notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

    return config_log
