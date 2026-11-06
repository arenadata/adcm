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

"""Resolve the object-addressing vocabulary internal scripts share with `config_apply`.

The ansible plugin layer has its own resolver (`ansible_plugin.base._from_target_description`),
which internal scripts used to reach into. It resolves one object per call, one query each, and
only ever against the job's own cluster. Internal scripts address a list of objects and must not
pay a query per entry, so the resolution lives here instead: a whole batch of descriptions is
turned into ORM objects in a fixed number of queries, and nothing in `cm.legacy.services.job`
has to import the ansible layer to do it.
"""

from collections import defaultdict
from collections.abc import Collection, Iterable
from dataclasses import dataclass

from cm.errors import AdcmEx
from cm.models import Cluster, Component, Provider, Service
from core.action import ComponentObjectTarget, ObjectTarget, ServiceObjectTarget, TypeBasedObjectTarget
from core.types import ClusterID, ObjectID

AddressableObject = Cluster | Service | Component | Provider


@dataclass(slots=True, frozen=True)
class ObjectContext:
    """The objects a task's own position makes addressable without naming them."""

    cluster_id: ClusterID | None = None
    provider_id: ObjectID | None = None


def describe(target: ObjectTarget) -> str:
    match target.type:
        case "service":
            return f'service "{target.service_name}"'
        case "component":
            return f'component "{target.service_name}.{target.component_name}"'
        case _:
            return target.type


def resolve_object_targets(
    targets: Collection[ObjectTarget], context: ObjectContext, addressed_by: str
) -> dict[ObjectTarget, AddressableObject]:
    """Resolve every target against the task's context, in a fixed number of queries.

    One query for the cluster, one for the provider, one for every named service and one for
    every named component - regardless of how many targets name them. A target that resolves
    to nothing is an error naming the target, not a silently skipped entry.
    """

    if not targets:
        return {}

    resolved: dict[ObjectTarget, AddressableObject] = {}

    service_names = {
        target.service_name for target in targets if isinstance(target, ServiceObjectTarget | ComponentObjectTarget)
    }
    component_names = {target.component_name for target in targets if target.type == "component"}

    cluster: Cluster | None = None
    needs_cluster = any(target.type == "cluster" for target in targets) or bool(service_names)
    if needs_cluster:
        if context.cluster_id is None:
            raise AdcmEx(
                code="WRONG_OWNER",
                msg=f"{addressed_by} addresses an object of a cluster, but the task has no cluster",
            )

        cluster = Cluster.objects.filter(id=context.cluster_id).first()
        if cluster is None:
            raise AdcmEx(code="CLUSTER_NOT_FOUND")

    provider: Provider | None = None
    if any(target.type == "provider" for target in targets):
        if context.provider_id is None:
            raise AdcmEx(
                code="WRONG_OWNER",
                msg=f"{addressed_by} addresses a provider, but the task has no provider",
            )

        provider = Provider.objects.filter(id=context.provider_id).first()
        if provider is None:
            raise AdcmEx(code="PROVIDER_NOT_FOUND")

    services: dict[str, Service] = {}
    if service_names:
        services = {
            service.prototype.name: service
            for service in Service.objects.filter(
                cluster_id=context.cluster_id, prototype__name__in=service_names
            ).select_related("prototype")
        }

    components: dict[tuple[str, str], Component] = {}
    if component_names:
        components = {
            (component.service.prototype.name, component.prototype.name): component
            for component in Component.objects.filter(
                cluster_id=context.cluster_id,
                prototype__name__in=component_names,
                service__prototype__name__in=service_names,
            ).select_related("prototype", "service__prototype")
        }

    for target in targets:
        found: AddressableObject | None
        match target:
            case ServiceObjectTarget():
                found = services.get(target.service_name)
            case ComponentObjectTarget():
                found = components.get((target.service_name, target.component_name))
            case TypeBasedObjectTarget():
                # both are already known to exist: their absence is refused above
                found = cluster if target.type == "cluster" else provider

        if found is None:
            raise AdcmEx(
                code="INTERNAL_SERVER_ERROR",
                msg=f"{addressed_by} names {describe(target)}, which this cluster does not have",
            )

        resolved[target] = found

    return resolved


def group_by_owner(
    entries: Iterable[tuple[ObjectTarget, object]], resolved: dict[ObjectTarget, AddressableObject]
) -> dict[AddressableObject, list[object]]:
    grouped = defaultdict(list)
    for target, entry in entries:
        grouped[resolved[target]].append(entry)

    return grouped
