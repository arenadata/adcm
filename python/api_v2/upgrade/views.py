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

from api_v2.upgrade.serializers import (
    UpgradeListSerializer,
    UpgradeRetrieveSerializer,
    UpgradeRunSerializer,
)
from cm.issue import update_hierarchy_issues
from cm.models import Cluster, Upgrade
from cm.upgrade import do_upgrade, get_upgrade
from guardian.shortcuts import get_objects_for_user
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND
from rest_framework.viewsets import GenericViewSet

from adcm.permissions import VIEW_CLUSTER_PERM, DjangoModelPermissionsAudit


class UpgradeViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    queryset = Upgrade.objects.all()
    serializer_class = UpgradeListSerializer
    permission_classes = [DjangoModelPermissionsAudit]

    def get_serializer_class(
        self,
    ) -> type[UpgradeListSerializer] | type[UpgradeRunSerializer] | type[UpgradeRetrieveSerializer]:
        if self.action == "retrieve":
            return UpgradeRetrieveSerializer

        if self.action == "run":
            return UpgradeRunSerializer

        return self.serializer_class

    @staticmethod
    def _has_perm(request: Request, kwargs: dict) -> Cluster | None:
        cluster_queryset = get_objects_for_user(user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster)
        cluster = cluster_queryset.get(pk=kwargs["cluster_pk"])

        if not request.user.has_perm(perm="cm.view_upgrade_of_cluster", obj=cluster):
            return None

        return cluster

    def list(self, request: Request, *args, **kwargs):
        cluster = self._has_perm(request=request, kwargs=kwargs)
        if not cluster:
            return Response(
                data=f'Current user has no permission to upgrade cluster with pk "{kwargs["cluster_pk"]}"',
                status=HTTP_403_FORBIDDEN,
            )

        update_hierarchy_issues(obj=cluster)
        upgrade_list = get_upgrade(obj=cluster)
        serializer = self.serializer_class(instance=upgrade_list, many=True)

        return Response(data=serializer.data)

    @action(methods=["post"], detail=True)
    def run(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        cluster = self._has_perm(request=request, kwargs=kwargs)
        if not cluster:
            return Response(
                data=f'Current user has no permission to upgrade cluster with pk "{kwargs["cluster_pk"]}"',
                status=HTTP_403_FORBIDDEN,
            )

        upgrade = Upgrade.objects.filter(pk=kwargs["pk"]).first()
        if not upgrade:
            return Response(data=f'Upgrade with pk "{kwargs["pk"]}" not found', status=HTTP_404_NOT_FOUND)

        do_upgrade(
            obj=cluster,
            upgrade=upgrade,
            config=serializer.validated_data.get("config", {}),
            attr=serializer.validated_data.get("attr", {}),
            hostcomponent=serializer.validated_data.get("host_component_map", []),
        )

        return Response()
