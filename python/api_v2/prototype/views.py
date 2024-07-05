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

from adcm.permissions import VIEW_CLUSTER_PERM, DjangoModelPermissionsAudit
from adcm.serializers import EmptySerializer
from audit.utils import audit
from cm.models import ObjectType, Prototype
from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from api_v2.api_schema import ErrorSerializer
from api_v2.prototype.filters import PrototypeFilter, PrototypeVersionFilter
from api_v2.prototype.serializers import (
    PrototypeSerializer,
    PrototypeVersionsSerializer,
)
from api_v2.prototype.utils import accept_license
from api_v2.views import ADCMReadOnlyModelViewSet


@extend_schema_view(
    list=extend_schema(operation_id="getPrototypes", description="Get a list of all prototypes."),
    retrieve=extend_schema(
        operation_id="getPrototype",
        description="Get detail information about a specific prototype.",
        responses={200: PrototypeSerializer, 404: ErrorSerializer},
    ),
)
class PrototypeViewSet(ADCMReadOnlyModelViewSet):
    queryset = Prototype.objects.exclude(type="adcm").select_related("bundle").order_by("name")
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_CLUSTER_PERM]
    filterset_class = PrototypeFilter

    def get_serializer_class(self):
        if self.action == "versions":
            return PrototypeVersionsSerializer

        if self.action == "accept":
            return EmptySerializer

        return PrototypeSerializer

    @extend_schema(
        operation_id="getPrototypeVersions",
        description="Get a list of ADCM bundles when creating an object (cluster or provider).",
        responses={200: PrototypeVersionsSerializer(many=True)},
    )
    @action(methods=["get"], detail=False, filterset_class=PrototypeVersionFilter)
    def versions(self, request):  # noqa: ARG001, ARG002
        queryset = self.get_filtered_prototypes_unique_by_display_name()
        return Response(data=self.get_serializer(queryset, many=True).data)

    @extend_schema(
        operation_id="postLicense",
        description="Accept prototype license.",
        responses={200: None, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    @audit
    @action(methods=["post"], detail=True, url_path="license/accept", url_name="accept-license")
    def accept(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
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
