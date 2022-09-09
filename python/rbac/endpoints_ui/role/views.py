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

"""Role object candidates view set"""

from collections import defaultdict

from rest_framework import mixins, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from api.base_view import GenericUIViewSet
from cm import models as cm_models
from rbac import models


class RoleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    parametrized_by_type = serializers.JSONField()
    object_candidate_url = serializers.HyperlinkedIdentityField(
        view_name="rbac-ui:role-object-candidate"
    )


class RoleViewSet(mixins.ListModelMixin, GenericUIViewSet):
    queryset = models.Role.objects.all()
    serializer_class = RoleSerializer

    @action(methods=["get"], detail=True)
    def object_candidate(self, request, **kwargs):
        role = self.get_object()
        if role.type != models.RoleTypes.role:
            return Response({"cluster": [], "provider": [], "service": [], "host": []})

        clusters = []
        providers = []
        services = []
        hosts = []

        if models.ObjectType.cluster.value in role.parametrized_by_type:
            for cluster in cm_models.Cluster.objects.all():
                clusters.append(
                    {
                        "name": cluster.display_name,
                        "type": cm_models.ObjectType.Cluster,
                        "id": cluster.id,
                    }
                )

        if models.ObjectType.provider.value in role.parametrized_by_type:
            for provider in cm_models.HostProvider.objects.all():
                providers.append(
                    {
                        "name": provider.display_name,
                        "type": cm_models.ObjectType.Provider,
                        "id": provider.id,
                    }
                )

        if models.ObjectType.host.value in role.parametrized_by_type:
            for host in cm_models.Host.objects.all():
                hosts.append(
                    {
                        "name": host.display_name,
                        "type": cm_models.ObjectType.Host,
                        "id": host.id,
                    }
                )

        if (
            models.ObjectType.service.value in role.parametrized_by_type
            or models.ObjectType.component.value in role.parametrized_by_type
        ):
            _services = defaultdict(list)
            for service in cm_models.ClusterObject.objects.all():
                _services[service.display_name].append(
                    {
                        "name": service.cluster.display_name,
                        "type": "service",
                        "id": service.id,
                    }
                )
            for service_name, clusters_info in _services.items():
                services.append(
                    {
                        "name": service_name,
                        "clusters": sorted(clusters_info, key=lambda x: x["name"]),
                    }
                )

        return Response(
            {
                "cluster": sorted(clusters, key=lambda x: x["name"]),
                "provider": sorted(providers, key=lambda x: x["name"]),
                "service": sorted(services, key=lambda x: x["name"]),
                "host": sorted(hosts, key=lambda x: x["name"]),
            }
        )
