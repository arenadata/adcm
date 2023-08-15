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
from typing import Tuple

from api_v2.upgrade.serializers import (
    ClusterUpgradeListSerializer,
    HostProviderUpgradeListSerializer,
    UpgradeRetrieveSerializer,
    UpgradeRunSerializer,
)
from api_v2.views import CamelCaseGenericViewSet
from cm.issue import update_hierarchy_issues
from cm.models import Cluster, HostProvider, Upgrade
from cm.upgrade import do_upgrade, get_upgrade
from guardian.shortcuts import get_objects_for_user
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from adcm.permissions import (
    VIEW_CLUSTER_PERM,
    VIEW_CLUSTER_UPGRADE_PERM,
    VIEW_PROVIDER_PERM,
    VIEW_PROVIDER_UPGRADE_PERM,
    DjangoModelPermissionsAudit,
)


class UpgradeViewSet(ListModelMixin, RetrieveModelMixin, CamelCaseGenericViewSet):  # pylint: disable=too-many-ancestors
    queryset = Upgrade.objects.all().select_related("action").order_by("pk")
    permission_classes = [DjangoModelPermissionsAudit]
    filter_backends = []

    base_for_upgrade = {
        "cluster_pk": {"perms": VIEW_CLUSTER_PERM, "klass": Cluster, "list_serializer": ClusterUpgradeListSerializer},
        "hostprovider_pk": {
            "perms": VIEW_PROVIDER_PERM,
            "klass": HostProvider,
            "list_serializer": HostProviderUpgradeListSerializer,
        },
    }

    def get_serializer_class(
        self,
    ) -> type[ClusterUpgradeListSerializer] | type[UpgradeRunSerializer] | type[UpgradeRetrieveSerializer]:
        if self.action == "retrieve":
            return UpgradeRetrieveSerializer

        if self.action == "run":
            return UpgradeRunSerializer

        return self.base_for_upgrade[list(self.kwargs.keys()).pop()]["list_serializer"]

    def _has_perm(self, request: Request, **kwargs) -> Cluster | HostProvider | None:
        if "hostprovider_pk" in kwargs:
            pk_name, pk_value = "hostprovider_pk", kwargs["hostprovider_pk"]
        else:
            pk_name, pk_value = "cluster_pk", kwargs["cluster_pk"]
        perms, klass, _ = self.base_for_upgrade[pk_name].values()
        object_queryset = get_objects_for_user(user=request.user, perms=perms, klass=klass)
        object_to_upgrade = object_queryset.filter(pk=pk_value).first()
        if not object_to_upgrade:
            raise NotFound
        object_premissions_for_uprgade = {HostProvider: VIEW_PROVIDER_UPGRADE_PERM, Cluster: VIEW_CLUSTER_UPGRADE_PERM}

        if not request.user.has_perm(
            perm=object_premissions_for_uprgade[type(object_to_upgrade)], obj=object_to_upgrade
        ):
            return None

        return object_to_upgrade

    def _get_error_message_403(self, **kwargs):
        if "hostprovider_pk" in kwargs:
            pk_name, pk_value = "host provider", kwargs["hostprovider_pk"]
        else:
            pk_name, pk_value = "cluster", kwargs["cluster_pk"]
        return (
            f"Current user has no permission to upgrade {pk_name} with pk '{pk_value}' "
            f"by upgrade with pk '{kwargs['pk']}'",
        )

    # pylint: disable=unused-argument
    def get_upgrade_list(
        self, request: Request, *args, **kwargs
    ) -> Tuple[HostProvider | Cluster, list[Upgrade]] | None:
        object_to_upgrade = self._has_perm(request=request, **kwargs)
        if not object_to_upgrade:
            return None
        update_hierarchy_issues(obj=object_to_upgrade)
        return object_to_upgrade, get_upgrade(obj=object_to_upgrade)

    def list(self, request: Request, *args, **kwargs) -> Response:
        object_to_upgrade, upgrade_list = self.get_upgrade_list(request, *args, **kwargs)
        if not object_to_upgrade:
            Response(
                data=self._get_error_message_403(**kwargs),
                status=HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance=upgrade_list, many=True)
        return Response(data=serializer.data)

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        object_to_upgrade, upgrade_list = self.get_upgrade_list(request, *args, **kwargs)
        if not object_to_upgrade:
            Response(
                data=self._get_error_message_403(**kwargs),
                status=HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        if instance not in upgrade_list:
            return Response(
                data=f"The upgrade "
                f"{instance.name} with pk '{instance.pk}' "
                f"has not allowable to instance with pk {kwargs['pk']}",
                status=HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(instance)

        return Response(serializer.data)

    @action(methods=["post"], detail=True)
    def run(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        object_to_upgrade = self._has_perm(request, **kwargs)
        if not object_to_upgrade:
            return Response(
                data=self._get_error_message_403(**kwargs),
                status=HTTP_403_FORBIDDEN,
            )

        object_to_upgrade, allowable_upgrades = self.get_upgrade_list(request, *args, **kwargs)
        if not object_to_upgrade:
            Response(
                data=self._get_error_message_403(**kwargs),
                status=HTTP_403_FORBIDDEN,
            )
        if not Upgrade.objects.filter(pk=kwargs["pk"]).first():
            return Response(data=f"Upgrade with pk '{kwargs['pk']}' not found", status=HTTP_404_NOT_FOUND)

        matching_upgrades = [u for u in allowable_upgrades if u.pk == int(kwargs["pk"])]
        if not matching_upgrades:
            return Response(
                data=f"Upgrade with pk '{kwargs['pk']}' is not allowable for '{object_to_upgrade.pk}'",
                status=HTTP_409_CONFLICT,
            )

        do_upgrade(
            obj=object_to_upgrade,
            upgrade=matching_upgrades.pop(),
            config=serializer.validated_data.get("config", {}),
            attr=serializer.validated_data.get("attr", {}),
            hostcomponent=serializer.validated_data.get("host_component_map", []),
        )

        return Response()
