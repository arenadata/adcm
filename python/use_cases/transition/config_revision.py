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
from typing import Collection, Literal, TypeAlias

from cm.converters import core_type_to_model
from cm.legacy.services.config import retrieve_configs_with_revision
from cm.models import ConfigRevision, JobLog
from core.types import ADCMCoreType, ConfigID, CoreObjectDescriptor, ObjectID, PrototypeID
from django.db.transaction import atomic
import core

# This module should be merged with config use case module when it is clean enough (no direct queries)

ObjectName: TypeAlias = str  # service_name.component_name for components
HasChanged: TypeAlias = bool
DiffValue: TypeAlias = (
    dict[Literal["CLUSTER", "PROVIDER"], core.config.RevisionDiff]
    | dict[Literal["services", "components", "hosts"], dict[ObjectName, core.config.RevisionDiff]]
)


@dataclass(slots=True)
class TargetInfo:
    name: str
    prototype_id: PrototypeID
    old_prototype_id: PrototypeID | None = None
    current_config: core.config.Configuration | None = None
    revision_config: core.config.Configuration | None = None
    spec: core.config.spec.FullSpec | None = None


@dataclass(slots=True)
class SetPrimaryConfigRevision:
    @atomic
    def do(self, *, targets: Collection[CoreObjectDescriptor], job_id: int) -> HasChanged:
        existing_targets = _get_existing_targets(targets=targets)
        related_configs = _get_related_configs_of_targets(job_id=job_id, targets=existing_targets)
        configs = set(related_configs.values())

        existing_revisions = ConfigRevision.objects.filter(configlog_id__in=configs).values_list(
            "configlog_id", flat=True
        )
        if set(existing_revisions) == configs:
            return False

        ConfigRevision.objects.filter(configlog_id__in=configs).delete()
        ConfigRevision.objects.bulk_create(objs=[ConfigRevision(configlog_id=id_) for id_ in configs])

        return True


@dataclass(slots=True)
class FindPrimaryConfigDiff:
    config_service: core.config.ConfigService

    def do(self, *, targets: Collection[CoreObjectDescriptor], job_id: int) -> DiffValue:
        existing_targets = _get_existing_targets(targets=targets)
        current_configs = _get_related_configs_of_targets(job_id=job_id, targets=existing_targets)

        configs_with_revision: dict[CoreObjectDescriptor, ConfigID] = self._get_configs_with_revision(
            targets=existing_targets
        )
        suitable_targets: dict[CoreObjectDescriptor, TargetInfo] = self._get_suitable_targets(
            current_configs=current_configs, revisions=configs_with_revision, targets=existing_targets
        )

        return self._make_diff(targets=suitable_targets)

    def _make_diff(self, targets: dict[CoreObjectDescriptor, TargetInfo]) -> DiffValue:
        diff = defaultdict(dict)
        diffs_input: dict[CoreObjectDescriptor, core.config.RevisionDiffSource] = {}
        for cod, target_info in targets.items():
            if not target_info.spec or not target_info.current_config or not target_info.revision_config:
                continue

            diffs_input[cod] = core.config.RevisionDiffSource(
                revision=target_info.revision_config,
                current=target_info.current_config,
                specification=target_info.spec,
            )

        per_object_diff = self.config_service.prepare_revision_diffs(revisions=diffs_input)
        for cod, diff_value in per_object_diff.items():
            if not (diff_value["diff"] or diff_value["attr_diff"]):
                continue

            match cod.type:
                case ADCMCoreType.CLUSTER:
                    diff["CLUSTER"] = diff_value
                case ADCMCoreType.PROVIDER:
                    diff["PROVIDER"] = diff_value
                case _:
                    diff[f"{cod.type.value}s"][targets[cod].name] = diff_value

        return diff

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
        configs = self.config_service.retrieve_configurations_by_id(configurations=all_config_ids)
        specs = self.config_service.retrieve_specifications_by_prototypes(prototypes=all_prototype_ids)
        for target_cod in suitable_targets:
            targets[target_cod].current_config = configs[target_configs_map[target_cod]["current"]]
            targets[target_cod].revision_config = configs[target_configs_map[target_cod]["revision"]]
            targets[target_cod].spec = specs[targets[target_cod].prototype_id]

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
    *, job_id: int, targets: dict[CoreObjectDescriptor, TargetInfo]
) -> dict[CoreObjectDescriptor, ConfigID]:
    """Retrieve saved `objects_related_configs` suitable for `targets`, enrich targets with old prototype_id."""
    related_configs = _get_related_configs(job_id=job_id)
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


def _get_related_configs(*, job_id: int) -> list[core.config.RelatedConfigs] | None:
    return JobLog.objects.values_list("objects_related_configs", flat=True).get(id=job_id)


def _get_existing_targets(*, targets: Collection[CoreObjectDescriptor]) -> dict[CoreObjectDescriptor, TargetInfo]:
    """Returns existing targets with some extra info (name and current prototype_id)."""
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
