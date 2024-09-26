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

from collections import defaultdict, deque
from functools import partial
from operator import attrgetter
from typing import Callable, Iterable, Literal, NamedTuple, TypeAlias

from core.cluster.types import ClusterTopology, ServiceTopology
from core.types import ClusterID, ComponentID, ConfigID, HostID, MappingDict, ObjectID, PrototypeID, ServiceID
from django.db.models import Q
from typing_extensions import Self

from cm.models import (
    Cluster,
    ClusterBind,
    Component,
    Host,
    HostProvider,
    ObjectConfig,
    ObjectType,
    Prototype,
    PrototypeImport,
    Service,
)
from cm.services.cluster import retrieve_clusters_topology
from cm.services.config import retrieve_config_attr_pairs
from cm.services.config.spec import FlatSpec, retrieve_flat_spec_for_objects

ObjectWithConfig: TypeAlias = Cluster | Service | Component | HostProvider | Host
HasIssue: TypeAlias = bool
RequiresEntry: TypeAlias = dict[Literal["service", "component"], str]
ConstraintDBFormat: TypeAlias = tuple[str] | tuple[int | str, int | str]


class MissingRequirement(NamedTuple):
    type: Literal["service", "component"]
    name: str


class Constraint(NamedTuple):
    internal: ConstraintDBFormat
    checks: tuple[Callable[[int, int], bool], ...]

    @classmethod
    def from_db_repr(cls, constraint: ConstraintDBFormat) -> Self:
        match constraint:
            case [0, "+"]:
                # no checks actually required, it's the "default"
                checks = ()
            case ["+"]:
                checks = (check_on_all,)
            case ["odd"]:
                checks = (check_is_odd,)
            case [int(exact)]:
                checks = (partial(check_exact, argument=exact),)
            case [int(min_), "odd"]:
                checks = (partial(check_equal_or_greater, argument=min_), partial(check_is_odd, allow_zero=min_ == 0))
            case [int(min_), "+"]:
                checks = (partial(check_equal_or_greater, argument=min_),)
            case [int(min_), int(max_)]:
                checks = (partial(check_equal_or_greater, argument=min_), partial(check_equal_or_less, argument=max_))
            case _:
                checks = ()

        return Constraint(internal=constraint, checks=checks)

    def is_met_for(self, mapped_hosts: int, hosts_in_cluster: int) -> bool:
        return all(check(mapped_hosts, hosts_in_cluster) for check in self.checks)


class ServiceExternalRequirement(NamedTuple):
    name: str

    def __str__(self):
        return f'service "{self.name}"'


class ComponentExternalRequirement(NamedTuple):
    name: str
    service_name: str

    def __str__(self):
        return f'component "{self.name}" of service "{self.service_name}"'


class ServiceRequirements(NamedTuple):
    requires: tuple[ServiceExternalRequirement | ComponentExternalRequirement, ...]

    @property
    def is_requires_check_required(self) -> bool:
        return len(self.requires) > 0


class ComponentMappingRequirements(NamedTuple):
    constraint: Constraint
    requires: tuple[ServiceExternalRequirement | ComponentExternalRequirement, ...]
    bound_to: ComponentExternalRequirement | None

    @property
    def is_constraint_check_required(self) -> bool:
        return len(self.constraint.checks) > 0

    @property
    def is_requires_check_required(self) -> bool:
        return len(self.requires) > 0

    @property
    def is_bound_to_check_required(self) -> bool:
        return self.bound_to is not None


