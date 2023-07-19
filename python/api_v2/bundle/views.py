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
from api_v2.bundle.filters import BundleFilter
from api_v2.bundle.serializers import BundleListSerializer, UploadBundleSerializer
from cm.bundle import delete_bundle, load_bundle, upload_file
from cm.models import Bundle
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT
from rest_framework.viewsets import GenericViewSet

from adcm.permissions import VIEW_ACTION_PERM, DjangoModelPermissionsAudit


class BundleViewSet(
    CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, ListModelMixin, GenericViewSet
):  # pylint: disable=too-many-ancestors
    queryset = Bundle.objects.exclude(name="ADCM").prefetch_related("prototype_set")
    serializer_class = BundleListSerializer
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_ACTION_PERM]
    filterset_class = BundleFilter
    ordering_fields = ("id", "name", "display_name", "edition", "version", "upload_time")
    ordering = ["-date"]

    def create(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_path = upload_file(file=request.data["file"])
        bundle = load_bundle(bundle_file=str(file_path))

        return Response(status=HTTP_201_CREATED, data=BundleListSerializer(bundle).data)

    def destroy(self, request, *args, **kwargs) -> Response:
        bundle = self.get_object()
        delete_bundle(bundle=bundle)

        return Response(status=HTTP_204_NO_CONTENT)

    def get_serializer_class(self):
        if self.action == "create":
            return UploadBundleSerializer
        return super().get_serializer_class()
