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

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Collection, Literal, TypeAlias

from cm.converters import core_type_to_model
from cm.models import ConfigRevision, JobLog
from cm.services.config import ConfigAttrPair, retrieve_config_attr_pairs, retrieve_configs_with_revision
from cm.services.config.spec import FlatSpec, retrieve_flat_spec_for_objects
from cm.services.config.types import RelatedConfigs
from core.types import (
    ADCMCoreType,
    ConfigID,
    CoreObjectDescriptor,
    ObjectID,
    PrototypeID,
)
from django.db.transaction import atomic

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    BaseArgumentsWithTypedObjects,
    CallResult,
    PluginExecutorConfig,
    RuntimeEnvironment,
    TargetConfig,
    from_objects,
)
from ansible_plugin.errors import PluginValidationError

ObjectName: TypeAlias = str  # service_name.component_name for components
ParameterName: TypeAlias = str
AttributeName: TypeAlias = str
GroupName: TypeAlias = str
OldValue: TypeAlias = Any
NewValue: TypeAlias = Any
_InnermostDiffValue: TypeAlias = dict[Literal["value"], tuple[OldValue, NewValue]]
_ParamOrAttrDiff = dict[ParameterName | AttributeName, _InnermostDiffValue]
_ConfigDiff: TypeAlias = dict[GroupName, _ParamOrAttrDiff] | _ParamOrAttrDiff
DiffValue: TypeAlias = (
    dict[Literal["CLUSTER", "PROVIDER"], dict[Literal["diff", "attr_diff"], _ConfigDiff]]
    | dict[
        Literal["services", "components", "hosts"], dict[ObjectName, dict[Literal["diff", "attr_diff"], _ConfigDiff]]
    ]
)


@dataclass(slots=True)
class TargetInfo:
    name: str
    prototype_id: PrototypeID
    old_prototype_id: PrototypeID | None = None
    current_config: ConfigAttrPair | None = None
    revision_config: ConfigAttrPair | None = None
    spec: FlatSpec | None = None


class Operation(str, Enum):
    GET_PRIMARY_DIFF = "get_primary_diff"
    SET_PRIMARY_REVISION = "set_primary_revision"


class ManageRevisionArguments(BaseArgumentsWithTypedObjects):
    operation: Operation


def validate_objects(arguments: ManageRevisionArguments) -> PluginValidationError | None:
    """
    Check that at least one object is passed and all passed objects belong to cluster or provider hierarchy.
    """

    cluster_types = {"cluster", "service", "component"}
    provider_types = {"provider", "host"}

    object_types = {obj.type for obj in arguments.objects}

    if not object_types:
        return PluginValidationError("At least one object must be specified")

    in_cluster_types = bool(object_types.intersection(cluster_types))
    in_provider_types = bool(object_types.intersection(provider_types))
    if (in_cluster_types and in_provider_types) or not (in_cluster_types or in_provider_types):
        return PluginValidationError(f"Target objects must belong to {cluster_types} or {provider_types} hierarchy")


