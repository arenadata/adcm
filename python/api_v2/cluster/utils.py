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
from typing import Literal

from api_v2.cluster.data_containers import MappingData, MappingEntryData
from api_v2.prototype.utils import get_license_text
from cm.api import load_service_map
from cm.api_context import CTX
from cm.data_containers import (
    ClusterData,
    ComponentData,
    Empty,
    HostComponentData,
    HostData,
    PrototypeData,
    RequiresData,
    ServiceData,
)
from cm.errors import AdcmEx
from cm.issue import (
    add_concern_to_object,
    check_components_mapping_contraints,
    remove_concern_from_object,
    update_hierarchy_issues,
    update_issue_after_deleting,
)
from cm.models import (
    Cluster,
    ClusterObject,
    GroupConfig,
    Host,
    HostComponent,
    MaintenanceMode,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from cm.status_api import send_host_component_map_update_event
from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet
from django.db.transaction import atomic, on_commit
from rbac.models import Policy
from rest_framework.status import HTTP_409_CONFLICT


def get_requires(requires: list[dict]) -> dict:
    new_requires = defaultdict(list)

    for require in requires:
        if "component" in require:
            new_requires[require["service"]].append(require["component"])
        elif require["service"] not in new_requires:
            new_requires[require["service"]] = []

    return new_requires


def get_depend_on(
    prototype: Prototype, depend_on: list[dict] | None = None, checked_objects: set[Prototype] | None = None
) -> list[dict]:
    if depend_on is None:
        depend_on = []

    if checked_objects is None:
        checked_objects = set()

    checked_objects.add(prototype)

    for service_name, component_names in get_requires(requires=prototype.requires).items():
        required_service = Prototype.objects.get(type=ObjectType.SERVICE, name=service_name, bundle=prototype.bundle)
        checked_objects.add(required_service)
        service_prototype = {
            "id": required_service.pk,
            "name": required_service.name,
            "display_name": required_service.display_name,
            "version": required_service.version,
            "license": {
                "status": required_service.license,
                "text": get_license_text(
                    license_path=required_service.license_path,
                    path=required_service.path,
                    bundle_hash=required_service.bundle.hash,
                ),
            },
            "component_prototypes": [],
        }

        for component_name in component_names:
            required_component = Prototype.objects.get(
                type=ObjectType.COMPONENT, name=component_name, bundle=prototype.bundle, parent=required_service
            )
            checked_objects.add(required_component)
            service_prototype["component_prototypes"].append(
                {
                    "id": required_component.pk,
                    "name": required_component.name,
                    "display_name": required_component.display_name,
                    "version": required_component.version,
                }
            )

            if required_component.requires and required_component not in checked_objects:
                get_depend_on(prototype=required_component, depend_on=depend_on, checked_objects=checked_objects)

        depend_on.append({"service_prototype": service_prototype})

        if required_service.requires and required_service not in checked_objects:
            get_depend_on(prototype=required_service, depend_on=depend_on, checked_objects=checked_objects)

    return depend_on


def retrieve_mapping_data(
    cluster: Cluster, plain_hc: list[dict[Literal["host_id", "component_id"], int]]
) -> MappingData:
    mapping_data = {
        "cluster": ClusterData.from_orm(obj=cluster),
        "services": {},
        "components": {},
        "hosts": {},
        "prototypes": {},
        "mapping": [],
        "existing_mapping": [],
        "orm_objects": {"cluster": cluster, "hosts": {}, "providers": {}},
        "not_found_object_ids": {},
    }

    for service in (
        ClusterObject.objects.filter(cluster=cluster)
        .select_related("prototype")
        .prefetch_related("servicecomponent_set", "servicecomponent_set__prototype")
    ):
        service: ClusterObject
        mapping_data["services"][service.pk] = ServiceData.from_orm(obj=service)
        mapping_data["prototypes"][service.prototype.pk] = PrototypeData.from_orm(obj=service.prototype)
        for component in service.servicecomponent_set.all():
            component: ServiceComponent
            mapping_data["components"][component.pk] = ComponentData.from_orm(obj=component)
            mapping_data["prototypes"][component.prototype.pk] = PrototypeData.from_orm(obj=component.prototype)

    for host in Host.objects.filter(cluster=cluster).select_related("provider"):
        host: Host
        mapping_data["hosts"][host.pk] = HostData.from_orm(obj=host)
        mapping_data["orm_objects"]["hosts"][host.pk] = host
        mapping_data["orm_objects"]["providers"][host.provider.pk] = host.provider

    for map_ in HostComponent.objects.filter(cluster=cluster):
        mapping_data["existing_mapping"].append(HostComponentData.from_orm(obj=map_))

    mapping_data = MappingData(**mapping_data)

    mapping_data.mapping = [
        MappingEntryData(
            host=mapping_data.hosts[record["host_id"]],
            component=mapping_data.components[record["component_id"]],
            service=mapping_data.services[mapping_data.components[record["component_id"]].service_id],
        )
        for record in plain_hc
        if record["host_id"] in mapping_data.hosts and record["component_id"] in mapping_data.components
    ]
    mapping_data.not_found_object_ids = {
        "hosts": {record["host_id"] for record in plain_hc if record["host_id"] not in mapping_data.hosts},
        "components": {
            record["component_id"] for record in plain_hc if record["component_id"] not in mapping_data.components
        },
    }

    return mapping_data


def save_mapping(mapping_data: MappingData) -> QuerySet[HostComponent]:
    """
    Save given hosts-components mapping if all sanity checks pass
    """

    _check_mapping_data(mapping_data=mapping_data)
    return _save_mapping(mapping_data=mapping_data)


def _check_mapping_data(mapping_data: MappingData) -> None:
    if mapping_data.not_found_object_ids["hosts"]:
        ids_repr = ", ".join([f'"{host_id}"' for host_id in mapping_data.not_found_object_ids["hosts"]])
        raise AdcmEx(
            code="HOST_NOT_FOUND",
            http_code=HTTP_409_CONFLICT,
            msg=f'Host(s) {ids_repr} do not belong to cluster "{mapping_data.cluster.name}"',
        )
    if mapping_data.not_found_object_ids["components"]:
        ids_repr = ", ".join([f'"{component_id}"' for component_id in mapping_data.not_found_object_ids["components"]])
        raise AdcmEx(
            code="COMPONENT_NOT_FOUND",
            http_code=HTTP_409_CONFLICT,
            msg=f'Component(s) {ids_repr} do not belong to cluster "{mapping_data.cluster.name}"',
        )

    seen = set()
    duplicates = set()
    for map_ in mapping_data.mapping:
        ids = (map_.host.id, map_.component.id, map_.service.id)
        if ids in seen:
            duplicates.add(ids)
        seen.add(ids)

    if duplicates:
        error_mapping_repr = ", ".join(
            (f"component {map_ids[1]} - host {map_ids[0]}" for map_ids in sorted(duplicates))
        )
        raise AdcmEx(code="INVALID_INPUT", msg=f"Mapping entries duplicates found: {error_mapping_repr}.")

    hosts_mm_states_in_add_remove_groups = set(
        diff.host.maintenance_mode for diff in mapping_data.mapping_difference["add"]
    ).union(set(diff.host.maintenance_mode for diff in mapping_data.mapping_difference["remove"]))
    if MaintenanceMode.ON.value in hosts_mm_states_in_add_remove_groups:
        raise AdcmEx("INVALID_HC_HOST_IN_MM")

    for mapping_entry in mapping_data.mapping:
        service_prototype, component_prototype = mapping_data.entry_prototypes(entry=mapping_entry)

        if service_prototype.requires or component_prototype.requires:
            _check_single_mapping_requires(mapping_entry=mapping_entry, mapping_data=mapping_data)

        if not isinstance(component_prototype.bound_to, Empty):
            _check_single_mapping_bound_to(mapping_entry=mapping_entry, mapping_data=mapping_data)

    for service in mapping_data.services.values():
        service_prototype = mapping_data.prototypes[service.prototype_id]
        if service_prototype.requires:
            _check_single_service_requires(
                service_prototype=service_prototype, cluster_objects=mapping_data.objects_by_prototype_name
            )
        for component, component_prototype in mapping_data.service_components(service=service):
            check_components_mapping_contraints(
                hosts_count=len(mapping_data.hosts),
                target_mapping_count=len(
                    [
                        map_
                        for map_ in mapping_data.mapping
                        if map_.service.id == service.id and map_.component.id == component.id
                    ]
                ),
                service_prototype=service_prototype,
                component_prototype=component_prototype,
            )


@atomic
def _save_mapping(mapping_data: MappingData) -> QuerySet[HostComponent]:
    on_commit(func=load_service_map)

    for removed_host in mapping_data.removed_hosts:
        remove_concern_from_object(object_=removed_host, concern=CTX.lock)

    for added_host in mapping_data.added_hosts:
        add_concern_to_object(object_=added_host, concern=CTX.lock)

    _handle_mapping_config_groups(mapping_data=mapping_data)

    mapping_objects: list[HostComponent] = []
    for map_ in mapping_data.mapping:
        mapping_objects.append(
            HostComponent(
                cluster_id=mapping_data.cluster.id,
                host_id=map_.host.id,
                service_id=map_.service.id,
                component_id=map_.component.id,
            )
        )

    HostComponent.objects.filter(cluster_id=mapping_data.cluster.id).delete()
    HostComponent.objects.bulk_create(objs=mapping_objects)

    update_hierarchy_issues(obj=mapping_data.orm_objects["cluster"])
    for provider_id in set(host.provider_id for host in mapping_data.hosts.values()):
        update_hierarchy_issues(obj=mapping_data.orm_objects["providers"][provider_id])
    update_issue_after_deleting()

    _handle_mapping_policies(mapping_data=mapping_data)
    send_host_component_map_update_event(cluster=mapping_data.orm_objects["cluster"])

    return HostComponent.objects.filter(cluster_id=mapping_data.cluster.id)


def _handle_mapping_config_groups(mapping_data: MappingData) -> None:
    remaining_host_service = set((diff.host.id, diff.service.id) for diff in mapping_data.mapping_difference["remain"])
    removed_hosts_not_in_mapping = {
        mapping_data.orm_objects["hosts"][removed_mapping.host.id]
        for removed_mapping in mapping_data.mapping_difference["remove"]
        if (removed_mapping.host.id, removed_mapping.service.id) not in remaining_host_service
    }
    removed_mapping_host_ids = {hc.host.id for hc in mapping_data.mapping_difference["remove"]}

    for group_config in GroupConfig.objects.filter(
        object_type__model__in=["clusterobject", "servicecomponent"],
        hosts__in=removed_mapping_host_ids,
    ).distinct():
        group_config.hosts.remove(*removed_hosts_not_in_mapping)


def _handle_mapping_policies(mapping_data: MappingData) -> None:
    service_ids_in_mappings: set[int] = set(
        chain(
            (map_.service.id for map_ in mapping_data.mapping),
            (map_.service_id for map_ in mapping_data.existing_mapping),
        )
    )
    for policy in Policy.objects.filter(
        object__object_id__in=service_ids_in_mappings,
        object__content_type=ContentType.objects.get_for_model(model=ClusterObject),
    ):
        policy.apply()

    for policy in Policy.objects.filter(
        object__object_id=mapping_data.cluster.id,
        object__content_type=ContentType.objects.get_for_model(model=Cluster),
    ):
        policy.apply()


def _check_single_mapping_requires(mapping_entry: MappingEntryData, mapping_data: MappingData) -> None:
    service_prototype, component_prototype = mapping_data.entry_prototypes(entry=mapping_entry)

    for require, source_type in [
        *zip(component_prototype.requires, [component_prototype.type] * len(component_prototype.requires)),
        *zip(service_prototype.requires, [service_prototype.type] * len(service_prototype.requires)),
    ]:
        require: RequiresData

        if require.service not in mapping_data.mapping_names["services"]:
            if source_type == ObjectType.COMPONENT.value:
                reference = f'component "{component_prototype.name}" of service "{service_prototype.name}"'
            else:
                reference = f'service "{service_prototype.name}"'

            raise AdcmEx(
                code="COMPONENT_CONSTRAINT_ERROR", msg=f'No required service "{require.service}" for {reference}'
            )

        if require.component is None:
            continue

        if not [
            mapping_entry
            for mapping_entry in mapping_data.mapping_prototypes
            if mapping_entry[ObjectType.SERVICE.value].name == require.service
            and mapping_entry[ObjectType.COMPONENT.value].name == require.component
        ]:
            if source_type == ObjectType.COMPONENT.value:
                reference = f'component "{component_prototype.name}" of service "{service_prototype.name}"'
            else:
                reference = f'service "{service_prototype.name}"'

            raise AdcmEx(
                code="COMPONENT_CONSTRAINT_ERROR",
                msg=f'No required component "{require.component}" of service "{require.service}" for {reference}',
            )


def _check_single_mapping_bound_to(mapping_entry: MappingEntryData, mapping_data: MappingData) -> None:
    if not mapping_data.entry_bound_targets(entry=mapping_entry):
        service_prototype, component_prototype = mapping_data.entry_prototypes(entry=mapping_entry)

        bound_service_name = component_prototype.bound_to.service
        bound_component_name = component_prototype.bound_to.component

        bound_target_ref = f'component "{bound_component_name}" of service "{bound_service_name}"'
        bound_requester_ref = (
            f'component "{component_prototype.display_name}" of service "{service_prototype.display_name}"'
        )

        msg = f'No {bound_target_ref} on host "{mapping_entry.host.fqdn}" for {bound_requester_ref}'
        raise AdcmEx(code="COMPONENT_CONSTRAINT_ERROR", msg=msg)


def _check_single_service_requires(
    service_prototype: PrototypeData,
    cluster_objects: dict[
        Literal["services", "components"],
        dict[str, dict[Literal["object", "prototype"], ServiceData | ComponentData | PrototypeData]],
    ],
) -> None:
    for require in service_prototype.requires:
        required_service: ServiceData | None = cluster_objects["services"].get(require.service, {}).get("object")
        required_service_prototype: PrototypeData | None = (
            cluster_objects["services"].get(require.service, {}).get("prototype")
        )

        target_reference = f'service "{require.service}"'
        is_requirements_satisfied: bool = required_service is not None and required_service_prototype is not None

        if require.component is not None:
            required_component: ComponentData | None = (
                cluster_objects["components"].get(require.component, {}).get("object")
            )
            required_component_prototype: PrototypeData | None = (
                cluster_objects["components"].get(require.component, {}).get("prototype")
            )

            if required_component is None or required_component_prototype is None:
                target_reference = f'component "{require.component}" of service "{require.service}"'
                is_requirements_satisfied = False

        if not is_requirements_satisfied:
            raise AdcmEx(
                code="SERVICE_CONFLICT",
                msg=f"No required {target_reference} for {service_prototype.reference}",
            )