class RequirementsCheckDTO(NamedTuple):
    topology: ClusterTopology
    component_prototype_map: dict[ComponentID, tuple[PrototypeID, ServiceID, PrototypeID]]
    prototype_requirements: dict[PrototypeID, ComponentMappingRequirements | ServiceRequirements]
    existing_objects_map: dict[ComponentExternalRequirement | ServiceExternalRequirement, ComponentID | ServiceID]

    @property
    def prototype_requirements_only_component_requires(
        self,
    ) -> dict[PrototypeID, ComponentMappingRequirements | ServiceRequirements]:
        res = {}

        for prototype_id, requirements in self.prototype_requirements.items():
            new_requires = tuple(req for req in requirements.requires if isinstance(req, ComponentExternalRequirement))

            if isinstance(requirements, ComponentMappingRequirements):
                new_requirements = ComponentMappingRequirements(
                    constraint=requirements.constraint, requires=new_requires, bound_to=requirements.bound_to
                )
            elif isinstance(requirements, ServiceRequirements):
                new_requirements = ServiceRequirements(requires=new_requires)
            else:
                raise NotImplementedError(f"Unexpected requirements type: {type(requirements)}")

            res[prototype_id] = new_requirements

        return res

    @property
    def objects_map_by_type(
        self,
    ) -> dict[
        Literal["service", "component"],
        dict[ServiceID | ComponentID, ServiceExternalRequirement | ComponentExternalRequirement],
    ]:
        existing_objects = defaultdict(dict)

        for entity_reqs, entity_id in self.existing_objects_map.items():
            if isinstance(entity_reqs, ComponentExternalRequirement):
                existing_objects["component"][entity_id] = entity_reqs
            elif isinstance(entity_reqs, ServiceExternalRequirement):
                existing_objects["service"][entity_id] = entity_reqs

        return existing_objects


def object_configuration_has_issue(target: ObjectWithConfig) -> HasIssue:
    config_spec = next(iter(retrieve_flat_spec_for_objects(prototypes=(target.prototype_id,)).values()), None)
    if not config_spec:
        return False

    return target.id in filter_objects_with_configuration_issues(config_spec, target)


def object_imports_has_issue(target: Cluster | Service) -> HasIssue:
    prototype_id = target.prototype_id
    prototype_imports = PrototypeImport.objects.filter(prototype_id=prototype_id)
    required_import_names = set(prototype_imports.values_list("name", flat=True).filter(required=True))

    if not required_import_names:
        return False

    if not any(prototype_imports.values_list("required", flat=True)):
        return False

    for cluster_name, service_name in ClusterBind.objects.values_list(
        "source_cluster__prototype__name", "source_service__prototype__name"
    ).filter(Q(cluster__prototype_id=prototype_id) | Q(service__prototype_id=prototype_id)):
        if service_name:
            required_import_names -= {service_name}
        elif cluster_name:
            required_import_names -= {cluster_name}

    return required_import_names != set()


def object_has_required_services_issue(cluster: Cluster) -> HasIssue:
    bundle_id = cluster.prototype.bundle_id

    required_protos = Prototype.objects.filter(bundle_id=bundle_id, type="service", required=True)

    if (required_count := required_protos.count()) == 0:
        return False

    existing_required_objects = Service.objects.filter(cluster=cluster, prototype__in=required_protos)
    return existing_required_objects.count() != required_count


def filter_objects_with_configuration_issues(config_spec: FlatSpec, *objects: ObjectWithConfig) -> Iterable[ObjectID]:
    required_fields = tuple(name for name, spec in config_spec.items() if spec.required and spec.type != "group")
    if not required_fields:
        return ()

    object_config_log_map: dict[int, ConfigID] = dict(
        ObjectConfig.objects.values_list("id", "current").filter(id__in=map(attrgetter("config_id"), objects))
    )
    config_pairs = retrieve_config_attr_pairs(configurations=object_config_log_map.values())

    objects_with_issues: deque[ObjectID] = deque()
    for object_ in objects:
        config, attr = config_pairs[object_config_log_map[object_.config_id]]

        for composite_name in required_fields:
            group_name, field_name, *_ = composite_name.split("/")
            if not field_name:
                field_name = group_name
                group_name = None

            if group_name:
                if not attr.get(group_name, {}).get("active", False):
                    continue

                if config[group_name][field_name] is None:
                    objects_with_issues.append(object_.id)
                    break

            elif config[field_name] is None:
                objects_with_issues.append(object_.id)
                break

    return objects_with_issues


