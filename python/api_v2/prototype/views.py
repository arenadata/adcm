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
from api_v2.prototype.filters import PrototypeFilter
from api_v2.prototype.serializers import (
    PrototypeListSerializer,
    PrototypeTypeSerializer,
)
from api_v2.prototype.utils import accept_license
from cm.models import Prototype
from django.db.models import QuerySet
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import ModelViewSet

from adcm.permissions import VIEW_CLUSTER_PERM, DjangoModelPermissionsAudit


class PrototypeViewSet(ModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = Prototype.objects.exclude(type="adcm").select_related("bundle")
    serializer_class = PrototypeListSerializer
    permission_classes = [DjangoModelPermissionsAudit]
    permission_required = [VIEW_CLUSTER_PERM]
    filterset_class = PrototypeFilter
    ordering_fields = ["name", "bundle"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == "versions":
            return PrototypeTypeSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        if self.action == "versions":
            return self.get_distinct_queryset(queryset=Prototype.objects.all())

        return super().get_queryset()

    @action(methods=["get"], detail=False)
    def versions(self, request):  # pylint: disable=unused-argument
        queryset = self.filter_queryset(self.get_queryset())
        return Response(data=self.get_serializer(queryset, many=True).data)

    @action(methods=["post"], detail=True, url_path="license/accept", url_name="accept-license")
    def accept(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        prototype = self.get_object()
        accept_license(prototype=prototype)
        return Response(status=HTTP_200_OK)

    @staticmethod
    def get_distinct_queryset(queryset: QuerySet) -> QuerySet:
        distinct_prototype_pks = set()
        distinct_prototype_display_names = set()
        for prototype in queryset:
            if prototype.display_name in distinct_prototype_display_names:
                continue

            distinct_prototype_display_names.add(prototype.display_name)
            distinct_prototype_pks.add(prototype.pk)

        return queryset.filter(pk__in=distinct_prototype_pks)
