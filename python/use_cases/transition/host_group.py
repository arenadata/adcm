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

"""Configuration and action host groups, managed as a batch and safe to re-run.

ADCM's own group APIs are built for one HTTP request changing one thing: they raise when a host
is added twice or removed while absent, they re-save a configuration group (which resets its
customised values) to change its description, and the action-group service refuses to touch a
group whose owner is locked - which is always true from inside the task that holds the lock.
None of that survives a bundle re-running the same action, so the operations here work on the
difference between the wanted and the current state, address the models directly, and cost a
fixed number of queries no matter how many hosts a group holds.
"""

from collections import defaultdict
from collections.abc import Collection, Iterable
from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from cm.converters import orm_object_to_core_descriptor
from cm.errors import AdcmEx
from cm.models import ActionHostGroup, Cluster, Component, ConfigHostGroup, Host, ObjectConfig, Provider, Service
from core.config import ConfigService, ObjectWithoutConfigError
from core.types import ADCMHostGroupType, Descriptor, HostID, HostName
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

HostGroupOwner: TypeAlias = Cluster | Service | Component | Provider
HostGroupKind: TypeAlias = Literal["config_host_group", "action_host_group"]

GROUP_MODEL = {"config_host_group": ConfigHostGroup, "action_host_group": ActionHostGroup}

# `ActionHostGroup.name` is the shorter of the two columns, and a bundle that names a group
# from its action configuration can exceed it without ever seeing the constraint.
NAME_MAX_LENGTH = {"config_host_group": 1000, "action_host_group": 150}
DESCRIPTION_MAX_LENGTH = {"action_host_group": 255}


@dataclass(slots=True, frozen=True)
class GroupAddress:
    """What identifies a group: `unique_together` on both models is (owner, name)."""

    kind: HostGroupKind
    owner: HostGroupOwner
    name: str

    def __str__(self) -> str:
        return f'{self.kind} "{self.name}" of {self.owner}'


@dataclass(slots=True)
class GroupOutcome:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    hosts_added: int = 0
    hosts_removed: int = 0

    @property
    def with_updates(self) -> bool:
        return bool(self.created or self.updated or self.removed or self.hosts_added or self.hosts_removed)


def _content_types(owners: Iterable[HostGroupOwner]) -> dict[type, ContentType]:
    return {type(owner): ContentType.objects.get_for_model(model=owner) for owner in owners}


def retrieve_groups(addresses: Collection[GroupAddress]) -> dict[GroupAddress, ConfigHostGroup | ActionHostGroup]:
    """Look every address up, one query per group kind."""

    found = {}

    by_kind = defaultdict(list)
    for address in addresses:
        by_kind[address.kind].append(address)

    for kind, kind_addresses in by_kind.items():
        content_type_of = _content_types(address.owner for address in kind_addresses)

        query = Q()
        for address in kind_addresses:
            query |= Q(object_id=address.owner.pk, object_type=content_type_of[type(address.owner)], name=address.name)

        by_key = {
            (group.object_type_id, group.object_id, group.name): group
            for group in GROUP_MODEL[kind].objects.filter(query)
        }

        for address in kind_addresses:
            group = by_key.get((content_type_of[type(address.owner)].pk, address.owner.pk, address.name))
            if group is not None:
                found[address] = group

    return found


def group_key(group: ConfigHostGroup | ActionHostGroup) -> tuple[str, int]:
    """Identity of a group across both kinds.

    The two kinds live in separate tables with independent id sequences, so a configuration
    group and an action group routinely share a primary key. Anything that holds both at once
    has to say which table it means.
    """

    return type(group).__name__, group.pk


def retrieve_group_hosts(
    groups: Collection[ConfigHostGroup | ActionHostGroup],
) -> dict[tuple[str, int], set[HostID]]:
    """Membership of the given groups, one query per group kind."""

    membership = defaultdict(set)

    by_model = defaultdict(list)
    for group in groups:
        by_model[type(group)].append(group.pk)

    for model, group_ids in by_model.items():
        owner_field = f"{model.__name__.lower()}_id"
        for group_id, host_id in model.hosts.through.objects.filter(**{f"{owner_field}__in": group_ids}).values_list(
            owner_field, "host_id"
        ):
            membership[(model.__name__, group_id)].add(host_id)

    return membership


def _kind_of(group: ConfigHostGroup | ActionHostGroup) -> HostGroupKind:
    return "config_host_group" if isinstance(group, ConfigHostGroup) else "action_host_group"


