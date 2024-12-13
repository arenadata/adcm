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

from contextlib import contextmanager
from typing import NamedTuple

from adcm.permissions import (
    EDIT_ACTION_HOST_GROUPS,
    VIEW_ACTION_HOST_GROUPS,
    VIEW_CLUSTER_PERM,
    VIEW_COMPONENT_PERM,
    VIEW_SERVICE_PERM,
)
from audit.alt.api import audit_update, audit_view
from audit.alt.hooks import adjust_denied_on_404_result
from audit.utils import audit
from cm.converters import core_type_to_model
from cm.errors import AdcmEx
from cm.models import Action, ActionHostGroup, ADCMEntity, Cluster, Component, Host, Service
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
from django.db.models import F, Model, QuerySet
from django.db.transaction import atomic
from guardian.shortcuts import get_objects_for_user
from rbac.models import User
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
)

from api_v2.generic.action.audit import audit_action_viewset
from api_v2.generic.action.utils import has_run_perms
from api_v2.generic.action.views import ActionViewSet
from api_v2.generic.action_host_group.audit import (
    host_and_action_host_group_exist,
    nested_action_host_group_exists,
    parent_action_host_group_from_lookup,
    set_group_and_host_names,
    set_group_and_host_names_from_response,
)
from api_v2.generic.action_host_group.filters import ActionHostGroupFilter
from api_v2.generic.action_host_group.serializers import (
    ActionHostGroupCreateResultSerializer,
    ActionHostGroupCreateSerializer,
    ActionHostGroupSerializer,
    AddHostSerializer,
    ShortHostSerializer,
)
from api_v2.host.filters import HostGroupHostFilter
from api_v2.views import ADCMGenericViewSet, with_group_object, with_parent_object

_PARENT_PERMISSION_MAP: dict[ADCMCoreType, tuple[str, type[Model]]] = {
    ADCMCoreType.CLUSTER: (VIEW_CLUSTER_PERM, Cluster),
    ADCMCoreType.SERVICE: (VIEW_SERVICE_PERM, Service),
    ADCMCoreType.COMPONENT: (VIEW_COMPONENT_PERM, Component),
}


class PermissionCheckDTO(NamedTuple):
    require_edit: bool
    no_group_view_err: type[Exception] = NotFound


VIEW_ONLY_PERMISSION_DENIED = PermissionCheckDTO(require_edit=False, no_group_view_err=PermissionDenied)
VIEW_ONLY_NOT_FOUND = PermissionCheckDTO(require_edit=False, no_group_view_err=NotFound)
REQUIRE_EDIT_NOT_FOUND = PermissionCheckDTO(require_edit=True, no_group_view_err=NotFound)
REQUIRE_EDIT_PERMISSION_DENIED = PermissionCheckDTO(require_edit=True, no_group_view_err=PermissionDenied)


def check_has_group_permissions_for_object(
    user: User, parent_object: Cluster | Service | Component, dto: PermissionCheckDTO
) -> None:
    """
    If user hasn't got enough permissions on group, an error will be raised.

    Doesn't check permissions on parent.
    """

    model_name = parent_object.__class__.__name__.lower()
    view_perm_name = f"{VIEW_ACTION_HOST_GROUPS}_{model_name}"

    if not (user.has_perm(view_perm_name, obj=parent_object) or user.has_perm(f"cm.{view_perm_name}")):
        raise dto.no_group_view_err()

    if not dto.require_edit:
        return

    if not user.has_perm(f"{EDIT_ACTION_HOST_GROUPS}_{model_name}", obj=parent_object):
        raise PermissionDenied()


def check_has_group_permissions(user: User, parent: CoreObjectDescriptor, dto: PermissionCheckDTO) -> None:
    """
    Same as `check_has_group_permissions_for_object`, but with checking view permissions on parent
    """

    view_perm, model_class = _PARENT_PERMISSION_MAP[parent.type]

    try:
        parent_object = get_objects_for_user(user=user, perms=view_perm, klass=model_class).get(pk=parent.id)
    except model_class.DoesNotExist:
        raise NotFound() from None

    check_has_group_permissions_for_object(user=user, parent_object=parent_object, dto=dto)