def service_requirements_has_issue(service: Service) -> HasIssue:
    return bool(find_unsatisfied_requirements(cluster_id=service.cluster_id, requires=service.prototype.requires))


def find_unsatisfied_requirements(
    cluster_id: ClusterID, requires: list[RequiresEntry]
) -> tuple[MissingRequirement, ...]:
    if not requires:
        return ()

    names_of_required_services: set[str] = set()
    required_components: set[tuple[str, str]] = set()

    for requirement in requires:
        service_name = requirement["service"]

        if component_name := requirement.get("component"):
            required_components.add((service_name, component_name))
        else:
            names_of_required_services.add(service_name)

    missing_requirements = deque()

    if names_of_required_services:
        for missing_service_name in names_of_required_services.difference(
            Service.objects.values_list("prototype__name", flat=True).filter(cluster_id=cluster_id)
        ):
            missing_requirements.append(MissingRequirement(type="service", name=missing_service_name))

    if required_components:
        for _, missing_component_name in required_components.difference(
            Component.objects.values_list("service__prototype__name", "prototype__name").filter(cluster_id=cluster_id)
        ):
            missing_requirements.append(MissingRequirement(type="component", name=missing_component_name))

    return tuple(missing_requirements)


def cluster_mapping_has_issue(cluster: Cluster) -> HasIssue:
    """
    Checks:
      - requires (components only)
      - constraint
      - bound_to
    """

    requirements_data = extract_data_for_requirements_check(cluster=cluster)

    bound_not_ok, _ = is_bound_to_requirements_unsatisfied(
        topology=requirements_data.topology,
        component_prototype_map=requirements_data.component_prototype_map,
        prototype_requirements=requirements_data.prototype_requirements,
        existing_objects_map=requirements_data.existing_objects_map,
    )
    if bound_not_ok:
        return True

    requires_not_ok, _ = is_requires_requirements_unsatisfied(
        topology=requirements_data.topology,
        component_prototype_map=requirements_data.component_prototype_map,
        prototype_requirements=requirements_data.prototype_requirements_only_component_requires,
        existing_objects_map=requirements_data.existing_objects_map,
        existing_objects_by_type=requirements_data.objects_map_by_type,
    )
    if requires_not_ok:
        return True

    constraint_not_ok, _ = is_constraint_requirements_unsatisfied(
        topology=requirements_data.topology,
        component_prototype_map=requirements_data.component_prototype_map,
        prototype_requirements=requirements_data.prototype_requirements,
        components_map=requirements_data.objects_map_by_type["component"],
    )
    if constraint_not_ok:
        return True

    return False


