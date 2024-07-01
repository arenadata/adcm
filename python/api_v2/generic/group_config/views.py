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

from adcm.mixins import GetParentObjectMixin, ParentObject
from adcm.permissions import VIEW_GROUP_CONFIG_PERM, VIEW_HOST_PERM, check_config_perm
from cm.errors import AdcmEx
from cm.models import GroupConfig, Host
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import PermissionListMixin
from rbac.models import re_apply_object_policy
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
)

from api_v2.generic.config.utils import ConfigSchemaMixin
from api_v2.generic.group_config.permissions import GroupConfigHostsPermissions, GroupConfigPermissions
from api_v2.generic.group_config.serializers import GroupConfigSerializer, HostGroupConfigSerializer
from api_v2.host.filters import HostMemberFilter
from api_v2.host.serializers import HostAddSerializer
from api_v2.views import ADCMGenericViewSet


class GroupConfigViewSet(
    PermissionListMixin,
    GetParentObjectMixin,
    ConfigSchemaMixin,
    RetrieveModelMixin,
    ListModelMixin,
    ADCMGenericViewSet,
):
    queryset = GroupConfig.objects.order_by("name")
    serializer_class = GroupConfigSerializer
    permission_classes = [GroupConfigPermissions]
    permission_required = [VIEW_GROUP_CONFIG_PERM]
    filter_backends = []

    def get_queryset(self, *args, **kwargs):
        parent_object = self.get_parent_object()

        if parent_object is None:
            return GroupConfig.objects.none()

        return (
            super()
            .get_queryset(*args, **kwargs)
            .filter(object_id=parent_object.pk, object_type=ContentType.objects.get_for_model(model=parent_object))
        )

    def create(self, request: Request, *_, **__):
        parent_object = self.get_parent_object()

        self._check_parent_permissions(parent_object=parent_object)

        if parent_object.config is None:
            raise AdcmEx(code="GROUP_CONFIG_NO_CONFIG_ERROR")

        check_config_perm(
            user=request.user,
            action_type="change",
            model=ContentType.objects.get_for_model(model=parent_object).model,
            obj=parent_object,
        )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_config = GroupConfig.objects.create(
            object_type=ContentType.objects.get_for_model(model=parent_object),
            object_id=parent_object.pk,
            **serializer.validated_data,
        )

        re_apply_object_policy(apply_object=parent_object)

        return Response(data=self.get_serializer(group_config).data, status=HTTP_201_CREATED)

    @action(methods=["get"], detail=True, url_path="host-candidates", url_name="host-candidates", pagination_class=None)
    def host_candidates(self, request: Request, *args, **kwargs):  # noqa: ARG001, ARG002
        group_config: GroupConfig = self.get_object()
        hosts = group_config.host_candidate()
        serializer = HostGroupConfigSerializer(instance=hosts, many=True)

        return Response(data=serializer.data, status=HTTP_200_OK)

    def destroy(self, request: Request, *args, **kwargs):  # noqa: ARG002
        parent_object = self.get_parent_object()
        instance = get_object_or_404(
            self.filter_queryset(self.get_queryset()), **{self.lookup_field: self.kwargs[self.lookup_field]}
        )

        check_config_perm(
            user=request.user,
            action_type="change",
            model=ContentType.objects.get_for_model(model=parent_object).model,
            obj=parent_object,
        )
        instance.delete()
        return Response(status=HTTP_204_NO_CONTENT)

    def partial_update(self, request: Request, *_, **__):
        parent_object = self.get_parent_object()
        instance = get_object_or_404(
            self.filter_queryset(self.get_queryset()), **{self.lookup_field: self.kwargs[self.lookup_field]}
        )

        check_config_perm(
            user=request.user,
            action_type="change",
            model=ContentType.objects.get_for_model(model=parent_object).model,
            obj=parent_object,
        )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs) -> Response:
        self._check_parent_permissions()
        return super().retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs) -> Response:
        self._check_parent_permissions()
        return super().list(request, *args, **kwargs)

    def _check_parent_permissions(self, parent_object: ParentObject = None):
        parent_obj = parent_object or self.get_parent_object()
        parent_view_perm = f"cm.view_{parent_obj.__class__.__name__.lower()}"

        if parent_obj is None:
            raise NotFound()

        if not (
            self.request.user.has_perm(parent_view_perm, parent_obj) or self.request.user.has_perm(parent_view_perm)
        ):
            raise NotFound()

        parent_config_view_perm = "cm.view_objectconfig"
        if not (
            self.request.user.has_perm(parent_config_view_perm, parent_obj.config)
            or self.request.user.has_perm(parent_config_view_perm)
        ):
            raise PermissionDenied()


class HostGroupConfigViewSet(
    PermissionListMixin, GetParentObjectMixin, ListModelMixin, RetrieveModelMixin, ADCMGenericViewSet
):
    queryset = (
        Host.objects.select_related("provider", "cluster")
        .prefetch_related("concerns", "hostcomponent_set")
        .order_by("fqdn")
    )
    permission_classes = [GroupConfigHostsPermissions]
    permission_required = [VIEW_HOST_PERM]
    filterset_class = HostMemberFilter
    filter_backends = (DjangoFilterBackend,)
    pagination_class = None

    def get_serializer_class(self) -> type[HostGroupConfigSerializer | HostAddSerializer]:
        if self.action == "create":
            return HostAddSerializer

        return HostGroupConfigSerializer

    def get_queryset(self, *args, **kwargs):  # noqa: ARG002
        return self.queryset.filter(group_config__id=self.kwargs["group_config_pk"])

    def get_group_for_change(self) -> GroupConfig:
        config_group = super().get_parent_object()
        if config_group is None or not isinstance(config_group, GroupConfig):
            raise NotFound

        parent_view_perm = f"cm.view_{config_group.object.__class__.__name__.lower()}"
        if not (
            self.request.user.has_perm(perm=parent_view_perm, obj=config_group.object)
            or self.request.user.has_perm(perm=parent_view_perm)
        ):
            raise NotFound

        check_config_perm(
            user=self.request.user,
            action_type="change",
            model=config_group.object.content_type.model,
            obj=config_group.object,
        )

        return config_group

    def create(self, request, *_, **__):
        group_config = self.get_group_for_change()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        host_id = serializer.validated_data["host_id"]
        group_config.check_host_candidate(host_ids=[host_id])
        host = Host.objects.get(pk=host_id)
        group_config.hosts.add(host)

        return Response(status=HTTP_201_CREATED, data=HostGroupConfigSerializer(instance=host).data)

    def destroy(self, request, *_, **kwargs):  # noqa: ARG002
        group_config = self.get_group_for_change()

        host = group_config.hosts.filter(pk=kwargs["pk"]).first()
        if not host:
            raise NotFound

        group_config.hosts.remove(host)
        return Response(status=HTTP_204_NO_CONTENT)
