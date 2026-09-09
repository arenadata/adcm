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

"""Selecting hosts and moving copies of them between clusters.

A `source` is a list of selectors, and the hosts it means are the union of what each selector
matches. Resolution is by kind, not by entry: every `cluster` entry is answered by one query,
every `service` entry by one more, and so on, so a source naming a dozen objects across three
clusters still costs a fixed number of queries - and so does duplicating, mapping, grouping or
deleting the hundred hosts it resolves to.
"""

from collections import defaultdict
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass, field

from cm.errors import AdcmEx
from cm.models import Cluster, Component, Host, HostComponent
from cm.transition.status import StatusScenarios
from core.action import (
    ActionHostGroupSource,
    ClusterHostSource,
    ComponentHostSource,
    ConfigHostGroupSource,
    HcAclRule,
    HostSource,
    ServiceHostSource,
    TaskMappingDelta,
)
from core.cluster import ClusterService
from core.config import ConfigService
from core.types import ClusterID, ComponentID, HostID, HostName, ObjectID
from django.db.models import Q
from django.db.transaction import atomic
from rbac.scenarios import RBACScenarios

from use_cases.transition.host.duplicate import create_duplicates
from use_cases.transition.host_group import GroupAddress, group_key, retrieve_group_hosts, retrieve_groups
from use_cases.transition.object_address import ObjectContext, resolve_object_targets


@dataclass(slots=True, frozen=True)
class SelectionContext:
    """Where a selector that names nothing is resolved."""

    cluster_id: ClusterID
    provider_id: ObjectID | None = None


def resolve_source(source: Sequence[HostSource], context: SelectionContext) -> list[HostID]:
    """The hosts the whole `source` means, deduplicated, in a stable order.

    A selector that legitimately matches nothing - a component nobody is mapped to, a group
    that was never created - contributes nothing. A selector naming an object that does not
    exist is an error: it is a bundle mistake, not an empty set.
    """

    clusters = _resolve_cluster_names(source=source, context=context)

    selected: set[HostID] = set()
    selected |= _hosts_of_clusters(source=source, clusters=clusters)
    selected |= _hosts_of_services(source=source, clusters=clusters)
    selected |= _hosts_of_components(source=source, clusters=clusters)
    selected |= _hosts_by_name(source=source)
    selected |= _hosts_of_groups(source=source, context=context)

    return sorted(selected)


def _resolve_cluster_names(source: Iterable[HostSource], context: SelectionContext) -> dict[str | None, ClusterID]:
    """Map every `cluster_name` a selector uses to its id, in one query.

    `None` is the key of the task's own cluster, which is what a selector without a
    `cluster_name` means.
    """

    names = {
        entry.cluster_name
        for entry in source
        if isinstance(entry, ClusterHostSource | ServiceHostSource | ComponentHostSource)
        and entry.cluster_name is not None
    }

    resolved: dict[str | None, ClusterID] = {None: context.cluster_id}
    if not names:
        return resolved

    found = dict(Cluster.objects.filter(name__in=names).values_list("name", "id"))

    missing = sorted(names - set(found))
    if missing:
        raise AdcmEx(
            code="CLUSTER_NOT_FOUND",
            msg=f"This ADCM does not manage a cluster named {', '.join(missing)}, "
            "so its hosts can't be selected here",
        )

    resolved.update(found)

    return resolved


def _hosts_of_clusters(source: Iterable[HostSource], clusters: dict[str | None, ClusterID]) -> set[HostID]:
    cluster_ids = {clusters[entry.cluster_name] for entry in source if entry.type == "cluster"}
    if not cluster_ids:
        return set()

    return set(Host.objects.filter(cluster_id__in=cluster_ids).values_list("id", flat=True))


def _hosts_of_services(source: Iterable[HostSource], clusters: dict[str | None, ClusterID]) -> set[HostID]:
    wanted = {(clusters[entry.cluster_name], entry.service_name) for entry in source if entry.type == "service"}
    if not wanted:
        return set()

    selected = set()
    for cluster_id, service_name, host_id in HostComponent.objects.filter(
        cluster_id__in={cluster_id for cluster_id, _ in wanted},
        service__prototype__name__in={service_name for _, service_name in wanted},
    ).values_list("cluster_id", "service__prototype__name", "host_id"):
        if (cluster_id, service_name) in wanted:
            selected.add(host_id)

    return selected


