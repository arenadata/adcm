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

from typing import TypeAlias

from adcm.permissions import VIEW_CLUSTER_PERM
from adcm.serializers import EmptySerializer
from audit.alt.api import audit_update
from cm.models import Bundle, ObjectType, Prototype
from dishka import FromDishka
from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT
from use_cases.bundle import AcceptLicense

from api_v2.api_schema import DefaultParams, responses
from api_v2.prototype.filters import PrototypeFilter, PrototypeVersionFilter
from api_v2.prototype.serializers import (
    PrototypeSerializer,
    PrototypeVersionsSerializer,
)
from api_v2.utils.audit import bundle_from_prototype_lookup
from api_v2.utils.di import inject
from api_v2.views import ADCMReadOnlyModelViewSet, annotate_contract_version_status

PrototypeAttrs: TypeAlias = tuple[str, str]


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
    queryset = Prototype.objects.exclude(type="adcm").order_by("name")
    permission_classes = [DjangoModelPermissions]
    permission_required = [VIEW_CLUSTER_PERM]
    filterset_class = PrototypeFilter

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                Prefetch(
                    "bundle",
                    queryset=Bundle.objects.annotate(
                        **annotate_contract_version_status(
                            contract_version_field="contract_version",
                            request=self.request,
                        )
                    ),
                )
            )
        )

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
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                enum=(
                    "contractVersionStatus",
                    "-contractVersionStatus",
                    "contractVersionValue",
                    "-contractVersionValue",
                ),
            ),
        ],
        responses=responses(success=(HTTP_200_OK, PrototypeVersionsSerializer(many=True))),
    )
    @action(methods=["get"], detail=False, filterset_class=PrototypeVersionFilter, pagination_class=None)
    def versions(self, request):  # noqa: ARG001, ARG002
        filtered_prototypes = self.filter_queryset(self.get_queryset())
        unique_prototypes, versions_by_type_and_name = group_prototypes_for_versions(tuple(filtered_prototypes))

        context = self.get_serializer_context() | {"versions_by_type_and_name": versions_by_type_and_name}

        return Response(data=self.get_serializer(unique_prototypes, many=True, context=context).data)

    @extend_schema(
        operation_id="postLicense",
        description="Accept prototype license.",
        responses=responses(success=(HTTP_200_OK, None), errors=(HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)),
    )
    @audit_update(name="Bundle license accepted", object_=bundle_from_prototype_lookup)
    @action(methods=["post"], detail=True, url_path="license/accept", url_name="accept-license")
    @inject
    def accept(
        self,
        *_,
        accept_license: FromDishka[AcceptLicense],
        **__,
    ) -> Response:
        prototype = self.get_object()
        accept_license.do(prototype=prototype)

        return Response(status=HTTP_200_OK)


def group_prototypes_for_versions(
    prototypes: tuple[Prototype],
) -> tuple[list[Prototype], dict[PrototypeAttrs, list[Prototype]]]:
    """
    Collect unique cluster or provider prototypes and their versions.
    """
    unique_prototypes = []
    processed_pairs = set()
    versions_by_type_and_name = {}

    for prototype in prototypes:
        versions_by_type_and_name.setdefault((prototype.type, prototype.name), []).append(prototype)

        if (prototype.type, prototype.display_name) not in processed_pairs:
            unique_prototypes.append(prototype)
            processed_pairs.add((prototype.type, prototype.display_name))

    for versions in versions_by_type_and_name.values():
        versions.sort(key=lambda prototype: (prototype.version, prototype.bundle.edition), reverse=True)

    return unique_prototypes, versions_by_type_and_name
