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

import os

from adcm.feature_flags import use_new_bundle_parsing_approach
from audit.alt.api import audit_create, audit_delete
from audit.alt.object_retrievers import ignore_object_search
from cm.bundle import delete_bundle, load_bundle, upload_file
from cm.models import Bundle, ObjectType
from cm.services.adcm import adcm_config, get_adcm_config_id
from cm.services.bundle_alt.load import Directories, parse_bundle_from_request_to_db
from django.conf import settings
from django.db.models import F
from django_filters.rest_framework.backends import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.api_schema import DefaultParams, ErrorSerializer, responses
from api_v2.bundle.filters import BundleFilter
from api_v2.bundle.serializers import BundleSerializer, UploadBundleSerializer
from api_v2.utils.audit import bundle_from_lookup
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    list=extend_schema(
        operation_id="getBundles",
        description="Get a list of ADCM bundles with information on them.",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(
                name="id",
                type=int,
                description="Filter by id.",
            ),
            OpenApiParameter(
                name="display_name",
                description="Case insensitive and partial filter by display name.",
            ),
            OpenApiParameter(
                name="product",
                description="Case insensitive filter by product.",
            ),
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                enum=("displayName", "-displayName", "uploadTime", "-uploadTime"),
                default="displayName",
            ),
        ],
        responses=responses(success=(HTTP_200_OK, BundleSerializer(many=True))),
    ),
    retrieve=extend_schema(
        operation_id="getBundle",
        description="Get detail information about a specific bundle.",
        responses=responses(success=(HTTP_200_OK, BundleSerializer), errors=HTTP_404_NOT_FOUND),
    ),
)
class BundleViewSet(ListModelMixin, RetrieveModelMixin, DestroyModelMixin, CreateModelMixin, ADCMGenericViewSet):
    queryset = (
        Bundle.objects.exclude(name="ADCM")
        .annotate(
            type=F("prototype__type"),
            display_name=F("prototype__display_name"),
            main_prototype_id=F("prototype"),
            main_prototype_name=F("prototype__name"),
            main_prototype_description=F("prototype__description"),
            main_prototype_path=F("prototype__path"),
            main_prototype_license=F("prototype__license"),
            main_prototype_license_path=F("prototype__license_path"),
        )
        .filter(type__in=[ObjectType.CLUSTER, ObjectType.PROVIDER])
        .order_by(F("prototype__display_name").asc())
    )
    permission_classes = [DjangoModelPermissions]
    filterset_class = BundleFilter
    filter_backends = (DjangoFilterBackend,)

    def get_serializer_class(self):
        if self.action == "create":
            return UploadBundleSerializer

        return BundleSerializer

    @extend_schema(
        operation_id="postBundles",
        description="Upload new bundle.",
        request={"multipart/form-data": UploadBundleSerializer},
        responses={
            HTTP_201_CREATED: BundleSerializer,
            HTTP_400_BAD_REQUEST: ErrorSerializer,
            HTTP_403_FORBIDDEN: ErrorSerializer,
            HTTP_409_CONFLICT: ErrorSerializer,
        },
    )
    @audit_create(name="Bundle uploaded", object_=ignore_object_search)
    def create(self, request, *args, **kwargs) -> Response:  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        use_new_approach = use_new_bundle_parsing_approach(env=os.environ, headers=request.headers)
        func = self._new_create if use_new_approach else self._old_create

        bundle = func(request.data["file"])

        return Response(
            status=HTTP_201_CREATED, data=BundleSerializer(instance=self.get_queryset().get(id=bundle.pk)).data
        )

    def _old_create(self, file) -> Bundle:
        file_path = upload_file(file=file)
        return load_bundle(bundle_file=str(file_path))

    def _new_create(self, file) -> Bundle:
        verified_signature_only = adcm_config(get_adcm_config_id()).config["global"]["accept_only_verified_bundles"]
        return parse_bundle_from_request_to_db(
            file_from_request=file,
            directories=Directories(
                downloads=settings.DOWNLOAD_DIR, bundles=settings.BUNDLE_DIR, files=settings.FILE_DIR
            ),
            adcm_version=settings.ADCM_VERSION,
            verified_signature_only=verified_signature_only,
        )

    @extend_schema(
        operation_id="deleteBundle",
        description="Delete a specific ADCM bundle.",
        responses={
            HTTP_204_NO_CONTENT: None,
            HTTP_403_FORBIDDEN: ErrorSerializer,
            HTTP_404_NOT_FOUND: ErrorSerializer,
            HTTP_409_CONFLICT: ErrorSerializer,
        },
    )
    @audit_delete(name="Bundle deleted", object_=bundle_from_lookup, removed_on_success=True)
    def destroy(self, request, *args, **kwargs) -> Response:  # noqa: ARG002
        bundle = self.get_object()
        delete_bundle(bundle=bundle)

        return Response(status=HTTP_204_NO_CONTENT)
