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
from guardian.mixins import PermissionListMixin
from rest_framework.permissions import DjangoObjectPermissions

from api_v2.audit.filters import AuditLogFilterSet, AuditSessionFilterSet
from api_v2.audit.serializers import AuditLogSerializer, AuditSessionSerializer
from api_v2.views import CamelCaseReadOnlyModelViewSet


class AuditSessionViewSet(PermissionListMixin, CamelCaseReadOnlyModelViewSet):
    queryset = AuditSession.objects.select_related("user").order_by("-login_time")
    serializer_class = AuditSessionSerializer
    permission_classes = [DjangoObjectPermissions]
    permission_required = ["audit.view_auditsession"]
    filterset_class = AuditSessionFilterSet
    filter_backends = (DjangoFilterBackend,)


class AuditLogViewSet(PermissionListMixin, CamelCaseReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("audit_object", "user").order_by("-operation_time")
    serializer_class = AuditLogSerializer
    permission_classes = [DjangoObjectPermissions]
    permission_required = ["audit.view_auditlog"]
    filterset_class = AuditLogFilterSet
    filter_backends = (DjangoFilterBackend,)
