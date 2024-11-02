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

from audit.models import AuditLog, AuditSession
from django_filters.rest_framework.backends import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
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
            DefaultParams.ordering_by("-login_time"),
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Operation id.",
            ),
            OpenApiParameter(
                name="login",
                type=str,
                location=OpenApiParameter.QUERY,
                description="User login.",
            ),
            OpenApiParameter(
                name="loginResult",
                type=str,
                location=OpenApiParameter.QUERY,
                description="User login result.",
                enum=("success", "wrong password", "user not found", "account disabled"),
            ),
            OpenApiParameter(
                name="loginTime",
                type=date,
                location=OpenApiParameter.QUERY,
                description="User login time.",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                required=False,
                enum=(
                    "loginTime",
                    "loginResult",
                    "login",
                    "id",
                    "-loginTime",
                    "-loginResult",
                    "-login",
                    "-id",
                    "time",
                    "-time",
                ),
                default="-loginTime",
            ),
        ],
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
    filter_backends = (DjangoFilterBackend,)


@extend_schema_view(
    list=extend_schema(
        operation_id="getAuditOperations",
        summary="GET audit operations",
        description="Get a list of audited ADCM operations.",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
            DefaultParams.ordering_by("-operation_time"),
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Operation id.",
            ),
            OpenApiParameter(
                name="name",
                location=OpenApiParameter.QUERY,
                description="Case insensitive and partial filter by operation name.",
                type=str,
            ),
            OpenApiParameter(
                name="userName",
                location=OpenApiParameter.QUERY,
                description="Case insensitive and partial filter by user name.",
                type=str,
            ),
            OpenApiParameter(
                name="result",
                location=OpenApiParameter.QUERY,
                description="Operation result filter.",
                type=str,
                enum=(
                    "success",
                    "fail",
                    "denied",
                ),
            ),
            OpenApiParameter(
                name="type",
                location=OpenApiParameter.QUERY,
                description="Operation type filter.",
                type=str,
                enum=(
                    "create",
                    "update",
                    "delete",
                ),
            ),
            OpenApiParameter(
                name="timeFrom",
                location=OpenApiParameter.QUERY,
                description="Operation time from.",
                type=date,
            ),
            OpenApiParameter(
                name="timeTo",
                location=OpenApiParameter.QUERY,
                description="Operation time to.",
                type=date,
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                required=False,
                enum=(
                    "id",
                    "-id",
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
    filter_backends = (DjangoFilterBackend,)