def _check_description_fits(kind: HostGroupKind, name: str, description: str) -> None:
    limit = DESCRIPTION_MAX_LENGTH.get(kind)
    if limit is not None and len(description) > limit:
        raise AdcmEx(
            code="INTERNAL_SERVER_ERROR",
            msg=f'Description of {kind} "{name}" is longer than the {limit} characters ' f"an {kind} allows",
        )


def create_group(
    address: GroupAddress, description: str, config_service: ConfigService
) -> ConfigHostGroup | ActionHostGroup:
    if len(address.name) > NAME_MAX_LENGTH[address.kind]:
        raise AdcmEx(
            code="INTERNAL_SERVER_ERROR",
            msg=f"Name of {address} is longer than the {NAME_MAX_LENGTH[address.kind]} characters "
            f"an {address.kind} allows",
        )

    _check_description_fits(kind=address.kind, name=address.name, description=description)

    if address.kind == "config_host_group" and address.owner.config is None:
        raise AdcmEx(code="GROUP_CONFIG_NO_CONFIG_ERROR")

    group = GROUP_MODEL[address.kind].objects.create(
        object_id=address.owner.pk,
        object_type=ContentType.objects.get_for_model(model=address.owner),
        name=address.name,
        description=description,
    )

    # A configuration group's own configuration is seeded from its owner's, as a step of its
    # own - creating the row does not do it, and everything that reads the group's
    # configuration afterwards assumes it is there.
    if isinstance(group, ConfigHostGroup):
        try:
            config_service.create_initial_configuration_of_host_group(
                group=Descriptor(id=group.pk, type=ADCMHostGroupType.CONFIG),
                owner=orm_object_to_core_descriptor(address.owner),
            )
        except ObjectWithoutConfigError as e:
            raise AdcmEx(code="GROUP_CONFIG_NO_CONFIG_ERROR") from e

    return group


def set_description(group: ConfigHostGroup | ActionHostGroup, description: str) -> bool:
    """Set an existing group's description without re-saving the model.

    `ConfigHostGroup.save()` rebuilds the group's configuration from the owner's with every
    parameter marked synchronized, so saving a group to change its description would silently
    discard exactly the per-group values the group exists for.
    """

    if group.description == description:
        return False

    _check_description_fits(kind=_kind_of(group), name=group.name, description=description)

    type(group).objects.filter(id=group.pk).update(description=description)
    group.description = description

    return True


def remove_groups(addresses: Collection[GroupAddress]) -> list[GroupAddress]:
    """Delete each named group that exists; an absent one is success, not an error."""

    existing = retrieve_groups(addresses)
    if not existing:
        return []

    config_ids = [
        group.config_id  # pyright: ignore[reportAttributeAccessIssue]
        for group in existing.values()
        if isinstance(group, ConfigHostGroup) and group.config_id  # pyright: ignore[reportAttributeAccessIssue]
    ]

    for kind, model in GROUP_MODEL.items():
        ids = [group.pk for address, group in existing.items() if address.kind == kind]
        if ids:
            model.objects.filter(id__in=ids).delete()

    # The one-to-one runs group -> config, so deleting the group leaves its configuration and
    # every revision of it behind. An action that creates and drops a group on every attach and
    # detach would accumulate those forever.
    if config_ids:
        ObjectConfig.objects.filter(id__in=config_ids).delete()

    return sorted(existing, key=str)


def _candidate_host_ids(group: ConfigHostGroup) -> set[HostID]:
    """The hosts this configuration group may hold, as ids.

    `ConfigHostGroup.host_candidate()` answers the same question but materialises every
    candidate host; only the ids are needed here.
    """

    owner = group.object

    match owner:
        case Cluster() | Provider():
            candidates = Host.objects.filter(**{f"{type(owner).__name__.lower()}_id": owner.pk})
        case Service():
            candidates = Host.objects.filter(
                cluster_id=owner.cluster_id,  # pyright: ignore[reportAttributeAccessIssue]
                hostcomponent__service_id=owner.pk,
            )
        case Component():
            candidates = Host.objects.filter(
                cluster_id=owner.cluster_id,  # pyright: ignore[reportAttributeAccessIssue]
                hostcomponent__component_id=owner.pk,
            )
        case _:
            raise AdcmEx(code="GROUP_CONFIG_TYPE_ERROR")

    # a host belongs to at most one configuration group of a given owner
    held_elsewhere = set(
        ConfigHostGroup.hosts.through.objects.filter(
            confighostgroup__object_id=owner.pk,
            confighostgroup__object_type=ContentType.objects.get_for_model(model=owner),
        )
        .exclude(confighostgroup_id=group.pk)
        .values_list("host_id", flat=True)
    )

    return set(candidates.values_list("id", flat=True)) - held_elsewhere


