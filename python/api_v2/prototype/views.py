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

from adcm.permissions import VIEW_CLUSTER_PERM
from adcm.serializers import EmptySerializer
from audit.alt.api import audit_update
from cm.models import ObjectType, Prototype
from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from api_v2.api_schema import DefaultParams, responses
from api_v2.prototype.filters import PrototypeFilter, PrototypeVersionFilter
from api_v2.prototype.serializers import (
    PrototypeSerializer,
    PrototypeVersionsSerializer,
)
from api_v2.prototype.utils import accept_license
from api_v2.utils.audit import bundle_from_prototype_lookup
from api_v2.views import ADCMReadOnlyModelViewSet


@extend_schema_view(
    list=extend_schema(
        operation_id="getPrototypes",
        description="Get a list of all prototypes.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                description="Filter by ID.",
            ),
            OpenApiParameter(
                name="bundle_id",
                type=int,
                description="Filter by bundle ID.",
            ),
            OpenApiParameter(
                name="display_name",
                description="Filter by display name.",
            ),
            OpenApiParameter(
                name="type",
                description="Filter by type.",
                enum=(
                    ObjectType.CLUSTER.value,
                    ObjectType.PROVIDER.value,
                    ObjectType.HOST.value,
                    ObjectType.SERVICE.value,
                    ObjectType.COMPONENT.value,
                ),
            ),
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
        ],
    ),
    retrieve=extend_schema(
        operation_id="getPrototype",
        description="Get detail information about a specific prototype.",
        responses=responses(success=(HTTP_200_OK, PrototypeSerializer(many=True)), errors=HTTP_404_NOT_FOUND),
    ),
)
class PrototypeViewSet(ADCMReadOnlyModelViewSet):
    queryset = Prototype.objects.exclude(type="adcm").select_related("bundle").order_by("name")
    permission_classes = [DjangoModelPermissions]
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
        parameters=[
            OpenApiParameter(
                name="type",
                description="Filter by prototype type.",
                enum=(
                    ObjectType.CLUSTER.value,
                    ObjectType.PROVIDER.value,
                ),
            ),
        ],
        responses=responses(success=(HTTP_200_OK, PrototypeVersionsSerializer(many=True))),
    )
    @action(methods=["get"], detail=False, filterset_class=PrototypeVersionFilter, pagination_class=None)
    def versions(self, request):  # noqa: ARG001, ARG002
        queryset = self.get_filtered_prototypes_unique_by_display_name()
        return Response(data=self.get_serializer(queryset, many=True).data)

    @extend_schema(
        operation_id="postLicense",
        description="Accept prototype license.",
        responses=responses(success=(HTTP_200_OK, None), errors=(HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)),
    )
    @audit_update(name="Bundle license accepted", object_=bundle_from_prototype_lookup)
    @action(methods=["post"], detail=True, url_path="license/accept", url_name="accept-license")
    def accept(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        prototype = self.get_object()
        accept_license(prototype=prototype)
        return Response(status=HTTP_200_OK)

    def get_filtered_prototypes_unique_by_display_name(self) -> QuerySet:
        filtered_queryset = Prototype.objects.filter(
            type__in={ObjectType.PROVIDER.value, ObjectType.CLUSTER.value}
        ).all()

        prototype_pks = set()
        processed_pairs = set()
        for pk, type_, display_name in filtered_queryset.values_list("pk", "type", "display_name"):
            if (type_, display_name) in processed_pairs:
                continue

            prototype_pks.add(pk)
            processed_pairs.add((type_, display_name))

        return self.filter_queryset(Prototype.objects.filter(pk__in=prototype_pks))