class ActionHostGroupViewSet(ADCMGenericViewSet):
    queryset = ActionHostGroup.objects.prefetch_related("hosts").order_by("id")
    repo = ActionHostGroupRepo()
    action_host_group_service = ActionHostGroupService(repository=repo)
    filterset_class = ActionHostGroupFilter

    def get_serializer_class(self) -> type[Serializer]:
        if self.action == "create":
            return ActionHostGroupCreateSerializer

        if self.action == "host_candidate":
            return ShortHostSerializer

        return ActionHostGroupSerializer

    @audit
    @with_parent_object
    def create(self, request: Request, *_, parent: CoreObjectDescriptor, **__) -> Response:
        check_has_group_permissions(user=request.user, parent=parent, dto=REQUIRE_EDIT_PERMISSION_DENIED)

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
    def list(self, request: Request, parent: CoreObjectDescriptor, **__) -> Response:
        check_has_group_permissions(user=request.user, parent=parent, dto=VIEW_ONLY_PERMISSION_DENIED)

        serializer = self.get_serializer(
            instance=self.paginate_queryset(
                self.filter_queryset(self.filter_by_parent(qs=self.get_queryset(), parent=parent))
            ),
            many=True,
        )
        return self.get_paginated_response(serializer.data)

    @with_parent_object
    def retrieve(self, request: Request, parent: CoreObjectDescriptor, pk: str, **__) -> Response:
        check_has_group_permissions(user=request.user, parent=parent, dto=VIEW_ONLY_NOT_FOUND)

        try:
            instance = self.filter_by_parent(qs=self.get_queryset(), parent=parent).get(id=int(pk))
        except ActionHostGroup.DoesNotExist:
            raise NotFound() from None

        return Response(data=self.get_serializer(instance=instance).data)

    @audit
    @with_parent_object
    def destroy(self, request: Request, parent: CoreObjectDescriptor, pk: str, **__) -> Response:
        check_has_group_permissions(user=request.user, parent=parent, dto=REQUIRE_EDIT_NOT_FOUND)

        if not self.filter_by_parent(qs=ActionHostGroup.objects.filter(id=pk), parent=parent).exists():
            raise NotFound()

        try:
            self.action_host_group_service.delete(group_id=int(pk))
        except GroupIsLockedError as err:
            raise AdcmEx(code="TASK_ERROR", msg=err.message) from None

        return Response(status=HTTP_204_NO_CONTENT)

    @action(
        methods=["get"],
        detail=False,
        url_path="host-candidates",
        url_name="host-candidates",
        pagination_class=None,
        filterset_class=HostGroupHostFilter,
    )
    @with_parent_object
    def owner_host_candidate(self, request: Request, parent: CoreObjectDescriptor, **__):
        check_has_group_permissions(user=request.user, parent=parent, dto=VIEW_ONLY_PERMISSION_DENIED)

        match parent.type:
            case ADCMCoreType.CLUSTER:
                host_ids = self.repo.get_all_host_candidates_for_cluster(cluster_id=parent.id)
            case ADCMCoreType.SERVICE:
                host_ids = self.repo.get_all_host_candidates_for_service(service_id=parent.id)
            case ADCMCoreType.COMPONENT:
                host_ids = self.repo.get_all_host_candidates_for_component(component_id=parent.id)
            case _:
                message = f"Can't get host candidates for {parent.type}"
                raise RuntimeError(message)

        queryset = Host.objects.values("id", name=F("fqdn")).filter(id__in=host_ids).order_by("fqdn")
        queryset = self.filter_queryset(queryset)

        return Response(data=list(queryset))

    @action(
        methods=["get"],
        detail=True,
        url_path="host-candidates",
        url_name="host-candidates",
        pagination_class=None,
        filterset_class=HostGroupHostFilter,
    )
    @with_parent_object
    def host_candidate(self, request: Request, parent: CoreObjectDescriptor, pk: str, **__):
        if not self.filter_by_parent(qs=ActionHostGroup.objects.filter(id=pk), parent=parent).exists():
            raise NotFound()

        check_has_group_permissions(user=request.user, parent=parent, dto=VIEW_ONLY_NOT_FOUND)

        host_ids = self.action_host_group_service.get_host_candidates(group_id=int(pk))

        queryset = Host.objects.values("id", name=F("fqdn")).filter(id__in=host_ids).order_by("fqdn")
        queryset = self.filter_queryset(queryset)

        return Response(data=list(queryset))

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


