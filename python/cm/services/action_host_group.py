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

from core.types import (
    ADCMCoreType,
    ADCMMessageError,
    ClusterID,
    ComponentID,
    CoreObjectDescriptor,
    HostID,
    ServiceID,
    ShortObjectInfo,
    TaskID,
)
from django.contrib.contenttypes.models import ContentType

from cm.converters import core_type_to_model, model_name_to_core_type
from cm.models import ActionHostGroup, Host, HostComponent, TaskLog

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
    description: str = ""


class ActionHostGroupError(ADCMMessageError):
    ...


class NameCollisionError(ActionHostGroupError):
    ...


class GroupIsLockedError(ActionHostGroupError):
    def __init__(self, message: str, task_id: int):
        self.message = message
        self.task_id = task_id

    def __str__(self):
        return self.message


class HostError(ADCMMessageError):
    ...


class ActionHostGroupRepo:
    group_hosts_model = ActionHostGroup.hosts.through

    def create(self, dto: CreateDTO) -> ActionHostGroupID:
        object_type = ContentType.objects.get_for_model(core_type_to_model(dto.owner.type))

        # todo maybe just catch integration error and analyze it?
        if ActionHostGroup.objects.filter(name=dto.name, object_id=dto.owner.id, object_type=object_type).exists():
            message = f'Group with name "{dto.name}" exists for {dto.owner}'
            raise NameCollisionError(message)

        return ActionHostGroup.objects.create(
            name=dto.name,
            description=dto.description,
            object_id=dto.owner.id,
            object_type=object_type,
        ).id

    def retrieve(self, id: ActionHostGroupID) -> ActionTargetHostGroup:  # noqa: A002
        group = ActionHostGroup.objects.get(id=id)
        owner = CoreObjectDescriptor(id=group.object_id, type=model_name_to_core_type(group.object_type.model))

        hosts_qs = group.hosts.values_list("id", flat=True)
        hosts = tuple(
            ShortObjectInfo(*entry) for entry in Host.objects.values_list("id", "fqdn").filter(id__in=hosts_qs)
        )

        return ActionTargetHostGroup(id=group.id, name=group.name, owner=owner, hosts=hosts)

    def delete(self, id: ActionHostGroupID) -> None:  # noqa: A002
        ActionHostGroup.objects.filter(id=id).delete()

    def get_hosts(self, id: ActionHostGroupID) -> set[HostID]:  # noqa: A002
        return set(self.group_hosts_model.objects.values_list("host_id", flat=True).filter(actionhostgroup_id=id))

    def get_all_host_candidates_for_cluster(self, cluster_id: ClusterID) -> set[HostID]:
        return set(Host.objects.values_list("id", flat=True).filter(cluster_id=cluster_id))

    def get_all_host_candidates_for_service(self, service_id: ServiceID) -> set[HostID]:
        return set(HostComponent.objects.values_list("host_id", flat=True).filter(service_id=service_id))

    def get_all_host_candidates_for_component(self, component_id: ComponentID) -> set[HostID]:
        return set(HostComponent.objects.values_list("host_id", flat=True).filter(component_id=component_id))

    def add_hosts(self, id: ActionHostGroupID, hosts: Iterable[HostID]) -> None:  # noqa: A002
        self.group_hosts_model.objects.bulk_create(
            objs=(self.group_hosts_model(actionhostgroup_id=id, host_id=host_id) for host_id in hosts)
        )

    def remove_hosts(self, id: ActionHostGroupID, hosts: Iterable[HostID]) -> None:  # noqa: A002
        self.group_hosts_model.objects.filter(actionhostgroup_id=id, host_id__in=hosts).delete()

    def get_blocking_task_id(self, id: ActionHostGroupID) -> TaskID | None:  # noqa: A002
        object_id, model_name = ActionHostGroup.objects.values_list("object_id", "object_type__model").get(id=id)
        return (
            TaskLog.objects.values_list("id", flat=True)
            .filter(
                owner_id=object_id, owner_type=model_name_to_core_type(model_name=model_name).value, lock__isnull=False
            )
            .first()
        )


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

    def delete(self, group_id: int) -> None:
        if task_id := self._repo.get_blocking_task_id(id=group_id):
            message = f"Can't delete group #{group_id}, because it has running task: {task_id}"
            raise GroupIsLockedError(message=message, task_id=task_id)

        self._repo.delete(id=group_id)

    def get_host_candidates(self, group_id: ActionHostGroupID) -> set[HostID]:
        group = self._repo.retrieve(id=group_id)

        match group.owner.type:
            case ADCMCoreType.CLUSTER:
                all_candidates = self._repo.get_all_host_candidates_for_cluster(cluster_id=group.owner.id)
            case ADCMCoreType.SERVICE:
                all_candidates = self._repo.get_all_host_candidates_for_service(service_id=group.owner.id)
            case ADCMCoreType.COMPONENT:
                all_candidates = self._repo.get_all_host_candidates_for_component(component_id=group.owner.id)
            case _:
                message = f"Can't detect host candidates for owner of type {group.owner.type}"
                raise NotImplementedError(message)

        return all_candidates - {host.id for host in group.hosts}

    def add_hosts_to_group(self, group_id: ActionHostGroupID, hosts: Iterable[HostID]) -> None:
        if task_id := self._repo.get_blocking_task_id(id=group_id):
            message = f"Can't add hosts to group #{group_id}, because it has running task: {task_id}"
            raise GroupIsLockedError(message=message, task_id=task_id)

        hosts_in_group: set[HostID] = self._repo.get_hosts(id=group_id)
        hosts_to_add = set(hosts)

        if incorrect_hosts := hosts_in_group & hosts_to_add:
            message = f"Some hosts are already in action group #{group_id}: {', '.join(map(str, incorrect_hosts))}"
            raise HostError(message)

        candidates = self.get_host_candidates(group_id=group_id)
        if incorrect_hosts := hosts_to_add - candidates:
            message = f"Some hosts can't be added to action group #{group_id}: {', '.join(map(str, incorrect_hosts))}"
            raise HostError(message)

        self._repo.add_hosts(id=group_id, hosts=hosts_to_add)

    def remove_hosts_from_group(self, group_id: ActionHostGroupID, hosts: Iterable[HostID]) -> None:
        if task_id := self._repo.get_blocking_task_id(id=group_id):
            message = f"Can't remove hosts from group #{group_id}, because it has running task: {task_id}"
            raise GroupIsLockedError(message=message, task_id=task_id)

        group = self._repo.retrieve(id=group_id)
        hosts_in_group: set[HostID] = {host.id for host in group.hosts}
        hosts_to_remove = set(hosts)

        if absent_hosts := hosts_to_remove - hosts_in_group:
            message = f"Some hosts can't be removed from action group #{group_id}: {', '.join(map(str, absent_hosts))}"
            raise HostError(message)

        self._repo.remove_hosts(id=group_id, hosts=hosts_to_remove)
