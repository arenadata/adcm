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

from api_v2.prototype.filters import PrototypeFilter, PrototypeVersionFilter
from api_v2.prototype.serializers import (
    PrototypeListSerializer,
    PrototypeTypeSerializer,
)
from api_v2.prototype.utils import accept_license
from api_v2.views import CamelCaseReadOnlyModelViewSet
from cm.models import ObjectType, Prototype
from django.db.models import QuerySet
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from adcm.permissions import VIEW_CLUSTER_PERM, DjangoModelPermissionsAudit


class PrototypeViewSet(CamelCaseReadOnlyModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = Prototype.objects.exclude(type="adcm").select_related("bundle").order_by("name")
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_CLUSTER_PERM]
    filterset_class = PrototypeFilter

    def get_serializer_class(self):
        if self.action == "versions":
            return PrototypeTypeSerializer

        return PrototypeListSerializer

    @action(methods=["get"], detail=False, filterset_class=PrototypeVersionFilter)
    def versions(self, request):  # pylint: disable=unused-argument
        queryset = self.get_filtered_prototypes_unique_by_display_name()
        return Response(data=self.get_serializer(queryset, many=True).data)

    @action(methods=["post"], detail=True, url_path="license/accept", url_name="accept-license")
    def accept(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        prototype = self.get_object()
        accept_license(prototype=prototype)
        return Response(status=HTTP_200_OK)

    def get_filtered_prototypes_unique_by_display_name(self) -> QuerySet:
        filtered_queryset = self.filter_queryset(
            Prototype.objects.filter(type__in={ObjectType.PROVIDER.value, ObjectType.CLUSTER.value}).all()
        )

        prototype_pks = set()
        processed_pairs = set()
        for pk, type_, display_name in filtered_queryset.values_list("pk", "type", "display_name"):
            if (type_, display_name) in processed_pairs:
                continue

            prototype_pks.add(pk)
            processed_pairs.add((type_, display_name))

        return Prototype.objects.filter(pk__in=prototype_pks)
