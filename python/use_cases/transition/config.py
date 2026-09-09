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
from typing import Protocol, TypeAlias, TypeVar

from cm import converters
from cm.errors import AdcmEx
from cm.legacy.services.concern import delete_issue
from cm.legacy.services.job.run import update_related_configs
from cm.models import ADCM, ADCMEntity, ConcernCause, ConfigHostGroup, ConfigLog, MainObject
from cm.transition.status import StatusScenarios
from core.config.constants import SYSTEM_CONFIG_CREATOR
from core.scenarios.config import ConfigScenarios
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


@dataclass(slots=True)
class UpdateConfigurationOfObject:
    config_scenarios: ConfigScenarios
    config_service: core.config.ConfigService
    rbac_scenarios: RBACScenarios
    status_scenarios: StatusScenarios

    def do(
        self,
        *,
        owner: MainObject | ADCM,
        input_config: T,
        convert: InputConfigConverter[T],
        config_extra_info: core.config.ConfigurationExtraInfo,
    ) -> ConfigID:
        from cm.legacy.api import raise_outdated_config_flag_if_required

        concern_id, related_objects = None, {}

        owner_descriptor = converters.orm_object_to_core_descriptor(owner)
        with atomic():
            specification = self.config_service.retrieve_specification(owner=owner_descriptor)
            new_config = convert(input_config, specification)
            current_config = self.config_service.retrieve_current_configuration(owner=owner_descriptor)

            result = self.config_service.prepare_new_configuration(
                new=new_config, previous=current_config, specification=specification, owner=owner_descriptor
            )

            main_config_log_id = self.config_scenarios.save_encrypted_config(
                owner=owner_descriptor,
                encrypted_main_config=result.encrypted_config,
                specification=specification,
                config_extra_info=config_extra_info,
            )

            # related configs should be updated

            delete_issue(owner=owner_descriptor, cause=ConcernCause.CONFIG)
            # flag on ADCM can't be raised
            if not isinstance(owner, ADCM) and result.has_changed:
                concern_id, related_objects = raise_outdated_config_flag_if_required(object_=owner)
            self.rbac_scenarios.apply_policy_for_new_config(
                config_object=owner, config_log=_get_config_log(id_=main_config_log_id)
            )

        self.status_scenarios.send_config_creation_event(
            owner=owner_descriptor, created_by=config_extra_info.created_by
        )
        if concern_id:
            self.status_scenarios.notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

        return main_config_log_id


@dataclass(slots=True)
class UpdateConfigurationOfHostGroup:
    config_service: core.config.ConfigService
    rbac_scenarios: RBACScenarios
    status_scenarios: StatusScenarios

    def do(
        self,
        *,
        owner: MainObject | ADCM,
        input_config: T,
        convert: InputConfigConverter[T],
        config_extra_info: core.config.ConfigurationExtraInfo,
        group: ConfigHostGroup,
    ) -> ConfigID:
        from cm.legacy.api import raise_outdated_config_flag_if_required

        concern_id, related_objects = None, {}

        owner_descriptor = converters.orm_object_to_core_descriptor(owner)
        file_owner_prefix = core.config.files.build_config_host_group_prefix(owner=owner_descriptor, group_id=group.pk)

        with atomic():
            specification = self.config_service.retrieve_specification(owner=owner_descriptor)
            new_config = convert(input_config, specification)
            current_config = self.config_service.retrieve_current_configuration(
                owner=Descriptor(id=group.pk, type=ADCMHostGroupType.CONFIG)
            )

            result = self.config_service.prepare_new_configuration(
                new=new_config, previous=current_config, specification=specification, owner=owner_descriptor
            )

            main_object_config = self.config_service.retrieve_current_configuration(owner=owner_descriptor)

            # sync with changes from main config
            updated_configuration = self.config_service.prepare_updated_configurations_of_host_groups(
                main=main_object_config, groups={0: result.encrypted_config}, specification=specification
            )[0]

            config_id = self.config_service.create_new_configuration_by_descriptor(
                configuration=updated_configuration,
                configuration_extra_info=config_extra_info,
                owner=HostGroupDescriptor(id=group.pk, type=ADCMHostGroupType.CONFIG),
            )

            delete_issue(owner=owner_descriptor, cause=ConcernCause.CONFIG)
            # flag on ADCM can't be raised
            if not isinstance(owner, ADCM) and result.has_changed:
                concern_id, related_objects = raise_outdated_config_flag_if_required(object_=owner)
            self.rbac_scenarios.apply_policy_for_new_config(config_object=owner, config_log=_get_config_log(config_id))

            # see why it's in here in main config save
            self.config_service.prepare_file_parameter_values_on_fs(
                configuration=updated_configuration,
                specification=specification,
                owner_prefix=file_owner_prefix,
            )

        self.status_scenarios.send_config_creation_event(
            owner=owner_descriptor, created_by=config_extra_info.created_by
        )
        if concern_id:
            self.status_scenarios.notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

        return config_id