class ActionHostGroupHostsViewSet(ADCMGenericViewSet):
    queryset = Host.objects.none()  # This is necessary for the BrowsableAPIRenderer to work correctly
    pagination_class = None
    serializer_class = AddHostSerializer
    repo = ActionHostGroupRepo()
    action_host_group_service = ActionHostGroupService(repository=repo)
    filterset_class = HostGroupHostFilter

    def __init_subclass__(cls, **__):
        audit_view(
            create=(
                audit_update(
                    name="Host {host_name} added to action host group {group_name}",
                    object_=parent_action_host_group_from_lookup,
                ).attach_hooks(
                    pre_call=set_group_and_host_names_from_response,
                    on_collect=adjust_denied_on_404_result(objects_exist=nested_action_host_group_exists),
                )
            ),
            destroy=(
                audit_update(
                    name="Host {host_name} removed from action host group {group_name}",
                    object_=parent_action_host_group_from_lookup,
                ).attach_hooks(
                    on_collect=[
                        set_group_and_host_names,
                        adjust_denied_on_404_result(objects_exist=host_and_action_host_group_exist),
                    ]
                )
            ),
        )(cls)

    @contextmanager
    def convert_exception(self) -> None:
        """
        Customization of `handle_exception` leads to "problems" with audit:
        either audit should catch all exception itself
        or "correct" exceptions should be raised inside of function wrapped by audit decorator.

        The latter is the solution for now to avoid more customization for audit
        without rethinking its place and usage.
        """

        try:
            yield
        except HostError as err:
            raise AdcmEx(code="HOST_GROUP_CONFLICT", msg=err.message) from None
        except GroupIsLockedError as err:
            raise AdcmEx(code="TASK_ERROR", msg=err.message) from None

    @with_group_object
    def create(
        self, request: Request, *_, parent: CoreObjectDescriptor, host_group: HostGroupDescriptor, **__
    ) -> Response:
        check_has_group_permissions(user=request.user, parent=parent, dto=REQUIRE_EDIT_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        host_id = serializer.validated_data["host_id"]

        with self.convert_exception(), atomic():
            self.action_host_group_service.add_hosts_to_group(group_id=host_group.id, hosts=[host_id])

        return Response(
            data=ShortHostSerializer(instance=Host.objects.values("id", name=F("fqdn")).get(id=host_id)).data,
            status=HTTP_201_CREATED,
        )

    @with_group_object
    def destroy(
        self, request: Request, parent: CoreObjectDescriptor, host_group: HostGroupDescriptor, pk: str, **__
    ) -> Response:
        check_has_group_permissions(user=request.user, parent=parent, dto=REQUIRE_EDIT_NOT_FOUND)

        if not ActionHostGroup.hosts.through.objects.filter(actionhostgroup_id=host_group.id, host_id=pk).exists():
            raise NotFound()

        with self.convert_exception(), atomic():
            self.action_host_group_service.remove_hosts_from_group(group_id=host_group.id, hosts=[int(pk)])

        return Response(status=HTTP_204_NO_CONTENT)

    @with_group_object
    def list(
        self, request: Request, *_, parent: CoreObjectDescriptor, host_group: HostGroupDescriptor, **__
    ) -> Response:
        check_has_group_permissions(user=request.user, parent=parent, dto=VIEW_ONLY_NOT_FOUND)
        host_ids = self.repo.get_hosts(id=host_group.id)

        queryset = Host.objects.values("id", name=F("fqdn")).filter(id__in=host_ids).order_by("fqdn")
        queryset = self.filter_queryset(queryset)

        return Response(data=list(queryset))

    @with_group_object
    def retrieve(
        self, request: Request, *_, parent: CoreObjectDescriptor, host_group: HostGroupDescriptor, **__
    ) -> Response:
        check_has_group_permissions(user=request.user, parent=parent, dto=VIEW_ONLY_NOT_FOUND)
        host_id = int(self.kwargs["pk"])

        all_hosts = self.repo.get_hosts(id=host_group.id)

        if host_id not in all_hosts:
            raise NotFound()

        return Response(data=ShortHostSerializer(instance=Host.objects.get(id=host_id)).data)


class ActionHostGroupActionsViewSet(ActionViewSet):
    def __init_subclass__(cls, **__):
        audit_action_viewset(retrieve_owner=parent_action_host_group_from_lookup)(cls)

    def get_parent_object(self) -> ActionHostGroup | None:
        if "action_host_group_pk" not in self.kwargs:
            return None

        parent = super().get_parent_object()

        return (
            ActionHostGroup.objects.prefetch_related("object__prototype")
            .filter(
                pk=self.kwargs["action_host_group_pk"],
                object_id=parent.pk,
                object_type=ContentType.objects.get_for_model(model=parent.__class__),
            )
            .first()
        )

    def get_queryset(self, *_, **__) -> QuerySet:
        group_owner = self.parent_object.object
        self.prototype_objects = {group_owner.prototype: group_owner}
        return self.general_queryset.filter(prototype=group_owner.prototype, allow_for_action_host_group=True)

    def check_permissions_for_list(self, request: Request) -> None:
        if not (self.parent_object and self.parent_object.object):
            raise NotFound()

        group_owner = self.parent_object.object
        model_name = group_owner.__class__.__name__.lower()
        if not (
            request.user.has_perm(perm=f"cm.view_{model_name}")
            or request.user.has_perm(perm=f"cm.view_{model_name}", obj=group_owner)
        ):
            raise NotFound()

        check_has_group_permissions_for_object(user=request.user, parent_object=group_owner, dto=VIEW_ONLY_NOT_FOUND)

    def check_permissions_for_run(self, request: Request, action: Action) -> None:
        self.check_permissions_for_list(request=request)

        if not has_run_perms(user=request.user, action=action, obj=self.parent_object.object):
            raise NotFound()

    def _get_actions_owner(self) -> ADCMEntity:
        return self.parent_object.object