def _hosts_of_components(source: Iterable[HostSource], clusters: dict[str | None, ClusterID]) -> set[HostID]:
    wanted = {
        (clusters[entry.cluster_name], entry.service_name, entry.component_name)
        for entry in source
        if entry.type == "component"
    }
    if not wanted:
        return set()

    selected = set()
    for cluster_id, service_name, component_name, host_id in HostComponent.objects.filter(
        cluster_id__in={cluster_id for cluster_id, _, _ in wanted},
        service__prototype__name__in={service_name for _, service_name, _ in wanted},
        component__prototype__name__in={component_name for _, _, component_name in wanted},
    ).values_list("cluster_id", "service__prototype__name", "component__prototype__name", "host_id"):
        if (cluster_id, service_name, component_name) in wanted:
            selected.add(host_id)

    return selected


def _hosts_by_name(source: Iterable[HostSource]) -> set[HostID]:
    """Hosts named by fqdn.

    An fqdn identifies a machine, and ADCM keeps it unique among originals, so a `host`
    selector names the original - which is the host every copy is made from anyway, and the
    reason the selector takes no cluster.
    """

    names = {entry.host_name for entry in source if entry.type == "host"}
    if not names:
        return set()

    found = dict(Host.objects.filter(fqdn__in=names, original__isnull=True).values_list("fqdn", "id"))

    missing = sorted(names - set(found))
    if missing:
        raise AdcmEx(
            code="HOST_NOT_FOUND",
            msg=f"This ADCM does not manage a host named {', '.join(missing)}",
        )

    return set(found.values())


def _hosts_of_groups(source: Iterable[HostSource], context: SelectionContext) -> set[HostID]:
    entries = [entry for entry in source if isinstance(entry, ConfigHostGroupSource | ActionHostGroupSource)]
    if not entries:
        return set()

    owners = resolve_object_targets(
        targets={entry.object for entry in entries},
        context=ObjectContext(cluster_id=context.cluster_id, provider_id=context.provider_id),
        addressed_by="`source`",
    )

    addresses = {GroupAddress(kind=entry.type, owner=owners[entry.object], name=entry.name) for entry in entries}
    groups = retrieve_groups(addresses)
    if not groups:
        return set()

    membership = retrieve_group_hosts(groups.values())

    return {host_id for group in groups.values() for host_id in membership.get(group_key(group), ())}


# ADD DUPLICATES


@dataclass(slots=True)
class AddDuplicatesOutcome:
    created: dict[ClusterID, list[HostName]] = field(default_factory=dict)
    existing: dict[ClusterID, list[HostName]] = field(default_factory=dict)
    # the duplicates the task's own cluster ends up holding, mapping and grouping act on these
    here: list[HostID] = field(default_factory=list)

    @property
    def created_count(self) -> int:
        return sum(len(names) for names in self.created.values())

    @property
    def existing_count(self) -> int:
        return sum(len(names) for names in self.existing.values())


def add_duplicates(
    source_host_ids: Collection[HostID],
    target_cluster_ids: Sequence[ClusterID],
    here: ClusterID,
    config_service: ConfigService,
    rbac_scenarios: RBACScenarios,
    status_scenarios: StatusScenarios,
) -> AddDuplicatesOutcome:
    """Give every target cluster a copy of every selected host that it does not have yet.

    Identity is the original, not the fqdn: a duplicate can be renamed, and what "this cluster
    already has this host" means is that a copy of that original is already here. A host whose
    original is already a member of the target in its own right is left alone too - a cluster
    does not hold a copy of its own host.
    """

    outcome = AddDuplicatesOutcome()

    originals = _originals_of(source_host_ids)
    if not originals:
        return outcome

    original_ids = [original.pk for original in originals]

    held: dict[ClusterID, dict[HostID, HostID]] = defaultdict(dict)
    for cluster_id, original_id, host_id in Host.objects.filter(
        cluster_id__in=target_cluster_ids, original_id__in=original_ids
    ).values_list("cluster_id", "original_id", "id"):
        held[cluster_id][original_id] = host_id

    for original in originals:
        original_cluster_id = original.cluster_id  # pyright: ignore[reportAttributeAccessIssue]
        if original_cluster_id in target_cluster_ids:
            held[original_cluster_id][original.pk] = original.pk

    for cluster_id in target_cluster_ids:
        to_create = [original for original in originals if original.pk not in held[cluster_id]]

        already = sorted(original.fqdn for original in originals if original.pk in held[cluster_id])
        if already:
            outcome.existing[cluster_id] = already

        if to_create:
            created = create_duplicates(
                config_service=config_service,
                originals=to_create,
                cluster_id=cluster_id,
                rbac_scenarios=rbac_scenarios,
                status_scenarios=status_scenarios,
            )
            outcome.created[cluster_id] = sorted(host.fqdn for host in created)

            for original, duplicate in zip(to_create, created, strict=True):
                held[cluster_id][original.pk] = duplicate.pk

    outcome.here = sorted(held[here].values())

    return outcome