def extract_data_for_requirements_check(
    cluster: Cluster,
    input_mapping: list[MappingDict] | None = None,
    target_component_prototypes: set[PrototypeID] | None = None,
) -> RequirementsCheckDTO:
    bundle_id = cluster.prototype.bundle_id
    prototype_requirements: dict[PrototypeID, ComponentMappingRequirements | ServiceRequirements] = {}

    query = {"bundle_id": bundle_id, "type__in": {ObjectType.COMPONENT, ObjectType.SERVICE}}
    if target_component_prototypes is not None:
        query.update({"pk__in": target_component_prototypes})

    for prototype_id, prototype_type, constraint, requires, bound_to in Prototype.objects.values_list(
        "id", "type", "constraint", "requires", "bound_to"
    ).filter(**query):
        prepared_requires = deque()
        for requirement in requires:
            service_name = requirement["service"]
            if component_name := requirement.get("component"):
                prepared_requires.append(ComponentExternalRequirement(name=component_name, service_name=service_name))
            else:
                prepared_requires.append(ServiceExternalRequirement(name=service_name))

        if prototype_type == ObjectType.COMPONENT:
            prototype_requirements[prototype_id] = ComponentMappingRequirements(
                constraint=Constraint.from_db_repr(constraint),
                requires=tuple(prepared_requires),
                bound_to=ComponentExternalRequirement(name=bound_to["component"], service_name=bound_to["service"])
                if bound_to
                else None,
            )
        elif prototype_type == ObjectType.SERVICE:
            prototype_requirements[prototype_id] = ServiceRequirements(requires=tuple(prepared_requires))
        else:
            raise NotImplementedError(f"Unexpected prototype type: {prototype_type}")

    # prepare data for check

    input_mapping = {cluster.id: input_mapping} if input_mapping else None
    topology = next(retrieve_clusters_topology(cluster_ids=(cluster.id,), input_mapping=input_mapping))

    query = {"cluster": cluster}
    if target_component_prototypes is not None:
        query.update({"components__prototype_id__in": target_component_prototypes})

    component_prototype_map: dict[ComponentID, tuple[PrototypeID, ServiceID, PrototypeID]] = {}
    existing_objects_map: dict[ComponentExternalRequirement | ServiceExternalRequirement, ComponentID | ServiceID] = {
        ServiceExternalRequirement(name=service_name): service_id
        for service_id, service_name in Service.objects.values_list("id", "prototype__name").filter(**query).distinct()
    }

    query = {"id__in": topology.component_ids}
    if target_component_prototypes is not None:
        query.update({"prototype_id__in": target_component_prototypes})

    for (
        component_id,
        prototype_id,
        service_id,
        service_prototype_id,
        component_name,
        service_name,
    ) in Component.objects.values_list(
        "id", "prototype_id", "service_id", "service__prototype_id", "prototype__name", "service__prototype__name"
    ).filter(**query):
        component_prototype_map[component_id] = (prototype_id, service_id, service_prototype_id)
        existing_objects_map[
            ComponentExternalRequirement(name=component_name, service_name=service_name)
        ] = component_id

    return RequirementsCheckDTO(
        topology=topology,
        component_prototype_map=component_prototype_map,
        prototype_requirements=prototype_requirements,
        existing_objects_map=existing_objects_map,
    )


def is_bound_to_requirements_unsatisfied(
    topology: ClusterTopology,
    component_prototype_map: dict[ComponentID, tuple[PrototypeID, ServiceID, PrototypeID]],
    prototype_requirements: dict[PrototypeID, ComponentMappingRequirements | ServiceRequirements],
    existing_objects_map: dict[ComponentExternalRequirement | ServiceExternalRequirement, ComponentID | ServiceID],
) -> tuple[bool, str | None]:
    existing_components: dict[ComponentID, ComponentExternalRequirement] = {}
    for entity_reqs, entity_id in existing_objects_map.items():
        if isinstance(entity_reqs, ComponentExternalRequirement):
            existing_components[entity_id] = entity_reqs

    for component_id, (prototype_id, service_id, _) in component_prototype_map.items():
        requirements = prototype_requirements[prototype_id]

        # only mapped components should be checked for bound_to
        if (
            not requirements.is_bound_to_check_required
            or not topology.services[service_id].components[component_id].hosts
        ):
            continue

        bound_requester_reference = str(existing_components[component_id])
        error_message = f"{str(requirements.bound_to).capitalize()} not in hc for {bound_requester_reference}"

        bound_component_id = existing_objects_map.get(requirements.bound_to)
        if not bound_component_id:
            return True, error_message

        service_id_of_bound_component = existing_objects_map.get(
            ServiceExternalRequirement(name=requirements.bound_to.service_name)
        )
        if not service_id_of_bound_component:
            return True, error_message

        bound_service_topology: ServiceTopology | None = topology.services.get(service_id_of_bound_component)
        if not bound_service_topology:
            return True, error_message

        error_message = f"No {str(requirements.bound_to).capitalize()} on host for {bound_requester_reference}"

        bound_component_hosts: set[HostID] = set(bound_service_topology.components[bound_component_id].hosts)
        current_component_hosts: set[HostID] = set(topology.services[service_id].components[component_id].hosts)

        if bound_component_hosts != current_component_hosts:
            return True, error_message

    return False, None


