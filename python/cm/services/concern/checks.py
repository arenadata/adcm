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

from collections import deque
from functools import partial
from operator import attrgetter
from typing import Callable, Iterable, Literal, NamedTuple, TypeAlias

from core.cluster.types import ServiceTopology
from core.types import ClusterID, ComponentID, ConfigID, HostID, ObjectID, PrototypeID, ServiceID
from django.db.models import Q
from typing_extensions import Self

from cm.models import (
    Cluster,
    ClusterBind,
    ClusterObject,
    Host,
    HostProvider,
    ObjectConfig,
    ObjectType,
    Prototype,
    PrototypeImport,
    ServiceComponent,
)
from cm.services.cluster import retrieve_clusters_topology
from cm.services.config import retrieve_config_attr_pairs
from cm.services.config.spec import FlatSpec, retrieve_flat_spec_for_objects

ObjectWithConfig: TypeAlias = Cluster | ClusterObject | ServiceComponent | HostProvider | Host
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
                checks = (partial(check_equal_or_greater, argument=min_), check_is_odd)
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


class ComponentExternalRequirement(NamedTuple):
    name: str
    service_name: str


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


def object_configuration_has_issue(target: ObjectWithConfig) -> HasIssue:
    config_spec = next(iter(retrieve_flat_spec_for_objects(prototypes=(target.prototype_id,)).values()), None)
    if not config_spec:
        return False

    return target.id in filter_objects_with_configuration_issues(config_spec, target)


def object_imports_has_issue(target: Cluster | ClusterObject) -> HasIssue:
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

    existing_required_objects = ClusterObject.objects.filter(cluster=cluster, prototype__in=required_protos)
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


def service_requirements_has_issue(service: ClusterObject) -> HasIssue:
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
            ClusterObject.objects.values_list("prototype__name", flat=True).filter(cluster_id=cluster_id)
        ):
            missing_requirements.append(MissingRequirement(type="service", name=missing_service_name))

    if required_components:
        for _, missing_component_name in required_components.difference(
            ServiceComponent.objects.values_list("service__prototype__name", "prototype__name").filter(
                cluster_id=cluster_id
            )
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

    # extract requirements

    bundle_id = cluster.prototype.bundle_id

    requirements_from_components: dict[PrototypeID, ComponentMappingRequirements] = {}

    for prototype_id, constraint, requires, bound_to in Prototype.objects.values_list(
        "id", "constraint", "requires", "bound_to"
    ).filter(bundle_id=bundle_id, type=ObjectType.COMPONENT):
        prepared_requires = deque()
        for requirement in requires:
            service_name = requirement["service"]
            if component_name := requirement.get("component"):
                # "service" requirements aren't checked for mapping issue
                prepared_requires.append(ComponentExternalRequirement(name=component_name, service_name=service_name))

        requirements_from_components[prototype_id] = ComponentMappingRequirements(
            constraint=Constraint.from_db_repr(constraint),
            requires=tuple(prepared_requires),
            bound_to=ComponentExternalRequirement(name=bound_to["component"], service_name=bound_to["service"])
            if bound_to
            else None,
        )

    # prepare data for check

    topology = next(retrieve_clusters_topology((cluster.id,)))

    component_prototype_map: dict[ComponentID, tuple[PrototypeID, ServiceID]] = {}
    existing_objects_map: dict[ComponentExternalRequirement | ServiceExternalRequirement, ComponentID | ServiceID] = {
        ServiceExternalRequirement(name=service_name): service_id
        for service_id, service_name in ClusterObject.objects.values_list("id", "prototype__name").filter(
            cluster=cluster
        )
    }

    for component_id, prototype_id, service_id, component_name, service_name in ServiceComponent.objects.values_list(
        "id", "prototype_id", "service_id", "prototype__name", "service__prototype__name"
    ).filter(id__in=topology.component_ids):
        component_prototype_map[component_id] = (prototype_id, service_id)
        existing_objects_map[
            ComponentExternalRequirement(name=component_name, service_name=service_name)
        ] = component_id

    hosts_amount = len(topology.hosts)

    existing_objects = set(existing_objects_map.keys())

    # run checks

    for component_id, (prototype_id, service_id) in component_prototype_map.items():
        requirements = requirements_from_components[prototype_id]

        if requirements.is_constraint_check_required and not requirements.constraint.is_met_for(
            mapped_hosts=len(topology.services[service_id].components[component_id].hosts),
            hosts_in_cluster=hosts_amount,
        ):
            return True

        # only mapped components should be checked for requires and bound_to
        if not topology.services[service_id].components[component_id].hosts:
            continue

        if requirements.is_requires_check_required:
            # all required components should be added
            if not existing_objects.issuperset(requirements.requires):
                return True

            for required_component in requirements.requires:
                required_component_id = existing_objects_map[required_component]
                required_service_id = existing_objects_map[
                    ServiceExternalRequirement(name=required_component.service_name)
                ]
                # if required component is unmapped - that's mapping issue
                if not topology.services[required_service_id].components[required_component_id].hosts:
                    return True

        if requirements.is_bound_to_check_required:
            bound_component_id = existing_objects_map.get(requirements.bound_to)
            if not bound_component_id:
                return True

            service_id_of_bound_component = existing_objects_map.get(
                ServiceExternalRequirement(name=requirements.bound_to.service_name)
            )
            if not service_id_of_bound_component:
                return True

            bound_service_topology: ServiceTopology | None = topology.services.get(service_id_of_bound_component)
            if not bound_service_topology:
                return True

            bound_component_hosts: set[HostID] = set(bound_service_topology.components[bound_component_id].hosts)
            current_component_hosts: set[HostID] = set(topology.services[service_id].components[component_id].hosts)

            if bound_component_hosts != current_component_hosts:
                return True

    return False


# constraint check functions


def check_equal_or_less(mapped_hosts: int, _: int, argument: int):
    return mapped_hosts <= argument


def check_equal_or_greater(mapped_hosts: int, _: int, argument: int):
    return mapped_hosts >= argument


def check_exact(mapped_hosts: int, _: int, argument: int):
    return mapped_hosts == argument


def check_is_odd(mapped_hosts: int, _: int):
    return mapped_hosts % 2 == 1


def check_on_all(mapped_hosts: int, hosts_in_cluster: int):
    return mapped_hosts > 0 and mapped_hosts == hosts_in_cluster
