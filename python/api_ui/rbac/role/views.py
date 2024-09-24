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

from adcm.permissions import DjangoObjectPermissionsAudit
from adcm.serializers import EmptySerializer
from api.base_view import GenericUIViewSet
from cm.models import Cluster, Host, HostProvider, ObjectType, Service
from rbac.models import ObjectType as RBACObjectType
from rbac.models import Role, RoleTypes
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.serializers import (
    CharField,
    HyperlinkedIdentityField,
    IntegerField,
    JSONField,
)


class RoleUISerializer(EmptySerializer):
    id = IntegerField()
    name = CharField()
    parametrized_by_type = JSONField()
    object_candidate_url = HyperlinkedIdentityField(view_name="rbac-ui:role-object-candidate")


class RoleViewSet(ListModelMixin, GenericUIViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleUISerializer
    permission_classes = (DjangoObjectPermissionsAudit,)

    @action(methods=["get"], detail=True)
    def object_candidate(self, request, **kwargs):  # noqa: ARG002
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
                        "type": ObjectType.CLUSTER,
                        "id": cluster.id,
                    },
                )

        if RBACObjectType.PROVIDER.value in role.parametrized_by_type:
            for provider in HostProvider.objects.all():
                providers.append(
                    {
                        "name": provider.display_name,
                        "type": ObjectType.PROVIDER,
                        "id": provider.id,
                    },
                )

        if RBACObjectType.HOST.value in role.parametrized_by_type:
            for host in Host.objects.all():
                hosts.append(
                    {
                        "name": host.display_name,
                        "type": ObjectType.HOST,
                        "id": host.id,
                    },
                )

        if (
            RBACObjectType.SERVICE.value in role.parametrized_by_type
            or RBACObjectType.COMPONENT.value in role.parametrized_by_type
        ):
            _services = defaultdict(list)
            for service in Service.objects.all():
                _services[service.display_name].append(
                    {
                        "name": service.cluster.display_name,
                        "type": "service",
                        "id": service.id,
                    },
                )
            for service_name, clusters_info in _services.items():
                services.append(
                    {
                        "name": service_name,
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
