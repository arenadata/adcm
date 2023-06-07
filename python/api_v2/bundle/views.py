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
from api_v2.bundle.utils import upload_file
from cm.bundle import delete_bundle, load_bundle
from cm.errors import AdcmEx
from cm.models import Bundle
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
from rest_framework.viewsets import ModelViewSet

from adcm.permissions import VIEW_ACTION_PERM, DjangoModelPermissionsAudit


class BundleViewSet(ModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = Bundle.objects.all()
    serializer_class = BundleListSerializer
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_ACTION_PERM]
    filterset_class = BundleFilter
    ordering_fields = ("id", "name", "display_name", "edition", "version", "upload_time")
    ordering = ["-date"]

    def create(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer_class()(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_409_CONFLICT)
        try:
            file = upload_file(request)
            bundle = load_bundle(file)
            bundle.save()
        except Exception:  # pylint: disable=broad-except
            return Response(status=HTTP_409_CONFLICT)
        return Response(status=HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs) -> Response:
        bundle = self.get_object()
        try:
            delete_bundle(bundle)
        except AdcmEx:
            return Response(status=HTTP_400_BAD_REQUEST)
        except FileNotFoundError:
            return Response(status=HTTP_404_NOT_FOUND)
        return Response(status=HTTP_204_NO_CONTENT)

    def get_serializer_class(self):
        if self.action == "create":
            return UploadBundleSerializer
        return super().get_serializer_class()
