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

from adcm.permissions import SuperuserOnlyMixin
from rest_framework.permissions import AllowAny
from rest_framework.routers import APIRootView
from rest_framework.schemas.coreapi import AutoSchema
from rest_framework.viewsets import ReadOnlyModelViewSet

from audit.filters import AuditLogListFilter, AuditSessionListFilter
from audit.models import AuditLog, AuditSession
from audit.serializers import AuditLogSerializer, AuditSessionSerializer


class AuditRoot(APIRootView):
    permission_classes = (AllowAny,)
    api_root_dict = {
        "operations": "auditlog-list",
        "logins": "auditsession-list",
    }


class AuditLogViewSet(SuperuserOnlyMixin, ReadOnlyModelViewSet):
    not_superuser_error_code = "AUDIT_OPERATIONS_FORBIDDEN"
    queryset = AuditLog.objects.select_related("audit_object", "user").order_by("-operation_time", "-pk")
    serializer_class = AuditLogSerializer
    filterset_class = AuditLogListFilter
    schema = AutoSchema()


class AuditSessionViewSet(SuperuserOnlyMixin, ReadOnlyModelViewSet):
    not_superuser_error_code = "AUDIT_LOGINS_FORBIDDEN"
    queryset = AuditSession.objects.select_related("user").order_by("-login_time", "-pk")
    serializer_class = AuditSessionSerializer
    filterset_class = AuditSessionListFilter
    schema = AutoSchema()