@dataclass(slots=True)
class UpdateConfigurationFromJob:
    config_scenarios: ConfigScenarios
    config_service: core.config.ConfigService
    rbac_scenarios: RBACScenarios
    status_scenarios: StatusScenarios

    def do(
        self,
        *,
        owner: CoreObjectDescriptor,
        changes_input: T,
        convert: ChangesConverter[T],
        description: str,
        job_id: JobID,
        # possible BS arguments, need to rethink them
        owner_orm: ADCMEntity,
    ) -> tuple[list[core.config.ChangeRequest], HasChanged]:
        with atomic():
            specification, defaults = self.config_service.retrieve_specification_with_defaults(owner=owner)
            changes = convert(changes_input, specification)

            configuration = self.config_service.retrieve_current_configuration(owner=owner)

            result = self.config_service.prepare_new_configuration_from_changes(
                changes=changes,
                configuration=configuration,
                specification=specification,
                defaults=defaults,
                owner=owner,
            )

            if not result.has_changed:
                return changes, False

            config_extra_info = core.config.ConfigurationExtraInfo(
                description=description, created_by=SYSTEM_CONFIG_CREATOR
            )

            config_id = self.config_scenarios.save_encrypted_config(
                owner=owner,
                encrypted_main_config=result.encrypted_config,
                specification=specification,
                config_extra_info=config_extra_info,
            )

            self.rbac_scenarios.apply_policy_for_new_config(
                config_object=owner_orm, config_log=_get_config_log(id_=config_id)
            )

            update_related_configs(
                job_id=job_id,
                object_=owner,
                object_prototype_id=owner_orm.prototype_id,  # pyright: ignore [reportAttributeAccessIssue]
                old_config_id=configuration.id,
                new_config_id=config_id,
            )

            delete_issue(owner=owner, cause=ConcernCause.CONFIG)

        self.status_scenarios.send_config_creation_event(owner=owner, created_by=config_extra_info.created_by)

        return changes, True


