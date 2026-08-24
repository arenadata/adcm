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

from adcm.permissions import VIEW_CLUSTER_PERM, get_object_for_user
from cm.models import Cluster
from cm.transition.status import StatusScenarios
from core.metrics import RetrieveClusterMetrics
from dishka import FromDishka
from drf_spectacular.utils import extend_schema, extend_schema_view
from guardian.shortcuts import get_objects_for_user
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from api_v2.metrics.serializers import ClusterMetricsSerializer
from api_v2.utils.di import inject
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    list=extend_schema(exclude=True),
    retrieve=extend_schema(exclude=True),
)
class ClusterMetricsViewSet(ADCMGenericViewSet):
    queryset = Cluster.objects.none()
    permission_classes = [IsAuthenticated]
    serializer_class = ClusterMetricsSerializer
    lookup_url_kwarg = "cluster_id"

    @inject
    def list(
        self,
        request: Request,
        *_,
        retrieve_cluster_metrics: FromDishka[RetrieveClusterMetrics],
        status_scenarios: FromDishka[StatusScenarios],
        **__,
    ) -> Response:
        cluster_ids_queryset = (
            get_objects_for_user(user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster)
            .order_by("id")
            .values_list("id", flat=True)
        )
        cluster_ids = self.paginate_queryset(cluster_ids_queryset)
        status_map = status_scenarios.retrieve_status_map()
        metrics = retrieve_cluster_metrics.retrieve_metrics_many(cluster_ids=cluster_ids, status_map=status_map)

        serializer_data = self.get_serializer(metrics, many=True).data
        return self.get_paginated_response(data=serializer_data)

    @inject
    def retrieve(
        self,
        request: Request,
        *_,
        retrieve_cluster_metrics: FromDishka[RetrieveClusterMetrics],
        status_scenarios: FromDishka[StatusScenarios],
        **kwargs,
    ) -> Response:
        cluster = get_object_for_user(
            user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=kwargs["cluster_id"]
        )
        status_map = status_scenarios.retrieve_status_map()
        metrics = retrieve_cluster_metrics.retrieve_metrics(cluster_id=cluster.id, status_map=status_map)
        serializer = self.get_serializer(metrics)

        return Response(serializer.data)
