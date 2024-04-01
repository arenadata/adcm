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
from audit.models import AuditLog, AuditSession
from django_filters.rest_framework.backends import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from rest_framework.permissions import DjangoObjectPermissions

from api_v2.api_schema import ErrorSerializer
from api_v2.audit.filters import AuditLogFilterSet, AuditSessionFilterSet
from api_v2.audit.serializers import AuditLogSerializer, AuditSessionSerializer
from api_v2.views import CamelCaseReadOnlyModelViewSet


@extend_schema_view(
    list=extend_schema(
        operation_id="getAuditLogins",
        summary="GET audit logins",
        description="Get information about auditing user authorizations in ADCM.",
    ),
    retrieve=extend_schema(
        operation_id="getAuditLogin",
        summary="GET audit login",
        description="Get information about a specific user authorization in ADCM.",
        responses={200: AuditSessionSerializer, 404: ErrorSerializer},
    ),
)
class AuditSessionViewSet(PermissionListMixin, CamelCaseReadOnlyModelViewSet):
    queryset = AuditSession.objects.select_related("user").order_by("-login_time")
    serializer_class = AuditSessionSerializer
    permission_classes = [DjangoObjectPermissions]
    permission_required = ["audit.view_auditsession"]
    filterset_class = AuditSessionFilterSet
    filter_backends = (DjangoFilterBackend,)


@extend_schema_view(
    list=extend_schema(
        operation_id="getAuditOperations",
        summary="GET audit operations",
        description="Get a list of audited ADCM operations.",
    ),
    retrieve=extend_schema(
        operation_id="getAuditOperation",
        summary="GET audit operation",
        description="Get information about a specific ADCM operation being audited.",
        responses={200: AuditLogSerializer, 404: ErrorSerializer},
    ),
)
class AuditLogViewSet(PermissionListMixin, CamelCaseReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("audit_object", "user").order_by("-operation_time")
    serializer_class = AuditLogSerializer
    permission_classes = [DjangoObjectPermissions]
    permission_required = ["audit.view_auditlog"]
    filterset_class = AuditLogFilterSet
    filter_backends = (DjangoFilterBackend,)
