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

from typing import Collection, Iterable, NamedTuple, TypeAlias

from core.types import ADCMCoreType, CoreObjectDescriptor, HostID, ObjectID, ShortObjectInfo
from django.db.models import F

from cm.converters import core_type_to_model, model_name_to_core_type
from cm.models import ConfigHostGroup
from cm.services.host_group_common import HostGroupRepoMixin

ConfigHostGroupName: TypeAlias = str


class ConfigHostGroupInfo(NamedTuple):
    id: ObjectID
    name: str

    hosts: set[ShortObjectInfo]

    current_config_id: int
    owner: CoreObjectDescriptor


def retrieve_config_host_groups_for_hosts(
    hosts: Iterable[HostID], restrict_by_owner_type: Collection[ADCMCoreType] = ()
) -> dict[ObjectID, ConfigHostGroupInfo]:
    query = ConfigHostGroup.objects.filter(hosts__in=hosts).values(
        "id",
        "name",
        current_config_id=F("config__current"),
        owner_id=F("object_id"),
        owner_model_type=F("object_type__model"),
        host_id=F("hosts__id"),
        host_name=F("hosts__fqdn"),
    )
    if restrict_by_owner_type:
        query = query.filter(
            object_type__model__in=(
                core_type_to_model(owner_type).__name__.lower() for owner_type in restrict_by_owner_type
            )
        )

    result: dict[ObjectID, ConfigHostGroupInfo] = {}

    for record in query:
        group = result.setdefault(
            record["id"],
            ConfigHostGroupInfo(
                id=record["id"],
                name=record["name"],
                current_config_id=record["current_config_id"],
                owner=CoreObjectDescriptor(
                    id=record["owner_id"], type=model_name_to_core_type(record["owner_model_type"])
                ),
                hosts=set(),
            ),
        )
        group.hosts.add(ShortObjectInfo(id=record["host_id"], name=record["host_name"]))

    return result


class ConfigHostGroupRepo(HostGroupRepoMixin):
    group_hosts_model = ConfigHostGroup.hosts.through
    group_hosts_field_name = "confighostgroup"
