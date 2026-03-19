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
from cm.legacy.services.concern import delete_issue
from cm.legacy.services.job.run import update_related_configs
from cm.legacy.status_api import notify_about_new_concern, send_config_creation_event
from cm.models import ADCM, ADCMEntity, ConcernCause, ConfigHostGroup, ConfigLog, MainObject
from core.config.constants import SYSTEM_CONFIG_CREATOR
from core.types import ADCMHostGroupType, ConfigID, CoreObjectDescriptor, Descriptor, HostGroupDescriptor, JobID
from django.db.transaction import atomic
from rbac.scenarios import RBACScenarios
import core

T = TypeVar("T", contravariant=True)


class InputConfigConverter(Protocol[T]):
    def __call__(self, configuration: T, specification: core.config.spec.FullSpec, /) -> core.config.Configuration:
        ...


class ChangesConverter(Protocol[T]):
    def __call__(
        self, configuration: T, specification: core.config.spec.FullSpec, /
    ) -> list[core.config.ChangeRequest]:
        ...


HasChanged: TypeAlias = bool


def update_configuration_of_object(
    *,
    owner: MainObject | ADCM,
    input_config: T,
    convert: InputConfigConverter[T],
    config_extra_info: core.config.ConfigurationExtraInfo,
    config_service: core.config.ConfigService,
    rbac_scenarios: RBACScenarios,
) -> ConfigID:
    from cm.legacy.api import raise_outdated_config_flag_if_required

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
            configuration=result.encrypted_config,
            configuration_extra_info=config_extra_info,
            owner=owner_descriptor,
        )

        configs_of_host_groups = config_service.retrieve_host_group_configurations(owner=owner_descriptor)
        updated_host_group_configs = config_service.prepare_updated_configurations_of_host_groups(
            main=result.encrypted_config, groups=configs_of_host_groups, specification=specification
        )

        for owner_group, updated_configuration in updated_host_group_configs.items():
            config_service.create_new_configuration_by_descriptor(
                configuration=updated_configuration,
                configuration_extra_info=config_extra_info,
                owner=owner_group,
            )

        # related configs should be updated

        delete_issue(owner=owner_descriptor, cause=ConcernCause.CONFIG)
        # flag on ADCM can't be raised
        if not isinstance(owner, ADCM) and result.has_changed:
            concern_id, related_objects = raise_outdated_config_flag_if_required(object_=owner)
        rbac_scenarios.apply_policy_for_new_config(
            config_object=owner, config_log=_get_config_log(id_=main_config_log_id)
        )

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

    send_config_creation_event(
        object_id=owner.pk,
        object_type=owner.prototype.type,
        changes={"createdBy": config_extra_info.created_by},
    )
    if concern_id:
        notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

    return main_config_log_id


def update_configuration_of_host_group(
    *,
    owner: MainObject | ADCM,
    input_config: T,
    convert: InputConfigConverter[T],
    config_extra_info: core.config.ConfigurationExtraInfo,
    group: ConfigHostGroup,
    config_service: core.config.ConfigService,
    rbac_scenarios: RBACScenarios,
) -> ConfigID:
    from cm.legacy.api import raise_outdated_config_flag_if_required

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
            main=main_object_config, groups={0: result.encrypted_config}, specification=specification
        )[0]

        config_id = config_service.create_new_configuration_by_descriptor(
            configuration=updated_configuration,
            configuration_extra_info=config_extra_info,
            owner=HostGroupDescriptor(id=group.pk, type=ADCMHostGroupType.CONFIG),
        )

        delete_issue(owner=owner_descriptor, cause=ConcernCause.CONFIG)
        # flag on ADCM can't be raised
        if not isinstance(owner, ADCM) and result.has_changed:
            concern_id, related_objects = raise_outdated_config_flag_if_required(object_=owner)
        rbac_scenarios.apply_policy_for_new_config(config_object=owner, config_log=_get_config_log(config_id))

        # see why it's in here in main config save
        config_service.prepare_file_parameter_values_on_fs(
            configuration=updated_configuration,
            specification=specification,
            owner_prefix=file_owner_prefix,
        )

    send_config_creation_event(
        object_id=owner.pk, object_type=owner.prototype.type, changes={"createdBy": config_extra_info.created_by}
    )
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
    rbac_scenarios: RBACScenarios,
    # possible BS arguments, need to rethink them
    owner_orm: ADCMEntity,
) -> tuple[list[core.config.ChangeRequest], HasChanged]:
    with atomic():
        specification, defaults = config_service.retrieve_specification_with_defaults(owner=owner)
        changes = convert(changes_input, specification)

        configuration = config_service.retrieve_current_configuration(owner=owner)

        result = config_service.prepare_new_configuration_from_changes(
            changes=changes, configuration=configuration, specification=specification, defaults=defaults, owner=owner
        )

        if not result.has_changed:
            return changes, False

        config_id = config_service.create_new_configuration_by_descriptor(
            configuration=result.encrypted_config,
            configuration_extra_info=core.config.ConfigurationExtraInfo(
                description=description, created_by=SYSTEM_CONFIG_CREATOR
            ),
            owner=owner,
        )
        config_service.prepare_file_parameter_values_on_fs(
            configuration=result.encrypted_config,
            specification=specification,
            owner_prefix=core.config.files.build_config_prefix(owner=owner),
        )

        config_log_orm = ConfigLog.objects.get(id=config_id)
        rbac_scenarios.apply_policy_for_new_config(config_object=owner_orm, config_log=config_log_orm)

        update_related_configs(
            job_id=job_id,
            object_=owner,
            object_prototype_id=owner_orm.prototype_id,  # pyright: ignore [reportAttributeAccessIssue]
            old_config_id=configuration.id,
            new_config_id=config_id,
        )
        delete_issue(owner=owner, cause=ConcernCause.CONFIG)
    send_config_creation_event(
        object_id=owner.id, object_type=owner.type, changes={"createdBy": config_log_orm.created_by}
    )

    return changes, True


# bad, but can't skip it for now
def _get_config_log(id_: ConfigID) -> ConfigLog:
    return ConfigLog.objects.get(id=id_)
