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
from collections import defaultdict

from api_v2.rbac.role.filters import RoleFilter
from api_v2.rbac.role.serializers import RoleCreateUpdateSerializer, RoleSerializer
from api_v2.views import CamelCaseModelViewSet
from audit.utils import audit
from cm.errors import raise_adcm_ex
from cm.models import Cluster, ClusterObject, Host, HostProvider, ProductCategory
from guardian.mixins import PermissionListMixin
from guardian.shortcuts import get_objects_for_user
from rbac.models import ObjectType as RBACObjectType
from rbac.models import Role, RoleTypes
from rbac.services.role import role_create, role_update
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from adcm.permissions import VIEW_ROLE_PERMISSION, CustomModelPermissionsByMethod


class RoleViewSet(PermissionListMixin, CamelCaseModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = Role.objects.prefetch_related("child", "category").order_by("display_name")
    permission_classes = (CustomModelPermissionsByMethod,)
    method_permissions_map = {
        "patch": [(VIEW_ROLE_PERMISSION, NotFound)],
        "delete": [(VIEW_ROLE_PERMISSION, NotFound)],
    }
    permission_required = ["rbac.view_role"]
    filterset_class = RoleFilter

    def get_queryset(self, *args, **kwargs):
        return get_objects_for_user(**self.get_get_objects_for_user_kwargs(Role.objects.all()))

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RoleCreateUpdateSerializer

        return RoleSerializer

    @audit
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = role_create(**serializer.validated_data)

        return Response(data=RoleSerializer(instance=role).data, status=HTTP_201_CREATED)

    @audit
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        if instance.built_in:
            raise_adcm_ex(code="ROLE_UPDATE_ERROR", msg=f"Can't modify role {instance.name} as it is auto created")

        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        role = role_update(role=instance, partial=partial, **serializer.validated_data)

        return Response(data=RoleSerializer(instance=role).data, status=HTTP_200_OK)

    @audit
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.built_in:
            raise_adcm_ex(code="ROLE_DELETE_ERROR", msg="It is forbidden to remove the built-in role.")

        return super().destroy(request, *args, **kwargs)

    @action(methods=["get"], detail=False)
    def categories(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return Response(data=sorted(category.value for category in ProductCategory.objects.all()), status=HTTP_200_OK)

    @action(methods=["get"], detail=True, url_path="object-candidates", url_name="object-candidates")
    def object_candidates(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        role = self.get_object()
        if role.type != RoleTypes.ROLE:
            return Response({"cluster": [], "provider": [], "service": [], "host": []})

        clusters = []
        providers = []
        services = []
        hosts = []

        if RBACObjectType.CLUSTER.value in role.parametrized_by_type:
            for cluster in Cluster.objects.all():
                clusters.append(
                    {
                        "name": cluster.display_name,
                        "id": cluster.id,
                    },
                )

        if RBACObjectType.PROVIDER.value in role.parametrized_by_type:
            for provider in HostProvider.objects.all():
                providers.append(
                    {
                        "name": provider.display_name,
                        "id": provider.id,
                    },
                )

        if RBACObjectType.HOST.value in role.parametrized_by_type:
            for host in Host.objects.all():
                hosts.append(
                    {
                        "name": host.display_name,
                        "id": host.id,
                    },
                )

        if (
            RBACObjectType.SERVICE.value in role.parametrized_by_type
            or RBACObjectType.COMPONENT.value in role.parametrized_by_type
        ):
            _services = defaultdict(list)
            for service in ClusterObject.objects.all():
                _services[service].append(
                    {
                        "name": service.cluster.name,
                        "id": service.id,
                    },
                )
            for service, clusters_info in _services.items():
                services.append(
                    {
                        "name": service.name,
                        "display_name": service.display_name,
                        "clusters": sorted(clusters_info, key=lambda x: x["name"]),
                    },
                )

        return Response(
            {
                "cluster": sorted(clusters, key=lambda x: x["name"]),
                "provider": sorted(providers, key=lambda x: x["name"]),
                "service": sorted(services, key=lambda x: x["name"]),
                "host": sorted(hosts, key=lambda x: x["name"]),
            },
        )
