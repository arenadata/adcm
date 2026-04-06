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


from audit.models import (
    AuditLog,
    AuditSession,
)
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from rest_framework.permissions import AllowAny, DjangoObjectPermissions
from rest_framework.routers import APIRootView
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from api_v2.api_schema import DefaultParams, responses
from api_v2.audit.filters import AuditLogFilter, AuditSessionFilter
from api_v2.audit.serializers import AuditLogSerializer, AuditSessionSerializer
from api_v2.views import ADCMReadOnlyModelViewSet


class AuditRoot(APIRootView):
    permission_classes = (AllowAny,)
    api_root_dict = {
        "operations": "auditlog-list",
        "logins": "auditsession-list",
    }


@extend_schema_view(
    list=extend_schema(
        operation_id="getAuditLogins",
        summary="GET audit logins",
        description="Get information about auditing user authorizations in ADCM.",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
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
        responses=responses(success=(HTTP_200_OK, AuditSessionSerializer(many=True))),
    ),
    retrieve=extend_schema(
        operation_id="getAuditLogin",
        summary="GET audit login",
        description="Get information about a specific user authorization in ADCM.",
        responses=responses(success=(HTTP_200_OK, AuditSessionSerializer), errors=HTTP_404_NOT_FOUND),
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
        responses=responses(success=(HTTP_200_OK, AuditLogSerializer(many=True))),
    ),
    retrieve=extend_schema(
        operation_id="getAuditOperation",
        summary="GET audit operation",
        description="Get information about a specific ADCM operation being audited.",
        responses=responses(success=(HTTP_200_OK, AuditLogSerializer), errors=HTTP_404_NOT_FOUND),
    ),
)
class AuditLogViewSet(PermissionListMixin, ADCMReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("audit_object", "user").order_by("-operation_time")
    serializer_class = AuditLogSerializer
    permission_classes = [DjangoObjectPermissions]
    permission_required = ["audit.view_auditlog"]
    filterset_class = AuditLogFilter