def is_requires_requirements_unsatisfied(
    topology: ClusterTopology,
    component_prototype_map: dict[ComponentID, tuple[PrototypeID, ServiceID, PrototypeID]],
    prototype_requirements: dict[PrototypeID, ComponentMappingRequirements | ServiceRequirements],
    existing_objects_map: dict[ComponentExternalRequirement | ServiceExternalRequirement, ComponentID | ServiceID],
    existing_objects_by_type: dict[
        Literal["service", "component"],
        dict[ServiceID | ComponentID, ServiceExternalRequirement | ComponentExternalRequirement],
    ],
) -> tuple[bool, str | None]:
    seen_service_prototypes: set[PrototypeID] = set()

    for component_id, (prototype_id, service_id, service_prototype_id) in component_prototype_map.items():
        # only mapped components should be checked for requires
        if not topology.services[service_id].components[component_id].hosts:
            continue

        component_requirements = prototype_requirements[prototype_id]
        service_requirements = None
        if service_prototype_id not in seen_service_prototypes:
            service_requirements = prototype_requirements[service_prototype_id]
            seen_service_prototypes.add(service_prototype_id)

        component_requires = (
            component_requirements.requires if component_requirements.is_requires_check_required else []
        )
        service_requires = (
            service_requirements.requires
            if service_requirements is not None and service_requirements.is_requires_check_required
            else []
        )
        all_requires = [
            *zip(component_requires, [existing_objects_by_type["component"][component_id]] * len(component_requires)),
            *zip(service_requires, [existing_objects_by_type["service"][service_id]] * len(service_requires)),
        ]
        for required_entity, owner in all_requires:
            try:
                if isinstance(required_entity, ComponentExternalRequirement):
                    required_component_id = existing_objects_map[required_entity]
                    required_service_id = existing_objects_map[
                        ServiceExternalRequirement(name=required_entity.service_name)
                    ]
                elif isinstance(required_entity, ServiceExternalRequirement):
                    required_component_id = None
                    required_service_id = existing_objects_map[required_entity]
                else:
                    raise NotImplementedError(f"Unexpected required_entity type: {type(required_entity)}")
            except KeyError:
                return True, f"No required {required_entity} for {owner}"

            if required_component_id is None:
                continue

            if not topology.services[required_service_id].components[required_component_id].hosts:
                return True, f"No required {required_entity} for {owner}"

    return False, None


def is_constraint_requirements_unsatisfied(
    topology: ClusterTopology,
    component_prototype_map: dict[ComponentID, tuple[PrototypeID, ServiceID, PrototypeID]],
    prototype_requirements: dict[PrototypeID, ComponentMappingRequirements | ServiceRequirements],
    components_map: dict[ComponentID, ComponentExternalRequirement],
) -> tuple[bool, str | None]:
    for component_id, (prototype_id, service_id, _) in component_prototype_map.items():
        requirements = prototype_requirements[prototype_id]

        if requirements.is_constraint_check_required and not requirements.constraint.is_met_for(
            mapped_hosts=len(topology.services[service_id].components[component_id].hosts),
            hosts_in_cluster=len(topology.hosts),
        ):
            return (
                True,
                f"{str(components_map[component_id]).capitalize()} "
                f"has unsatisfied constraint: {requirements.constraint.internal}",
            )

    return False, None


# constraint check functions


def check_equal_or_less(mapped_hosts: int, _: int, argument: int):
    return mapped_hosts <= argument


def check_equal_or_greater(mapped_hosts: int, _: int, argument: int):
    return mapped_hosts >= argument


def check_exact(mapped_hosts: int, _: int, argument: int):
    return mapped_hosts == argument


def check_is_odd(mapped_hosts: int, _: int, allow_zero: bool = False):
    if mapped_hosts == 0 and allow_zero:
        return True

    return mapped_hosts % 2 == 1


def check_on_all(mapped_hosts: int, hosts_in_cluster: int):
    return mapped_hosts > 0 and mapped_hosts == hosts_in_cluster
