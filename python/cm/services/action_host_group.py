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
from typing import Iterable, NamedTuple, TypeAlias

from core.types import ADCMCoreType, CoreObjectDescriptor, HostID, ShortObjectInfo
from django.contrib.contenttypes.models import ContentType

from cm.converters import core_type_to_model, model_name_to_core_type
from cm.models import ActionHostGroup, Host

ActionHostGroupID: TypeAlias = int


@dataclass(slots=True)
class ActionTargetHostGroup:
    owner: CoreObjectDescriptor
    id: ActionHostGroupID
    name: str
    hosts: tuple[ShortObjectInfo, ...]


class CreateDTO(NamedTuple):
    owner: CoreObjectDescriptor
    name: str
    description: str


class ActionHostGroupRepo:
    @staticmethod
    def create(dto: CreateDTO) -> ActionHostGroupID:
        return ActionHostGroup.objects.create(
            name=dto.name,
            description=dto.description,
            object_id=dto.owner.id,
            object_type=ContentType.objects.get_for_model(core_type_to_model(dto.owner.type)),
        ).id

    @staticmethod
    def retrieve(id: ActionHostGroupID) -> ActionTargetHostGroup:  # noqa: A002
        group = ActionHostGroup.objects.get(id=id)
        owner = CoreObjectDescriptor(id=group.object_id, type=model_name_to_core_type(group.object_type.model))

        hosts_qs = group.hosts_set.values_list("id", flat=True)
        hosts = tuple(map(ShortObjectInfo, Host.objects.values_list("id", "fqdn").filter(id__in=hosts_qs)))

        return ActionTargetHostGroup(id=group.id, name=group.name, owner=owner, hosts=hosts)

    @staticmethod
    def reset_hosts(id: ActionHostGroupID, hosts: Iterable[HostID]) -> None:  # noqa: A002
        # todo optimize requests
        m2m_model = ActionHostGroup.hosts.through
        m2m_model.objects.filter(actionhostgroup_id=id).delete()
        m2m_model.objects.bulk_create(objs=(m2m_model(actionhostgroup_id=id, host_id=host_id) for host_id in hosts))


class ActionHostGroupService:
    __slots__ = ("_repo",)

    def __init__(self, repository: ActionHostGroupRepo):
        self._repo = repository

    def create(self, dto: CreateDTO) -> ActionHostGroupID:
        if dto.owner.type == ADCMCoreType.HOST:
            message = "Action groups for host owner aren't supported"
            raise TypeError(message)

        return self._repo.create(dto=dto)

    def retrieve(self, group_id: ActionHostGroupID) -> ActionTargetHostGroup:
        return self._repo.retrieve(id=group_id)

    def set_hosts(self, group_id: ActionHostGroupID, hosts: tuple[HostID, ...]) -> None:
        # todo add check that hosts belong to group owner
        self._repo.reset_hosts(id=group_id, hosts=hosts)