def _action_group_candidate_host_ids(group: ActionHostGroup) -> set[HostID]:
    """The hosts an action host group may hold, as ids.

    The same rule the public API applies: the owner's cluster for a cluster group, and the hosts
    mapped to the owner for a service or component group. Unlike a configuration group, a host
    may be in several action groups of one owner.
    """

    owner = group.object

    match owner:
        case Cluster():
            candidates = Host.objects.filter(cluster_id=owner.pk)
        case Service():
            candidates = Host.objects.filter(
                cluster_id=owner.cluster_id,  # pyright: ignore[reportAttributeAccessIssue]
                hostcomponent__service_id=owner.pk,
            )
        case Component():
            candidates = Host.objects.filter(
                cluster_id=owner.cluster_id,  # pyright: ignore[reportAttributeAccessIssue]
                hostcomponent__component_id=owner.pk,
            )
        case _:
            raise AdcmEx(
                code="HOST_GROUP_CONFLICT",
                msg=f"An action host group can't be owned by a {type(owner).__name__.lower()}",
            )

    return set(candidates.values_list("id", flat=True))


def drop_hosts(group: ConfigHostGroup | ActionHostGroup, wanted: set[HostID], held: set[HostID]) -> int:
    """Remove from the group every held host the wanted set does not contain."""

    to_remove = held - wanted
    if not to_remove:
        return 0

    _through(group).objects.filter(**{_owner_field(group): group.pk, "host_id__in": to_remove}).delete()

    return len(to_remove)


def add_hosts(group: ConfigHostGroup | ActionHostGroup, wanted: set[HostID], held: set[HostID]) -> int:
    """Add the wanted hosts the group does not hold yet, leaving the ones it does alone.

    Only the difference is written, so the same call made twice adds nothing the second time -
    where ADCM's own group APIs raise on a host that is already a member.
    """

    to_add = wanted - held
    if not to_add:
        return 0

    if isinstance(group, ConfigHostGroup):
        not_allowed = to_add - _candidate_host_ids(group)
        if not_allowed:
            fqdns = sorted(Host.objects.filter(id__in=not_allowed).values_list("fqdn", flat=True))
            raise AdcmEx(
                code="GROUP_CONFIG_HOST_ERROR",
                msg=f'These hosts can\'t join the "{group.name}" configuration host group: '
                f"{', '.join(fqdns)}. A host must be mapped to the group's owner and can be in "
                "only one of its configuration groups.",
            )
    else:
        # An action host group has no equivalent of `host_candidate`, and the model does not
        # constrain membership at all - a host of any cluster fits in the table. The one rule
        # that has to hold is that a group's hosts belong to the cluster it acts on.
        not_allowed = to_add - _action_group_candidate_host_ids(group)
        if not_allowed:
            fqdns = sorted(Host.objects.filter(id__in=not_allowed).values_list("fqdn", flat=True))
            raise AdcmEx(
                code="HOST_GROUP_CONFLICT",
                msg=f'These hosts can\'t join the "{group.name}" action host group: '
                f"{', '.join(fqdns)}. A host must belong to the group owner's cluster"
                + (", and be mapped to the owner." if not isinstance(group.object, Cluster) else "."),
            )

    through = _through(group)
    through.objects.bulk_create(
        through(**{_owner_field(group): group.pk, "host_id": host_id}) for host_id in sorted(to_add)
    )

    return len(to_add)


def _through(group: ConfigHostGroup | ActionHostGroup):
    return type(group).hosts.through


def _owner_field(group: ConfigHostGroup | ActionHostGroup) -> str:
    return f"{type(group).__name__.lower()}_id"


def resolve_host_names(owner: HostGroupOwner, names: Collection[HostName]) -> dict[HostName, HostID]:
    """Hosts of the group owner by fqdn.

    A group only ever holds hosts of its owner - of its cluster, or of its provider - and an
    fqdn is unique within either, so this is where a name is turned into a host.
    """

    if not names:
        return {}

    if isinstance(owner, Provider):
        candidates = Host.objects.filter(provider_id=owner.pk)
    else:
        cluster_id = owner.pk if isinstance(owner, Cluster) else owner.cluster_id  # pyright: ignore[reportAttributeAccessIssue]
        candidates = Host.objects.filter(cluster_id=cluster_id)

    found = dict(candidates.filter(fqdn__in=set(names)).values_list("fqdn", "id"))

    missing = sorted(set(names) - set(found))
    if missing:
        raise AdcmEx(
            code="HOST_NOT_FOUND",
            msg=f"{owner} has no host named {', '.join(missing)}, so it can't join a host group of it",
        )

    return found
