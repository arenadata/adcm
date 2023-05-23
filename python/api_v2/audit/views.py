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
from api_v2.audit.filters import AuditLogListFilter, AuditSessionListFilter
from api_v2.audit.services import filter_objects_within_time_range
from audit.models import AuditLog, AuditSession, AuditSessionLoginResult
from audit.serializers import AuditLogSerializer, AuditSessionSerializer
from django.db.models import QuerySet
from django.http import HttpResponseRedirect
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.viewsets import ReadOnlyModelViewSet

from adcm.permissions import SuperuserOnlyMixin


# pylint: disable=too-many-ancestors
class AuditSessionViewSet(SuperuserOnlyMixin, ReadOnlyModelViewSet):
    not_superuser_error_code = "AUDIT_LOGINS_FORBIDDEN"
    queryset = AuditSession.objects.select_related("user").order_by("-login_time", "-pk")
    serializer_class = AuditSessionSerializer
    filterset_class = AuditSessionListFilter
    pagination_class = LimitOffsetPagination

    def get_queryset(self, *args, **kwargs) -> QuerySet:
        login_result = self.request.query_params.get("login_result", None)
        if login_result and login_result.casefold() in AuditSessionLoginResult.values:
            self.queryset = self.queryset.filter(login_result=login_result.casefold())
        self.queryset = filter_objects_within_time_range(self.queryset, self.request.query_params)
        return self.queryset

    def list(self, request, *args, **kwargs):
        if not AuditSessionListFilter(data=self.request.query_params, queryset=self.queryset).is_valid():
            return Response(self.request.query_params, status=HTTP_400_BAD_REQUEST)
        login_id = self.request.query_params.get("login", None)
        if self.request.query_params.get("login", None):
            return HttpResponseRedirect(f"{request.path}{login_id}/")
        return super().list(request, *args, **kwargs)


class AuditLogViewSet(ReadOnlyModelViewSet):
    not_superuser_error_code = "AUDIT_OPERATIONS_FORBIDDEN"
    queryset = AuditLog.objects.select_related("audit_object", "user").order_by("-operation_time", "-pk")
    serializer_class = AuditLogSerializer
    filterset_class = AuditLogListFilter
    pagination_class = LimitOffsetPagination

    def get_queryset(self, *args, **kwargs) -> QuerySet:
        return filter_objects_within_time_range(self.queryset, self.request.query_params)

    def list(self, request, *args, **kwargs):
        if not AuditLogListFilter(data=self.request.query_params, queryset=self.queryset).is_valid():
            return Response(self.request.query_params, status=HTTP_400_BAD_REQUEST)
        return super().list(request, *args, **kwargs)
