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

from api_v2.group_config.serializers import GroupConfigSerializer
from api_v2.host.serializers import HostGroupConfigSerializer
from cm.models import GroupConfig
from django.contrib.contenttypes.models import ContentType
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED
from rest_framework.viewsets import ModelViewSet

from adcm.mixins import GetParentObjectMixin
from adcm.permissions import VIEW_GROUP_CONFIG_PERM, check_config_perm


class GroupConfigViewSet(PermissionListMixin, ModelViewSet, GetParentObjectMixin):  # pylint: disable=too-many-ancestors
    queryset = GroupConfig.objects.all()
    serializer_class = GroupConfigSerializer
    permission_required = [VIEW_GROUP_CONFIG_PERM]
    ordering = ["id"]

    def get_queryset(self, *args, **kwargs):
        parent_object = self.get_parent_object()
        if parent_object is None:
            raise NotFound

        return (
            super()
            .get_queryset(*args, **kwargs)
            .filter(object_id=parent_object.pk, object_type=ContentType.objects.get_for_model(model=parent_object))
        )

    def create(self, request: Request, *args, **kwargs):
        parent_object = self.get_parent_object()
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
            **serializer.validated_data
        )

        return Response(data=self.get_serializer(group_config).data, status=HTTP_201_CREATED)

    @action(methods=["get", "post"], detail=True)
    def hosts(self, request: Request, *args, **kwargs):  # pylint: disable=unused-argument
        group_config: GroupConfig = self.get_object()

        if request.method == "POST":
            serializer = HostGroupConfigSerializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            hosts = [host_data["id"] for host_data in serializer.validated_data]
            group_config.check_host_candidate([host.pk for host in hosts])
            group_config.hosts.add(*hosts)

            return Response(data=HostGroupConfigSerializer(hosts, many=True).data, status=HTTP_201_CREATED)

        queryset = group_config.hosts.order_by("id")
        serializer = HostGroupConfigSerializer(self.paginate_queryset(queryset=queryset), many=True)

        return self.get_paginated_response(data=serializer.data)

    @action(methods=["get"], detail=True, url_path="host-candidates", url_name="host-candidates")
    def host_candidates(self, request: Request, *args, **kwargs):  # pylint: disable=unused-argument
        group_config: GroupConfig = self.get_object()
        hosts = group_config.host_candidate()
        serializer = HostGroupConfigSerializer(self.paginate_queryset(queryset=hosts), many=True)

        return self.get_paginated_response(data=serializer.data)
