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
from typing import Protocol, TypeAlias, TypeVar

from cm import converters
from cm.models import ADCM, ADCMEntity, ConcernCause, ConfigHostGroup, ConfigLog, MainObject
from cm.services.concern import delete_issue
from cm.services.job.run import update_related_configs
from cm.status_api import notify_about_new_concern, send_config_creation_event, send_config_creation_event_by_descriptor
from core.types import ADCMHostGroupType, ConfigID, CoreObjectDescriptor, Descriptor, HostGroupDescriptor, JobID
from django.db.transaction import atomic
from rbac.roles import apply_policy_for_new_config
import core

T = TypeVar("T", contravariant=True)


class InputConfigConverter(Protocol[T]):
    def __call__(self, configuration: T, specification: core.config.spec.FullSpec, /) -> core.config.Configuration:
        ...


class ChangesConverter(Protocol[T]):
    def __call__(self, configuration: T, specification: core.config.spec.FullSpec, /) -> core.config.FlatConfiguration:
        ...


HasChanged: TypeAlias = bool


def update_configuration_of_object(
    *,
    owner: MainObject | ADCM,
    input_config: T,
    convert: InputConfigConverter[T],
    description: str,
    config_service: core.config.ConfigService,
) -> ConfigID:
    from cm.api import raise_outdated_config_flag_if_required

    concern_id, related_objects = None, {}

    owner_descriptor = converters.orm_object_to_core_descriptor(owner)
    file_owner_prefix = core.config.files.build_config_prefix(owner_descriptor)

    with atomic():
        specification = config_service.retrieve_specification(owner=owner_descriptor)
        new_config = convert(input_config, specification)
        current_config = config_service.retrieve_current_configuration(owner=owner_descriptor)

        result = config_service.prepare_new_configuration(
            new=new_config, previous=current_config, specification=specification, owner=owner_descriptor
        )

        main_config_log_id = config_service.create_new_configuration_by_descriptor(
            configuration=result.encrypted_config, description=description, owner=owner_descriptor
        )

        configs_of_host_groups = config_service.retrieve_host_group_configurations(owner=owner_descriptor)
        updated_host_group_configs = config_service.prepare_updated_configurations_of_host_groups(
            main=result.encrypted_config, groups=configs_of_host_groups
        )

        for owner_group, updated_configuration in updated_host_group_configs.items():
            config_service.create_new_configuration_by_descriptor(
                configuration=updated_configuration, description=description, owner=owner_group
            )

        # related configs should be updated

        delete_issue(owner=owner_descriptor, cause=ConcernCause.CONFIG)
        # flag on ADCM can't be raised
        if not isinstance(owner, ADCM) and result.has_changed:
            concern_id, related_objects = raise_outdated_config_flag_if_required(object_=owner)
        apply_policy_for_new_config(config_object=owner, config_log=_get_config_log(id_=main_config_log_id))

        prepare_files = partial(
            config_service.prepare_file_parameter_values_on_fs,
            specification=specification,
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

    return main_config_log_id


def update_configuration_of_host_group(
    *,
    owner: MainObject | ADCM,
    input_config: T,
    convert: InputConfigConverter[T],
    description: str = "",
    group: ConfigHostGroup,
    config_service: core.config.ConfigService,
) -> ConfigID:
    from cm.api import raise_outdated_config_flag_if_required

    concern_id, related_objects = None, {}

    owner_descriptor = converters.orm_object_to_core_descriptor(owner)
    file_owner_prefix = core.config.files.build_config_host_group_prefix(owner=owner_descriptor, group_id=group.pk)

    with atomic():
        specification = config_service.retrieve_specification(owner=owner_descriptor)
        new_config = convert(input_config, specification)
        current_config = config_service.retrieve_current_configuration(
            owner=Descriptor(id=group.pk, type=ADCMHostGroupType.CONFIG)
        )

        result = config_service.prepare_new_configuration(
            new=new_config, previous=current_config, specification=specification, owner=owner_descriptor
        )

        main_object_config = config_service.retrieve_current_configuration(owner=owner_descriptor)

        # sync with changes from main config
        updated_configuration = config_service.prepare_updated_configurations_of_host_groups(
            main=main_object_config, groups={0: result.encrypted_config}
        )[0]

        config_id = config_service.create_new_configuration_by_descriptor(
            configuration=updated_configuration,
            description=description,
            owner=HostGroupDescriptor(id=group.pk, type=ADCMHostGroupType.CONFIG),
        )

        delete_issue(owner=owner_descriptor, cause=ConcernCause.CONFIG)
        # flag on ADCM can't be raised
        if not isinstance(owner, ADCM) and result.has_changed:
            concern_id, related_objects = raise_outdated_config_flag_if_required(object_=owner)
        apply_policy_for_new_config(config_object=owner, config_log=_get_config_log(config_id))

        # see why it's in here in main config save
        config_service.prepare_file_parameter_values_on_fs(
            configuration=updated_configuration,
            specification=specification,
            owner_prefix=file_owner_prefix,
        )

    send_config_creation_event(object_=owner)
    if concern_id:
        notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

    return config_id


def update_configuration_from_job(
    *,
    owner: CoreObjectDescriptor,
    changes_input: T,
    convert: ChangesConverter[T],
    description: str,
    job_id: JobID,
    config_service: core.config.ConfigService,
    # possible BS arguments, need to rethink them
    owner_orm: ADCMEntity,
) -> tuple[core.config.FlatConfiguration, HasChanged]:
    with atomic():
        specification = config_service.retrieve_specification(owner=owner)
        changes = convert(changes_input, specification)

        configuration = config_service.retrieve_current_configuration(owner=owner)

        result = config_service.prepare_new_configuration_from_changes(
            changes=changes, configuration=configuration, specification=specification, owner=owner
        )

        if not result.has_changed:
            return changes, False

        config_id = config_service.create_new_configuration_by_descriptor(
            configuration=result.encrypted_config, description=description, owner=owner
        )
        config_service.prepare_file_parameter_values_on_fs(
            configuration=result.encrypted_config,
            specification=specification,
            owner_prefix=core.config.files.build_config_prefix(owner=owner),
        )

        config_log_orm = ConfigLog.objects.get(id=config_id)
        apply_policy_for_new_config(config_object=owner_orm, config_log=config_log_orm)

        update_related_configs(
            job_id=job_id,
            object_=owner,
            object_prototype_id=owner_orm.prototype_id,  # pyright: ignore [reportAttributeAccessIssue]
            old_config_id=configuration.id,
            new_config_id=config_id,
        )

    send_config_creation_event_by_descriptor(object_=owner)

    return changes, True


# bad, but can't skip it for now
def _get_config_log(id_: ConfigID) -> ConfigLog:
    return ConfigLog.objects.get(id=id_)
