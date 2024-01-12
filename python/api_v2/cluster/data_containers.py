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
from functools import cached_property
from typing import Any, Literal

from cm.data_containers import (
    ClusterData,
    ComponentData,
    HostComponentData,
    HostData,
    PrototypeData,
    ServiceData,
)
from cm.models import Host


@dataclass
class MappingEntryData:
    host: HostData
    component: ComponentData
    service: ServiceData


@dataclass
class MappingData:
    cluster: ClusterData
    services: dict[int, ServiceData]
    components: dict[int, ComponentData]
    hosts: dict[int, HostData]
    prototypes: dict[int, PrototypeData]
    mapping: list[MappingEntryData]
    existing_mapping: list[HostComponentData]
    orm_objects: dict[Literal["hosts", "cluster", "providers"], dict[int, Any] | Any]
    not_found_object_ids: dict[Literal["hosts", "components"], set]

    @cached_property
    def mapping_difference(self) -> dict[Literal["add", "remove", "remain"], list[MappingEntryData]]:
        input_mapping_ids = {(map_.host.id, map_.component.id, map_.service.id) for map_ in self.mapping}
        existing_mapping_ids = {(map_.host_id, map_.component_id, map_.service_id) for map_ in self.existing_mapping}

        return {
            "add": [
                MappingEntryData(
                    host=self.hosts[ids[0]], component=self.components[ids[1]], service=self.services[ids[2]]
                )
                for ids in input_mapping_ids.difference(existing_mapping_ids)
            ],
            "remove": [
                MappingEntryData(
                    host=self.hosts[ids[0]], component=self.components[ids[1]], service=self.services[ids[2]]
                )
                for ids in existing_mapping_ids.difference(input_mapping_ids)
            ],
            "remain": [
                MappingEntryData(
                    host=self.hosts[ids[0]], component=self.components[ids[1]], service=self.services[ids[2]]
                )
                for ids in input_mapping_ids.intersection(existing_mapping_ids)
            ],
        }

    @cached_property
    def mapping_names(self) -> dict[Literal["services", "components"], set[str]]:
        return {
            "services": {
                self.prototypes[map_.service.prototype_id].name
                for map_ in self.mapping
                if self.prototypes[map_.service.prototype_id].type == "service"
            },
            "components": {
                self.prototypes[map_.service.prototype_id].name
                for map_ in self.mapping
                if self.prototypes[map_.service.prototype_id].type == "component"
            },
        }

    @cached_property
    def mapping_prototypes(self) -> list[dict[Literal["service", "component"], PrototypeData]]:
        return [
            {
                "service": self.prototypes[map_.service.prototype_id],
                "component": self.prototypes[map_.component.prototype_id],
            }
            for map_ in self.mapping
        ]

    @cached_property
    def objects_by_prototype_name(
        self,
    ) -> dict[
        Literal["services", "components"],
        dict[str, dict[Literal["object", "prototype"], ServiceData | ComponentData | PrototypeData]],
    ]:
        return {
            "components": {
                self.prototypes[obj.prototype_id].name: {"object": obj, "prototype": self.prototypes[obj.prototype_id]}
                for obj in self.components.values()
            },
            "services": {
                self.prototypes[obj.prototype_id].name: {"object": obj, "prototype": self.prototypes[obj.prototype_id]}
                for obj in self.services.values()
            },
        }

    @cached_property
    def added_hosts(self) -> list[Host]:
        existing_host_ids = {map_.host_id for map_ in self.existing_mapping}

        return [
            self.orm_objects["hosts"][map_.host.id] for map_ in self.mapping if map_.host.id not in existing_host_ids
        ]

    @cached_property
    def removed_hosts(self) -> list[Host]:
        mapping_host_ids = {map_.host.id for map_ in self.mapping}

        return [
            self.orm_objects["hosts"][map_.host_id]
            for map_ in self.existing_mapping
            if map_.host_id not in mapping_host_ids
        ]

    def entry_prototypes(self, entry: MappingEntryData) -> tuple[PrototypeData, PrototypeData]:
        service_prototype = self.prototypes[entry.service.prototype_id]
        component_prototype = self.prototypes[entry.component.prototype_id]

        return service_prototype, component_prototype

    def entry_bound_targets(self, entry: MappingEntryData) -> list[MappingEntryData]:
        _, component_prototype = self.entry_prototypes(entry=entry)
        bound_to = component_prototype.bound_to

        bound_targets: list[MappingEntryData] = []
        for mapping_entry in self.mapping:
            service_prototype, component_prototype = self.entry_prototypes(entry=mapping_entry)
            if all(
                (
                    service_prototype.name == bound_to.service,
                    component_prototype.name == bound_to.component,
                    entry.host.id == mapping_entry.host.id,
                )
            ):
                bound_targets.append(mapping_entry)

        return bound_targets

    def service_components(self, service: ServiceData) -> list[tuple[ComponentData, PrototypeData]]:
        service_prototype = self.prototypes[service.prototype_id]

        target_components = []
        for component in self.components.values():
            component_prototype = self.prototypes[component.prototype_id]
            if component_prototype.parent_id == service_prototype.id:
                target_components.append((component, component_prototype))

        return target_components
