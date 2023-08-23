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
from api_v2.views import CamelCaseReadOnlyModelViewSet
from cm.bundle import delete_bundle, load_bundle, upload_file
from cm.models import Bundle
from django_filters.rest_framework.backends import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from adcm.permissions import VIEW_ACTION_PERM, DjangoModelPermissionsAudit


class BundleViewSet(CamelCaseReadOnlyModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = Bundle.objects.exclude(name="ADCM").prefetch_related("prototype_set").order_by("name")
    serializer_class = BundleListSerializer
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_ACTION_PERM]
    filterset_class = BundleFilter
    filter_backends = (DjangoFilterBackend,)
    http_method_names = ["get", "post", "delete"]

    def create(self, request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_path = upload_file(file=request.data["file"])
        bundle = load_bundle(bundle_file=str(file_path))

        return Response(status=HTTP_201_CREATED, data=BundleListSerializer(bundle).data)

    def destroy(self, request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        bundle = self.get_object()
        delete_bundle(bundle=bundle)

        return Response(status=HTTP_204_NO_CONTENT)

    def get_serializer_class(self):
        if self.action == "create":
            return UploadBundleSerializer
        return super().get_serializer_class()
