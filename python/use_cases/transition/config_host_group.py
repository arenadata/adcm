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

from collections.abc import Collection
from dataclasses import dataclass

from cm.errors import AdcmEx
from cm.models import Cluster, Component, ConfigHostGroup, Provider, Service
from core.config import ObjectWithoutConfigError
from core.types import HostID, HostName
from django.contrib.contenttypes.models import ContentType
from django.db.transaction import atomic
from rbac.scenarios import RBACScenarios

ConfigHostGroupOwner = Cluster | Service | Component | Provider


@dataclass(slots=True)
class EnsureGroupOutcome:
    group_id: int
    created: bool
    added: list[HostName]


def ensure_config_host_group(
    owner: ConfigHostGroupOwner,
    name: str,
    hosts: dict[HostName, HostID],
    rbac_scenarios: RBACScenarios,
    description: str = "",
) -> EnsureGroupOutcome:
    """Ensure a configuration host group of the owner exists and includes the given hosts.

    The group is created when missing (with `description`), and every given host not in the
    group yet is added; hosts already there are left alone and never removed, so the
    operation is safe to re-run. Hosts go through the same candidate check as when the group
    is edited through the public API.
    """

    content_type = ContentType.objects.get_for_model(model=owner)
    group = ConfigHostGroup.objects.filter(object_id=owner.pk, object_type=content_type, name=name).first()

    created = False
    if group is None:
        try:
            with atomic():
                group = ConfigHostGroup.objects.create(
                    object_id=owner.pk, object_type=content_type, name=name, description=description
                )
        except ObjectWithoutConfigError as e:
            raise AdcmEx(code="GROUP_CONFIG_NO_CONFIG_ERROR") from e

        rbac_scenarios.re_apply_object_policy(apply_object=owner)
        created = True

    held = set(group.hosts.values_list("id", flat=True))
    to_add = {fqdn: host_id for fqdn, host_id in hosts.items() if host_id not in held}

    if to_add:
        # raises AdcmEx the same way the public API does on a host that can't join the group
        group.check_host_candidate(host_ids=list(to_add.values()))
        group.hosts.add(*to_add.values())

    return EnsureGroupOutcome(group_id=group.pk, created=created, added=sorted(to_add))


@dataclass(slots=True)
class RemoveGroupOutcome:
    existed: bool
    held: list[HostName]


def remove_config_host_group(owner: ConfigHostGroupOwner, name: str) -> RemoveGroupOutcome:
    """Remove a configuration host group of the owner, reporting the hosts it held."""

    group = ConfigHostGroup.objects.filter(
        object_id=owner.pk, object_type=ContentType.objects.get_for_model(model=owner), name=name
    ).first()

    if group is None:
        return RemoveGroupOutcome(existed=False, held=[])

    held = sorted(group.hosts.values_list("fqdn", flat=True))
    group.delete()

    return RemoveGroupOutcome(existed=True, held=held)


def retrieve_group_host_names(owner: ConfigHostGroupOwner, name: str) -> Collection[HostName]:
    """Fqdns held by the owner's configuration host group, empty when there is no such group."""

    group = ConfigHostGroup.objects.filter(
        object_id=owner.pk, object_type=ContentType.objects.get_for_model(model=owner), name=name
    ).first()

    if group is None:
        return ()

    return tuple(group.hosts.values_list("fqdn", flat=True))