def _originals_of(host_ids: Collection[HostID]) -> list[Host]:
    """The original of every selected host, deduplicated.

    A selector may resolve to a duplicate - one is a host like any other and can be mapped and
    grouped - and a copy is always made from the original.
    """

    if not host_ids:
        return []

    original_ids = {
        original_id or host_id
        for host_id, original_id in Host.objects.filter(id__in=host_ids).values_list("id", "original_id")
    }

    return list(Host.objects.filter(id__in=original_ids).order_by("fqdn"))


# REMOVE DUPLICATES


@dataclass(slots=True)
class RemoveDuplicatesOutcome:
    removed: list[HostName] = field(default_factory=list)
    removed_ids: list[HostID] = field(default_factory=list)


def remove_duplicates(
    source_host_ids: Collection[HostID],
    here: ClusterID,
    cluster_service: ClusterService,
    rbac_scenarios: RBACScenarios,
) -> RemoveDuplicatesOutcome:
    """Unmap, detach and delete this cluster's duplicates of the selected hosts.

    Only duplicates of this cluster are ever touched, and a selector may name either side of
    the copy: the originals in the cluster they belong to, or - when that cluster is already
    gone - the duplicates themselves, through a group that holds them. Components still mapped
    on a duplicate are unmapped first, so cleanup also finishes a run that failed before its
    mapping step.
    """

    # imported lazily: `cm.legacy.api` transitively imports the module that runs internal
    # scripts, the same cycle `bundle_switch` breaks the same way
    from cm.legacy.services.concern import delete_concerns_of_removed_objects, delete_issue
    from cm.legacy.services.concern.checks import cluster_mapping_has_issue_orm_version
    from cm.legacy.services.mapping import change_host_component_mapping_no_lock, check_nothing, lock_cluster_mapping
    from cm.legacy.services.status.notify import reset_hc_map, reset_objects_in_mm
    from cm.models import ConcernCause
    from core.types import ADCMCoreType, CoreObjectDescriptor

    outcome = RemoveDuplicatesOutcome()
    if not source_host_ids:
        return outcome

    duplicates = dict(
        Host.objects.filter(cluster_id=here, original__isnull=False)
        .filter(_either_side_of_the_copy(source_host_ids))
        .values_list("id", "fqdn")
    )
    if not duplicates:
        return outcome

    cluster = Cluster.objects.get(id=here)

    with atomic():
        lock_cluster_mapping(cluster_id=here)

        to_unmap = defaultdict(set)
        for component_id, host_id in HostComponent.objects.filter(cluster_id=here, host_id__in=duplicates).values_list(
            "component_id", "host_id"
        ):
            to_unmap[component_id].add(host_id)

        if to_unmap:
            change_host_component_mapping_no_lock(
                cluster_id=here,
                bundle_id=cluster.prototype.bundle_id,
                mapping_delta=TaskMappingDelta(remove=dict(to_unmap)),
                cluster_service=cluster_service,
                checks_func=check_nothing,
            )

        # Concerns a host OWNS hang off a generic foreign key, so no cascade reaches them and
        # deleting the rows would leave them behind; everything else a host holds - group
        # memberships, concern links, its configuration - does cascade. Tasks locking these
        # hosts are not cancelled the way `delete_host` cancels them: the task doing this is
        # one of them.
        delete_concerns_of_removed_objects(objects={ADCMCoreType.HOST: list(duplicates)})
        Host.objects.filter(id__in=duplicates).delete()

        if not cluster_mapping_has_issue_orm_version(cluster):
            delete_issue(
                owner=CoreObjectDescriptor(id=here, type=ADCMCoreType.CLUSTER), cause=ConcernCause.HOSTCOMPONENT
            )

        rbac_scenarios.re_apply_object_policy(apply_object=cluster)

    reset_hc_map()
    reset_objects_in_mm(cluster_service=cluster_service)

    outcome.removed = sorted(duplicates.values())
    outcome.removed_ids = sorted(duplicates)

    return outcome


def _either_side_of_the_copy(host_ids: Collection[HostID]) -> Q:
    return Q(id__in=host_ids) | Q(original_id__in=host_ids)