class ADCMManageRevisionPluginExecutor(ADCMAnsiblePluginExecutor[ManageRevisionArguments, DiffValue | None]):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=ManageRevisionArguments, validators=(validate_objects,)),
        target=TargetConfig(detectors=(from_objects,)),
    )

    def __call__(
        self, targets: Collection[CoreObjectDescriptor], arguments: ManageRevisionArguments, runtime: RuntimeEnvironment
    ) -> CallResult[DiffValue | None]:
        existing_targets: dict[CoreObjectDescriptor, TargetInfo] = self._get_existing_targets(targets=targets)
        related_configs: dict[CoreObjectDescriptor, ConfigID] = self._get_related_configs_of_targets(
            job_id=runtime.vars.job.id, targets=existing_targets
        )

        match arguments.operation:
            case Operation.SET_PRIMARY_REVISION:
                value, changed = self._set_primary_revisions(configs=set(related_configs.values()))

            case Operation.GET_PRIMARY_DIFF:
                value, changed = self._get_primary_diff(targets=existing_targets, current_configs=related_configs)

        return CallResult(value=value, changed=changed, error=None)

    @atomic
    def _set_primary_revisions(self, configs: set[ConfigID]) -> tuple[None, bool]:
        existing_revisions = ConfigRevision.objects.filter(configlog_id__in=configs).values_list(
            "configlog_id", flat=True
        )
        if set(existing_revisions) == configs:
            return None, False

        ConfigRevision.objects.filter(configlog_id__in=configs).delete()
        ConfigRevision.objects.bulk_create(objs=[ConfigRevision(configlog_id=id_) for id_ in configs])

        return None, True

    def _get_primary_diff(
        self, targets: dict[CoreObjectDescriptor, TargetInfo], current_configs: dict[CoreObjectDescriptor, ConfigID]
    ) -> tuple[DiffValue, bool]:
        configs_with_revision: dict[CoreObjectDescriptor, ConfigID] = self._get_configs_with_revision(targets=targets)
        suitable_targets: dict[CoreObjectDescriptor, TargetInfo] = self._get_suitable_targets(
            current_configs=current_configs, revisions=configs_with_revision, targets=targets
        )

        return self._make_diff(targets=suitable_targets), False

    def _make_diff(self, targets: dict[CoreObjectDescriptor, TargetInfo]) -> DiffValue:
        diff = defaultdict(dict)
        for cod, info in targets.items():
            groups: set[str] = {
                param_name.rstrip("/") for param_name, value in info.spec.items() if value.type == "group"
            }
            activatable_groups: set[str] = {
                param_name for param_name in groups if info.spec[f"{param_name}/"].limits.get("activatable", False)
            }
            config_diff, attr_diff = self._get_configs_diff(
                old_config=info.revision_config,
                new_config=info.current_config,
                group_keys=groups,
                activatable_group_keys=activatable_groups,
            )

            diff_value = {}
            if not (config_diff or attr_diff):
                continue

            diff_value["diff"] = config_diff
            diff_value["attr_diff"] = attr_diff

            match cod.type:
                case ADCMCoreType.CLUSTER:
                    diff["CLUSTER"] = diff_value
                case ADCMCoreType.PROVIDER:
                    diff["PROVIDER"] = diff_value
                case _:
                    diff[f"{cod.type.value}s"][info.name] = diff_value

        return diff

    def _get_configs_diff(
        self,
        old_config: ConfigAttrPair | dict,
        new_config: ConfigAttrPair | dict,
        group_keys: set[str] | None = None,
        activatable_group_keys: set[str] | None = None,
        in_group: bool = False,
    ) -> tuple[_ConfigDiff, _ConfigDiff]:
        group_keys = group_keys or set()
        activatable_group_keys = activatable_group_keys or set()

        diff, attr_dif = {}, defaultdict(dict)
        config = old_config if in_group else old_config.config
        for param_name in config:
            param_name: str

            if param_name in group_keys:
                group_name = param_name

                group_diff, _ = self._get_configs_diff(
                    old_config=old_config.config[group_name], new_config=new_config.config[group_name], in_group=True
                )
                if group_diff:
                    diff[group_name] = group_diff

                if group_name in activatable_group_keys:
                    old_active = old_config.attr[group_name]["active"]
                    new_active = new_config.attr[group_name]["active"]
                    if old_active != new_active:
                        attr_dif[group_name]["active"] = {"value": [old_active, new_active]}

                continue

            if in_group:
                old_value = old_config[param_name]
                new_value = new_config[param_name]
            else:
                old_value = old_config.config[param_name]
                new_value = new_config.config[param_name]
            if old_value != new_value:
                diff[param_name] = {"value": [old_value, new_value]}

        return diff, attr_dif

    def _get_suitable_targets(
        self,
        current_configs: dict[CoreObjectDescriptor, ConfigID],
        revisions: dict[CoreObjectDescriptor, ConfigID],
        targets: dict[CoreObjectDescriptor, TargetInfo],
    ) -> dict[CoreObjectDescriptor, TargetInfo]:
        all_config_ids: set[ConfigID] = set()
        all_prototype_ids: set[PrototypeID] = set()
        suitable_targets: set[CoreObjectDescriptor] = set()
        target_configs_map: dict[CoreObjectDescriptor, dict[Literal["current", "revision"], ConfigID]] = {}

        # collect targets with both current and revision configs and without prototype changes (schema stays the same);
        for cod in current_configs:
            target: TargetInfo | None = targets.get(cod)
            if not target:
                continue

            current_config_id: ConfigID = current_configs[cod]
            revision_config_id: ConfigID | None = revisions.get(cod)
            if (
                revision_config_id
                and current_config_id != revision_config_id
                and target.old_prototype_id
                and target.prototype_id == target.old_prototype_id
            ):
                target_configs_map[cod] = {"current": current_config_id, "revision": revision_config_id}
                suitable_targets.add(cod)

                all_config_ids.update((current_config_id, revision_config_id))
                all_prototype_ids.add(target.prototype_id)

        # enrich each target's data with corresponding configs, attrs and specs
        configs: dict[ConfigID, ConfigAttrPair] = retrieve_config_attr_pairs(configurations=all_config_ids)
        flat_specs: dict[PrototypeID, FlatSpec] = retrieve_flat_spec_for_objects(prototypes=all_prototype_ids)
        for target_cod in suitable_targets:
            targets[target_cod].current_config = configs[target_configs_map[target_cod]["current"]]
            targets[target_cod].revision_config = configs[target_configs_map[target_cod]["revision"]]
            targets[target_cod].spec = flat_specs[targets[target_cod].prototype_id]

        return {cod: target_info for cod, target_info in targets.items() if cod in suitable_targets}

    @staticmethod
    def _get_configs_with_revision(
        targets: dict[CoreObjectDescriptor, TargetInfo],
    ) -> dict[CoreObjectDescriptor, ConfigID]:
        type_ids_map: dict[ADCMCoreType, set[ObjectID]] = defaultdict(set)
        for target in targets:
            type_ids_map[target.type].add(target.id)

        return retrieve_configs_with_revision(objects=type_ids_map)

    def _get_related_configs_of_targets(
        self, job_id: int, targets: dict[CoreObjectDescriptor, TargetInfo]
    ) -> dict[CoreObjectDescriptor, ConfigID]:
        """Retrieve saved `objects_related_configs` suitable for `targets`, enrich targets with old prototype_id"""
        related_configs = self._get_related_configs(job_id=job_id)
        if not related_configs:
            return {}

        object_config_map: dict[CoreObjectDescriptor, ConfigID] = {}
        for cfg in related_configs:
            id_, type_, prototype_id = cfg["object_id"], cfg["object_type"], cfg["prototype_id"]

            cod = CoreObjectDescriptor(id=id_, type=ADCMCoreType(type_))
            if cod not in targets:
                continue

            targets[cod].old_prototype_id = prototype_id
            object_config_map[cod] = cfg["primary_config_id"]

        return object_config_map

    @staticmethod  # In a separate method for testing purposes
    def _get_related_configs(job_id: int) -> list[RelatedConfigs] | None:
        return JobLog.objects.values_list("objects_related_configs", flat=True).get(id=job_id)

    @staticmethod
    def _get_existing_targets(targets: Collection[CoreObjectDescriptor]) -> dict[CoreObjectDescriptor, TargetInfo]:
        """Returns existing targets with some extra info (name and current prototype_id)"""

        existing_targets: dict[CoreObjectDescriptor, TargetInfo] = {}
        targets_by_type: dict[ADCMCoreType, set[ObjectID]] = defaultdict(set)
        for target in targets:
            targets_by_type[target.type].add(target.id)

        for core_type, ids in targets_by_type.items():
            match core_type:
                case ADCMCoreType.HOST:
                    name_fields = ("fqdn",)
                case ADCMCoreType.COMPONENT:
                    name_fields = ("prototype__parent__name", "prototype__name")
                case _:
                    name_fields = ("prototype__name",)

            for object_id, prototype_id, *rest in (
                core_type_to_model(core_type).objects.filter(id__in=ids).values_list("id", "prototype_id", *name_fields)
            ):
                existing_targets[CoreObjectDescriptor(id=object_id, type=core_type)] = TargetInfo(
                    name=".".join(rest), prototype_id=prototype_id
                )

        return existing_targets
