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

from datetime import date

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
    AuditSession,
    AuditSessionLoginResult,
)
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from rest_framework.permissions import DjangoObjectPermissions

from api_v2.api_schema import DefaultParams, ErrorSerializer
from api_v2.audit.filters import AuditLogFilter, AuditSessionFilter
from api_v2.audit.serializers import AuditLogSerializer, AuditSessionSerializer
from api_v2.views import ADCMReadOnlyModelViewSet


@extend_schema_view(
    list=extend_schema(
        operation_id="getAuditLogins",
        summary="GET audit logins",
        description="Get information about auditing user authorizations in ADCM.",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(
                name="id",
                type=int,
                description="Filter by id.",
            ),
            OpenApiParameter(
                name="login",
                description="Case insensitive and partial filter by user login.",
            ),
            OpenApiParameter(
                name="login_result",
                description="Filter by login result.",
                enum=AuditSessionLoginResult.values,
            ),
            OpenApiParameter(
                name="time_from",
                description="Filter by time from.",
                type=date,
            ),
            OpenApiParameter(
                name="time_to",
                description="Filter by time to.",
                type=date,
            ),
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                enum=(
                    "loginTime",
                    "-loginTime",
                    "time",
                    "-time",
                ),
                default="-loginTime",
            ),
        ],
        responses={200: AuditSessionSerializer(many=True), 403: ErrorSerializer},
    ),
    retrieve=extend_schema(
        operation_id="getAuditLogin",
        summary="GET audit login",
        description="Get information about a specific user authorization in ADCM.",
        responses={200: AuditSessionSerializer, 404: ErrorSerializer},
    ),
)
class AuditSessionViewSet(PermissionListMixin, ADCMReadOnlyModelViewSet):
    queryset = AuditSession.objects.select_related("user").order_by("-login_time")
    serializer_class = AuditSessionSerializer
    permission_classes = [DjangoObjectPermissions]
    permission_required = ["audit.view_auditsession"]
    filterset_class = AuditSessionFilter


@extend_schema_view(
    list=extend_schema(
        operation_id="getAuditOperations",
        summary="GET audit operations",
        description="Get a list of audited ADCM operations.",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            OpenApiParameter(
                name="id",
                type=int,
                description="Filter by id.",
            ),
            OpenApiParameter(
                name="object_name",
                description="Case insensitive and partial filter by object name.",
            ),
            OpenApiParameter(
                name="object_type",
                description="Filter by object type.",
                enum=AuditObjectType.values,
            ),
            OpenApiParameter(
                name="operation_result",
                description="Filter by operation result.",
                enum=AuditLogOperationResult.values,
            ),
            OpenApiParameter(
                name="operation_type",
                description="Filter by operation type.",
                enum=AuditLogOperationType.values,
            ),
            OpenApiParameter(
                name="time_from",
                description="Filter by time from.",
                type=date,
            ),
            OpenApiParameter(
                name="time_to",
                description="Filter by time to.",
                type=date,
            ),
            OpenApiParameter(
                name="user_name",
                description="Case insensitive and partial filter by user name.",
            ),
            OpenApiParameter(
                name="username",
                description="Case insensitive and partial filter by user name.",
            ),
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                enum=(
                    "objectName",
                    "-objectName",
                    "objectType",
                    "-objectType",
                    "name",
                    "-name",
                    "type",
                    "-type",
                    "result",
                    "-result",
                    "userName",
                    "-userName",
                    "time",
                    "-time",
                ),
                default="-time",
            ),
        ],
        responses={200: AuditLogSerializer(many=True), 403: ErrorSerializer},
    ),
    retrieve=extend_schema(
        operation_id="getAuditOperation",
        summary="GET audit operation",
        description="Get information about a specific ADCM operation being audited.",
        responses={200: AuditLogSerializer, 404: ErrorSerializer},
    ),
)
class AuditLogViewSet(PermissionListMixin, ADCMReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("audit_object", "user").order_by("-operation_time")
    serializer_class = AuditLogSerializer
    permission_classes = [DjangoObjectPermissions]
    permission_required = ["audit.view_auditlog"]
    filterset_class = AuditLogFilter
