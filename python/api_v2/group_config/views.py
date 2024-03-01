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
from adcm.mixins import GetParentObjectMixin
from adcm.permissions import VIEW_GROUP_CONFIG_PERM, check_config_perm
from audit.utils import audit
from cm.models import GroupConfig
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from guardian.mixins import PermissionListMixin
from rbac.models import re_apply_object_policy
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from api_v2.config.utils import ConfigSchemaMixin
from api_v2.group_config.permissions import GroupConfigPermissions
from api_v2.group_config.serializers import GroupConfigSerializer
from api_v2.host.serializers import HostGroupConfigSerializer
from api_v2.views import CamelCaseModelViewSet


class GroupConfigViewSet(PermissionListMixin, GetParentObjectMixin, ConfigSchemaMixin, CamelCaseModelViewSet):
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

        parent_view_perm = f"cm.view_{parent_object.__class__.__name__.lower()}"
        if parent_object is None or not (
            request.user.has_perm(perm=parent_view_perm, obj=parent_object)
            or request.user.has_perm(perm=parent_view_perm)
        ):
            raise NotFound("Can't find config's parent object")
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

    @action(methods=["get"], detail=True, url_path="host-candidates", url_name="host-candidates")
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
        self.perform_destroy(instance)
        return Response(status=HTTP_204_NO_CONTENT)

    @audit
    def update(self, request: Request, *args, **kwargs):  # noqa: ARG002
        partial = kwargs.pop("partial", False)
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
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)
