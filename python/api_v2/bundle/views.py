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

from adcm.permissions import DjangoModelPermissionsAudit
from audit.utils import audit
from cm.bundle import delete_bundle, load_bundle, upload_file
from cm.models import Bundle, ObjectType
from django.db.models import F
from django_filters.rest_framework.backends import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from api_v2.api_schema import ErrorSerializer
from api_v2.bundle.filters import BundleFilter
from api_v2.bundle.serializers import BundleSerializer, UploadBundleSerializer
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    list=extend_schema(
        operation_id="getBundles",
        description="Get a list of ADCM bundles with information on them.",
    ),
    retrieve=extend_schema(
        operation_id="getBundle",
        description="Get detail information about a specific bundle.",
        responses={200: BundleSerializer, 404: ErrorSerializer},
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
    permission_classes = [DjangoModelPermissionsAudit]
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
            201: BundleSerializer,
            400: ErrorSerializer,
            403: ErrorSerializer,
            409: ErrorSerializer,
        },
    )
    @audit
    def create(self, request, *args, **kwargs) -> Response:  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_path = upload_file(file=request.data["file"])
        bundle = load_bundle(bundle_file=str(file_path))

        return Response(
            status=HTTP_201_CREATED, data=BundleSerializer(instance=self.get_queryset().get(id=bundle.pk)).data
        )

    @extend_schema(
        operation_id="deleteBundle",
        description="Delete a specific ADCM bundle.",
        responses={204: None, 403: ErrorSerializer, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    @audit
    def destroy(self, request, *args, **kwargs) -> Response:  # noqa: ARG002
        bundle = self.get_object()
        delete_bundle(bundle=bundle)

        return Response(status=HTTP_204_NO_CONTENT)