# MAPPING DELTA


def write_mapping_delta(
    delta: TaskMappingDelta,
    rules: Sequence[HcAclRule],
    host_ids: Collection[HostID],
    cluster_id: ClusterID,
) -> dict[str, int]:
    """Record in the task's mapping delta what the rules say about the given hosts.

    Nothing is committed here - `hc_apply` does that, after the jobs between the two have run
    against an inventory in which these hosts already appear in the `.add` and `.remove` groups
    the delta produces. Only the difference from what is mapped now is recorded, so writing the
    same delta twice adds nothing the second time.
    """

    if not rules or not host_ids:
        return {}

    components = _components_of_rules(rules=rules, cluster_id=cluster_id)

    mapped = defaultdict(set)
    for component_id, host_id in HostComponent.objects.filter(
        cluster_id=cluster_id, component_id__in=components.values(), host_id__in=host_ids
    ).values_list("component_id", "host_id"):
        mapped[component_id].add(host_id)

    written = {}
    for rule in rules:
        component_id = components[(rule.service, rule.component)]
        wanted = set(host_ids)

        if rule.action == "add":
            difference = wanted - mapped[component_id]
            target = delta.add
        else:
            difference = wanted & mapped[component_id]
            target = delta.remove

        if not difference:
            continue

        target.setdefault(component_id, set()).update(difference)
        written[f"{rule.service}.{rule.component}"] = len(difference)

    return written


def _components_of_rules(rules: Iterable[HcAclRule], cluster_id: ClusterID) -> dict[tuple[str, str], ComponentID]:
    wanted = {(rule.service, rule.component) for rule in rules}

    found = {
        (service_name, component_name): component_id
        for component_id, service_name, component_name in Component.objects.filter(
            cluster_id=cluster_id,
            service__prototype__name__in={service for service, _ in wanted},
            prototype__name__in={component for _, component in wanted},
        ).values_list("id", "service__prototype__name", "prototype__name")
    }

    missing = sorted(f"{service}.{component}" for service, component in wanted - set(found))
    if missing:
        raise AdcmEx(
            code="COMPONENT_NOT_FOUND",
            msg=f"`mapping_rules` names {', '.join(missing)}, which this cluster does not have",
        )

    return found


def merge_mapping_delta(into: TaskMappingDelta, addition: TaskMappingDelta) -> None:
    for source, target in ((addition.add, into.add), (addition.remove, into.remove)):
        for component_id, hosts in source.items():
            target.setdefault(component_id, set()).update(hosts)


def forget_hosts_in_delta(delta: TaskMappingDelta, host_ids: Collection[HostID]) -> bool:
    """Drop hosts from the task's mapping delta because they no longer exist.

    The delta is applied again when the task finishes, and a host deleted in the middle of one
    would make that final application fail on a host the cluster no longer has.
    """

    host_ids = set(host_ids)
    changed = False

    for mapping in (delta.add, delta.remove):
        for component_id, hosts in list(mapping.items()):
            remaining = hosts - host_ids
            if remaining != hosts:
                changed = True
                if remaining:
                    mapping[component_id] = remaining
                else:
                    del mapping[component_id]

    return changed


# GROUP MEMBERSHIP


def hosts_of_cluster_named(host_ids: Collection[HostID], cluster_id: ClusterID) -> set[HostID]:
    """Of the given hosts, the ones this cluster actually holds."""

    if not host_ids:
        return set()

    return set(Host.objects.filter(id__in=host_ids, cluster_id=cluster_id).values_list("id", flat=True))


def duplicates_here(host_ids: Collection[HostID], cluster_id: ClusterID) -> set[HostID]:
    """This cluster's duplicates of the given hosts.

    Only duplicates, never the cluster's own hosts: a selector may name the originals in the
    cluster they belong to or the duplicates themselves, and either way what comes back is the
    copies held here - the same set `remove_duplicates` would delete.
    """

    if not host_ids:
        return set()

    return set(
        Host.objects.filter(cluster_id=cluster_id, original__isnull=False)
        .filter(_either_side_of_the_copy(host_ids))
        .values_list("id", flat=True)
    )


__all__ = [
    "AddDuplicatesOutcome",
    "RemoveDuplicatesOutcome",
    "SelectionContext",
    "add_duplicates",
    "duplicates_here",
    "forget_hosts_in_delta",
    "merge_mapping_delta",
    "hosts_of_cluster_named",
    "remove_duplicates",
    "resolve_source",
    "write_mapping_delta",
]
