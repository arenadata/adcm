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
from adcm.permissions import VIEW_GROUP_CONFIG_PERM, check_config_perm
from audit.utils import audit
from cm.errors import AdcmEx
from cm.models import Cluster, ClusterObject, GroupConfig, Host, HostProvider, ServiceComponent
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from rbac.models import re_apply_object_policy
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND

from api_v2.api_schema import ErrorSerializer
from api_v2.config.utils import ConfigSchemaMixin
from api_v2.group_config.permissions import GroupConfigPermissions
from api_v2.group_config.serializers import GroupConfigSerializer
from api_v2.host.serializers import HostGroupConfigSerializer, HostShortSerializer
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    list=extend_schema(
        operation_id="getObjectConfigGroups",
        summary="GET object's config groups",
        description="Get information about object's config-groups",
        responses={HTTP_200_OK: GroupConfigSerializer, HTTP_404_NOT_FOUND: ErrorSerializer},
    ),
    retrieve=extend_schema(
        operation_id="getObjectConfigGroup",
        summary="GET object's config group",
        description="Get information about object's config-group",
        responses={HTTP_200_OK: GroupConfigSerializer, HTTP_404_NOT_FOUND: ErrorSerializer},
    ),
    create=extend_schema(
        operation_id="postObjectConfigGroups",
        summary="POST object's config-groups",
        description="Create new object's config-group.",
        responses={HTTP_200_OK: GroupConfigSerializer, HTTP_404_NOT_FOUND: ErrorSerializer},
    ),
    partial_update=extend_schema(
        operation_id="patchObjectConfigGroup",
        summary="PATCH object's config-group",
        description="Change object's config-group's name and description.",
        responses={HTTP_200_OK: GroupConfigSerializer, HTTP_404_NOT_FOUND: ErrorSerializer},
    ),
    destroy=extend_schema(
        operation_id="deleteObjectConfigGroup",
        summary="DELETE object's config-group",
        description="Delete specific object's config-group.",
        responses={HTTP_204_NO_CONTENT: None, HTTP_404_NOT_FOUND: ErrorSerializer},
    ),
    owner_host_candidates=extend_schema(
        operation_id="getObjectConfigGroupHostOwnCandidates",
        summary="GET object's host candidates for new config group",
        description="Get a list of hosts available for adding to object's new config group.",
        responses={HTTP_200_OK: HostShortSerializer(many=True), HTTP_404_NOT_FOUND: ErrorSerializer},
    ),
    host_candidates=extend_schema(
        operation_id="getObjectConfigGroupHostCandidates",
        summary="GET object's config-group host candidates",
        description="Get a list of hosts available for adding to object's config group.",
        responses={HTTP_200_OK: HostGroupConfigSerializer(many=True), HTTP_404_NOT_FOUND: ErrorSerializer},
    ),
)
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
            raise NotFound

        return (
            super()
            .get_queryset(*args, **kwargs)
            .filter(object_id=parent_object.pk, object_type=ContentType.objects.get_for_model(model=parent_object))
        )

    @audit
    def create(self, request: Request, *args, **kwargs):  # noqa: ARG002
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

    @action(
        methods=["get"], detail=False, url_path="host-candidates", url_name="host-candidates", pagination_class=None
    )
    def owner_host_candidates(self, request: Request, *_, **__):  # noqa: ARG002
        parent_object = self.get_parent_object()

        self._check_parent_permissions(parent_object=parent_object)

        # taken from GroupConfig.host_candidate
        if isinstance(parent_object, (Cluster, HostProvider)):
            hosts_qs = parent_object.host_set
        elif isinstance(parent_object, ClusterObject):
            hosts_qs = Host.objects.filter(
                cluster_id=parent_object.cluster_id, hostcomponent__service=parent_object
            ).distinct()
        elif isinstance(parent_object, ServiceComponent):
            hosts_qs = Host.objects.filter(
                cluster_id=parent_object.cluster_id, hostcomponent__component=parent_object
            ).distinct()
        else:
            raise AdcmEx("GROUP_CONFIG_TYPE_ERROR")

        taken_host_id_qs = (
            GroupConfig.hosts.through.objects.values_list("host_id", flat=True)
            .filter(
                groupconfig_id__in=(
                    GroupConfig.objects.values_list("id", flat=True).filter(
                        object_id=parent_object.id,
                        object_type=ContentType.objects.get_for_model(model=parent_object.__class__),
                    )
                )
            )
            .distinct()
        )

        return Response(
            data=HostShortSerializer(
                instance=hosts_qs.values("id", "fqdn").exclude(id__in=taken_host_id_qs), many=True
            ).data,
            status=HTTP_200_OK,
        )

    @action(methods=["get"], detail=True, url_path="host-candidates", url_name="host-candidates", pagination_class=None)
    def host_candidates(self, request: Request, *args, **kwargs):  # noqa: ARG001, ARG002
        group_config: GroupConfig = self.get_object()
        hosts = group_config.host_candidate()
        serializer = HostGroupConfigSerializer(instance=hosts, many=True)

        return Response(data=serializer.data, status=HTTP_200_OK)

    @audit
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

    @audit
    def partial_update(self, request: Request, *args, **kwargs):  # noqa: ARG002
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

    def retrieve(self, request, *args, **kwargs) -> Response:  # noqa: ARG002
        self._check_parent_permissions()
        return super().retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs) -> Response:  # noqa: ARG002
        self._check_parent_permissions()
        return super().list(request, *args, **kwargs)

    def _check_parent_permissions(self, parent_object: ParentObject = None):
        parent_obj = parent_object or self.get_parent_object()
        parent_view_perm = f"cm.view_{parent_obj.__class__.__name__.lower()}"

        if parent_obj is None:
            raise NotFound

        if not (
            self.request.user.has_perm(parent_view_perm, parent_obj) or self.request.user.has_perm(parent_view_perm)
        ):
            raise NotFound

        parent_config_view_perm = "cm.view_objectconfig"
        if not (
            self.request.user.has_perm(parent_config_view_perm, parent_obj.config)
            or self.request.user.has_perm(parent_config_view_perm)
        ):
            raise PermissionDenied