@dataclass(slots=True)
class UpdateHostGroupConfigurationFromJob:
    """Write parameter changes into a configuration host group, from inside a job.

    `UpdateConfigurationFromJob` is the same thing for a main object; a group differs in two
    ways. Its configuration is stored against the group, and a value written into it only
    survives if that parameter is also marked as no longer synchronized with the owner -
    otherwise the merge that keeps a group current with its owner overwrites it again on the
    way out, and the write silently does nothing.
    """

    config_service: core.config.ConfigService
    rbac_scenarios: RBACScenarios
    status_scenarios: StatusScenarios

    def do(
        self,
        *,
        owner_orm: MainObject,
        group: ConfigHostGroup,
        changes_input: T,
        convert: ChangesConverter[T],
        description: str,
    ) -> HasChanged:
        owner = converters.orm_object_to_core_descriptor(owner_orm)
        group_owner = HostGroupDescriptor(id=group.pk, type=ADCMHostGroupType.CONFIG)

        with atomic():
            specification, defaults = self.config_service.retrieve_specification_with_defaults(owner=owner)
            changes = convert(changes_input, specification)

            configuration = self.config_service.retrieve_current_configuration(owner=group_owner)

            result = self.config_service.prepare_new_configuration_from_changes(
                changes=changes,
                configuration=configuration,
                specification=specification,
                defaults=defaults,
                owner=owner,
            )

            # Setting a parameter to the value the group already shows is not a no-op when the
            # group is still following the owner: without the flag below, the next change to the
            # owner's configuration would carry the group along and the value asked for here
            # would silently go away. So the write is skipped only when the value is already
            # the group's own.
            desynchronized = self._desynchronize_changed_parameters(
                configuration=result.encrypted_config, changes=changes
            )

            if not (result.has_changed or desynchronized):
                return False

            main_configuration = self.config_service.retrieve_current_configuration(owner=owner)
            merged = self.config_service.prepare_updated_configurations_of_host_groups(
                main=main_configuration, groups={0: result.encrypted_config}, specification=specification
            )[0]

            config_extra_info = core.config.ConfigurationExtraInfo(
                description=description, created_by=SYSTEM_CONFIG_CREATOR
            )
            config_id = self.config_service.create_new_configuration_by_descriptor(
                configuration=merged, configuration_extra_info=config_extra_info, owner=group_owner
            )

            self.rbac_scenarios.apply_policy_for_new_config(
                config_object=owner_orm, config_log=_get_config_log(id_=config_id)
            )

            self.config_service.prepare_file_parameter_values_on_fs(
                configuration=merged,
                specification=specification,
                owner_prefix=core.config.files.build_config_host_group_prefix(owner=owner, group_id=group.pk),
            )

        self.status_scenarios.send_config_creation_event(owner=group_owner, created_by=SYSTEM_CONFIG_CREATOR)

        return True

    @staticmethod
    def _desynchronize_changed_parameters(
        configuration: core.config.Configuration, changes: list[core.config.ChangeRequest]
    ) -> bool:
        changed = False

        for change in changes:
            attributes = configuration.attributes.get(change.parameter)

            if attributes is None or not attributes.synchronization:
                raise AdcmEx(
                    code="INTERNAL_SERVER_ERROR",
                    msg=f'"{change.parameter}" can\'t be set in a configuration host group: '
                    "the bundle does not allow this parameter to differ per group "
                    "(`group_customization`)",
                )

            changed = changed or attributes.is_synced
            attributes.is_synced = False

        return changed


def apply_config_changes_to_host_group(
    db_object: MainObject,
    group: ConfigHostGroup,
    parameters: list[dict],
    changes_description: str,
    update_configuration: UpdateHostGroupConfigurationFromJob,
) -> HasChanged:
    _check_parameters_unique(parameters)

    return update_configuration.do(
        owner_orm=db_object,
        group=group,
        changes_input=parameters,
        convert=prepare_config_change_requests,
        description=changes_description,
    )


# bad, but can't skip it for now
def _get_config_log(id_: ConfigID) -> ConfigLog:
    return ConfigLog.objects.get(id=id_)


def apply_config_changes(
    job_id: JobID,
    db_object: ADCM | MainObject,
    parameters: list[dict],
    changes_description: str,
    update_configuration_from_job: UpdateConfigurationFromJob,
) -> HasChanged:
    _check_parameters_unique(parameters)

    _, has_changed = update_configuration_from_job.do(
        owner=converters.orm_object_to_core_descriptor(db_object),
        changes_input=parameters,
        convert=prepare_config_change_requests,
        job_id=job_id,
        description=changes_description,
        owner_orm=db_object,
    )

    return has_changed


def prepare_config_change_requests(
    parameters: list[dict], spec: core.config.spec.FullSpec
) -> list[core.config.ChangeRequest]:
    changes = []

    for parameter_change in parameters:
        full_name = core.config.names.ensure_full_name(parameter_change["key"])
        value = parameter_change["value"]

        if full_name not in spec.groups:
            change = core.config.ChangeRequest.for_value(name=full_name, value=value)
            changes.append(change)
            continue

        group_spec = spec.groups[full_name]
        if group_spec.selection:
            change = core.config.ChangeRequest.for_group_selection(name=full_name, value=value)
            changes.append(change)
            continue

        if not spec.groups[full_name].activation:
            raise AdcmEx(code="INTERNAL_SERVER_ERROR", msg=f"{full_name}: only activatable groups may be (de)activated")

        if not isinstance(value, bool):
            raise AdcmEx(code="INTERNAL_SERVER_ERROR", msg=f"{full_name}: value expected to be boolean")

        change = core.config.ChangeRequest.for_activation_attribute(name=full_name, value=value)
        changes.append(change)

    return changes


def _check_parameters_unique(parameters: list[dict]) -> None:
    checked = set()

    for entry in parameters:
        key = entry["key"]
        if key not in checked:
            checked.add(key)
        else:
            raise AdcmEx(code="INTERNAL_SERVER_ERROR", msg=f"{key} is not unique within parameters")
