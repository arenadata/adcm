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
from itertools import chain
from operator import itemgetter
from typing import Collection, NamedTuple, TypeAlias

from core.types import ADCMCoreType, CoreObjectDescriptor, PrototypeID
from django.db.models import Value
import core

from cm.converters import db_record_type_to_core_type
from cm.models import Cluster, ClusterBind, PrototypeExport, PrototypeImport, Service

ImportedObjectName: TypeAlias = str


class _ImportTarget(NamedTuple):
    prototype_id: PrototypeID
    multibind: bool
    default: tuple[str, ...] | None


def get_imports_for_inventory(cluster_id: int, config_service: core.config.ConfigService) -> dict:
    targets = _get_import_targets_for_bundle(
        bundle_id=Cluster.objects.values_list("prototype__bundle_id", flat=True).get(id=cluster_id)
    )

    if not targets:
        return {}

    existing_objects_prototypes = set(
        Cluster.objects.values_list("prototype_id", flat=True)
        .filter(id=cluster_id)
        .union(Service.objects.filter(cluster_id=cluster_id).values_list("prototype_id", flat=True))
    )
    targets = {
        core_type: target for core_type, target in targets.items() if target.prototype_id in existing_objects_prototypes
    }

    if not targets:
        return {}

    binds_info: dict[tuple[ADCMCoreType, str], list[dict]] = _get_binds_for_cluster(cluster_id=cluster_id)

    configurations = _get_configurations_prepared_for_inventory(binds=binds_info, config_service=config_service)

    # values are names of fields to export
    exports_info = defaultdict(set)
    for prototype_id, field_name in PrototypeExport.objects.values_list("prototype_id", "name").filter(
        prototype_id__in=map(itemgetter("prototype_id"), chain.from_iterable(binds_info.values()))
    ):
        exports_info[prototype_id].add(field_name)

    imports = {}

    fill_with_defaults = set()

    for (import_type, import_name, _), target in targets.items():
        sources = binds_info.get((import_type, import_name))

        if not sources:
            if target.default:
                fill_with_defaults.add((import_name, target))

            continue

        if target.multibind:
            imports[import_name] = [
                _extract_required_fields(
                    config=configurations[source["config_id"]].values, fields=exports_info[source["prototype_id"]]
                )
                for source in sources
                if source["config_id"] in configurations
            ]

            continue

        source = sources[0]
        imports[import_name] = _extract_required_fields(
            config=configurations[source["config_id"]].values, fields=exports_info[source["prototype_id"]]
        )

    if fill_with_defaults:
        _fill_imports_with_defaults_inplace(
            imports=imports, fill_with_defaults=fill_with_defaults, config_service=config_service
        )

    return imports


def _get_import_targets_for_bundle(
    bundle_id: int,
) -> dict[tuple[ADCMCoreType, ImportedObjectName, PrototypeID], _ImportTarget]:
    """Information about what can be imported to cluster and its services"""
    return {
        (db_record_type_to_core_type(row["prototype__type"]), row["name"], row["prototype_id"]): _ImportTarget(
            prototype_id=row["prototype_id"],
            multibind=row["multibind"],
            default=tuple(default) if (default := row["default"]) is not None else None,
        )
        for row in PrototypeImport.objects.values(
            "prototype_id", "prototype__type", "name", "multibind", "default"
        ).filter(prototype__bundle_id=bundle_id)
    }


def _get_binds_for_cluster(cluster_id: int) -> dict[tuple[ADCMCoreType, str], list[dict]]:
    """
    Binds are objects from which configurations are exported.
    First type (in return value key) is type of target object.
    """
    available_sources = defaultdict(list)

    for existing_bind in ClusterBind.objects.select_related(
        "source_cluster__config", "source_cluster__prototype", "source_service__config", "source_service__prototype"
    ).filter(cluster_id=cluster_id):
        target_object_type = ADCMCoreType.SERVICE if existing_bind.service else ADCMCoreType.CLUSTER

        if existing_bind.source_service:
            imported_object = existing_bind.source_service
            imported_object_type = ADCMCoreType.SERVICE
        else:
            imported_object = existing_bind.source_cluster
            imported_object_type = ADCMCoreType.CLUSTER

        available_sources[(target_object_type, imported_object.prototype.name)].append(
            {
                "object_id": imported_object.pk,
                "object_type": imported_object_type,
                "prototype_id": imported_object.prototype_id,
                "config_id": imported_object.config.current,
            }
        )

    return available_sources


def _get_configurations_prepared_for_inventory(
    binds: dict[tuple[ADCMCoreType, str], list[dict]], config_service: core.config.ConfigService
):
    config_ids = map(itemgetter("config_id"), chain.from_iterable(binds.values()))
    configurations = config_service.retrieve_configurations_by_id(configurations=config_ids)

    prototype_ids = map(itemgetter("prototype_id"), chain.from_iterable(binds.values()))
    specifications_for_prototypes = config_service.retrieve_specifications_by_prototypes(prototypes=prototype_ids)

    # actually we don't need to process the whole configurations here, just exported fields,
    # but currently types are too complex to write this selection in an understandable way
    processed_configs = set()
    for source in chain.from_iterable(binds.values()):
        config_id = source["config_id"]
        if config_id in processed_configs:
            continue

        owner = CoreObjectDescriptor(id=source["object_id"], type=source["object_type"])

        config_service.prepare_configuration_for_ansible(
            configuration=configurations[config_id],
            specification=specifications_for_prototypes[source["prototype_id"]],
            file_owner=owner,
            inplace=True,
        )

        processed_configs.add(config_id)

    return configurations


def _extract_required_fields(config: dict, fields: Collection[str]) -> dict:
    return {field: config[field] for field in fields}


def _fill_imports_with_defaults_inplace(
    imports: dict,
    fill_with_defaults: set[tuple[ImportedObjectName, _ImportTarget]],
    config_service: core.config.ConfigService,
):
    still_required_to_fill = {entry for entry in fill_with_defaults if entry[0] not in imports}
    if not still_required_to_fill:
        return imports

    required_prototypes = set(map(itemgetter(1), still_required_to_fill))
    specifications = config_service.retrieve_specifications_by_prototypes(prototypes=required_prototypes)

    cluster_query = Cluster.objects.values(
        "id", "config__current", "prototype_id", type=Value(ADCMCoreType.CLUSTER.value)
    ).filter(prototype_id__in=required_prototypes)
    service_query = Service.objects.values(
        "id", "config__current", "prototype_id", type=Value(ADCMCoreType.SERVICE.value)
    ).filter(prototype_id__in=required_prototypes)

    objects = {
        row["prototype_id"]: (CoreObjectDescriptor(row["id"], row["type"]), row["config__current"])
        for row in cluster_query.union(service_query)
    }
    config_ids = map(itemgetter(1), objects.values())
    configurations = config_service.retrieve_configurations_by_id(configurations=config_ids)

    for import_name, target in still_required_to_fill:
        object_, config_id = objects[target.prototype_id]
        updated_configuration = config_service.prepare_configuration_for_ansible(
            configuration=configurations[config_id],
            specification=specifications[target.prototype_id],
            file_owner=object_,
        )
        config_ = updated_configuration.values
        imports[import_name] = [config_] if target.multibind else config_

    return imports
