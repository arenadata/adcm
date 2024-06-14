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

from audit.utils import audit
from cm.converters import core_type_to_model
from cm.errors import AdcmEx
from cm.models import ActionHostGroup, Cluster, Host
from cm.services.action_host_group import (
    ActionHostGroupRepo,
    ActionHostGroupService,
    CreateDTO,
    GroupIsLockedError,
    HostError,
    NameCollisionError,
)
from core.types import ADCMCoreType, CoreObjectDescriptor, HostGroupDescriptor
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, QuerySet
from django.db.transaction import atomic
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from api_v2.action_host_group.serializers import (
    ActionHostGroupCreateResultSerializer,
    ActionHostGroupCreateSerializer,
    ActionHostGroupSerializer,
    AddHostSerializer,
    ShortHostSerializer,
)
from api_v2.views import CamelCaseGenericViewSet, with_group_object, with_parent_object


class ActionHostGroupViewSet(CamelCaseGenericViewSet):
    queryset = ActionHostGroup.objects.prefetch_related("hosts").order_by("id")
    action_host_group_service = ActionHostGroupService(repository=ActionHostGroupRepo())

    def get_serializer_class(self) -> type[Serializer]:
        if self.action == "create":
            return ActionHostGroupCreateSerializer

        if self.action == "host_candidate":
            return ShortHostSerializer

        return ActionHostGroupSerializer

    @audit
    @with_parent_object
    def create(self, request: Request, *_, parent: CoreObjectDescriptor, **__) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with atomic():
                new_group_id = self.action_host_group_service.create(
                    dto=CreateDTO(owner=parent, **serializer.validated_data)
                )
        except NameCollisionError:
            message = (
                f"Action host group with name {serializer.validated_data['name']} already exists "
                f"for {parent.type.value} {self.get_parent_name(parent=parent)}"
            )
            raise AdcmEx("CREATE_CONFLICT", msg=message) from None

        return Response(
            data=ActionHostGroupCreateResultSerializer(instance=ActionHostGroup.objects.get(id=new_group_id)).data,
            status=HTTP_201_CREATED,
        )

    @with_parent_object
    def list(self, *_, parent: CoreObjectDescriptor, **__) -> Response:
        serializer = self.get_serializer(
            instance=self.paginate_queryset(self.filter_by_parent(qs=self.get_queryset(), parent=parent)), many=True
        )
        return self.get_paginated_response(serializer.data)

    @with_parent_object
    def retrieve(self, *_, parent: CoreObjectDescriptor, pk: str, **__) -> Response:
        try:
            instance = self.filter_by_parent(qs=self.get_queryset(), parent=parent).get(id=int(pk))
        except ActionHostGroup.DoesNotExist:
            raise NotFound() from None

        return Response(data=self.get_serializer(instance=instance).data)

    @with_parent_object
    def destroy(self, *_, parent: CoreObjectDescriptor, pk: str, **__) -> Response:
        if not self.filter_by_parent(qs=ActionHostGroup.objects.filter(id=pk), parent=parent).exists():
            raise NotFound()

        try:
            self.action_host_group_service.delete(group_id=int(pk))
        except GroupIsLockedError as err:
            raise AdcmEx(code="TASK_ERROR", msg=err.message) from None

        return Response(status=HTTP_204_NO_CONTENT)

    @action(methods=["get"], detail=True, url_path="host-candidates", url_name="host-candidates", pagination_class=None)
    @with_parent_object
    def host_candidate(self, *_, parent: CoreObjectDescriptor, pk: str, **__):
        if not self.filter_by_parent(qs=ActionHostGroup.objects.filter(id=pk), parent=parent).exists():
            raise NotFound()

        hosts = self.action_host_group_service.get_host_candidates(group_id=int(pk))
        return Response(data=list(Host.objects.values("id", name=F("fqdn")).filter(id__in=hosts).order_by("fqdn")))

    def filter_by_parent(self, qs: QuerySet, parent: CoreObjectDescriptor) -> QuerySet:
        return qs.filter(
            object_id=parent.id, object_type=ContentType.objects.get_for_model(core_type_to_model(parent.type))
        )

    def get_parent_name(self, parent: CoreObjectDescriptor) -> str:
        if parent.type == ADCMCoreType.CLUSTER:
            return Cluster.objects.values_list("name", flat=True).get(id=parent.id)

        return (
            core_type_to_model(parent.type)
            .objects.values_list("prototype__display_name", flat=True)
            .filter(id=parent.id)
            .get()
        )


class HostActionHostGroupViewSet(CamelCaseGenericViewSet):
    serializer_class = AddHostSerializer
    action_host_group_service = ActionHostGroupService(repository=ActionHostGroupRepo())

    def handle_exception(self, exc: Exception) -> None:
        if isinstance(exc, HostError):
            exc = AdcmEx(code="HOST_GROUP_CONFLICT", msg=exc.message)
        elif isinstance(exc, GroupIsLockedError):
            exc = AdcmEx(code="TASK_ERROR", msg=exc.message)

        return super().handle_exception(exc)

    @audit
    @with_group_object
    def create(self, request: Request, *_, host_group: HostGroupDescriptor, **__) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        host_id = serializer.validated_data["host_id"]

        with atomic():
            self.action_host_group_service.add_hosts_to_group(group_id=host_group.id, hosts=[host_id])

        return Response(
            data=ShortHostSerializer(instance=Host.objects.values("id", name=F("fqdn")).get(id=host_id)).data,
            status=HTTP_201_CREATED,
        )

    @audit
    @with_group_object
    def destroy(self, *_, host_group: HostGroupDescriptor, pk: str, **__) -> Response:
        if not ActionHostGroup.hosts.through.objects.filter(actionhostgroup_id=host_group.id, host_id=pk).exists():
            raise NotFound()

        with atomic():
            self.action_host_group_service.remove_hosts_from_group(group_id=host_group.id, hosts=[int(pk)])

        return Response(status=HTTP_204_NO_CONTENT)
