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

from api_v2.audit.filters import AuditLogFilterSet, AuditSessionFilterSet
from api_v2.audit.serializers import AuditLogSerializer, AuditSessionSerializer
from api_v2.views import CamelCaseReadOnlyModelViewSet
from audit.models import AuditLog, AuditSession
from django_filters.rest_framework.backends import DjangoFilterBackend

from adcm.permissions import SuperuserOnlyMixin


# pylint: disable=too-many-ancestors
class AuditSessionViewSet(SuperuserOnlyMixin, CamelCaseReadOnlyModelViewSet):
    not_superuser_error_code = "AUDIT_LOGINS_FORBIDDEN"
    queryset = AuditSession.objects.select_related("user").order_by("-login_time")
    serializer_class = AuditSessionSerializer
    filterset_class = AuditSessionFilterSet
    filter_backends = (DjangoFilterBackend,)


class AuditLogViewSet(SuperuserOnlyMixin, CamelCaseReadOnlyModelViewSet):
    not_superuser_error_code = "AUDIT_OPERATIONS_FORBIDDEN"
    queryset = AuditLog.objects.select_related("audit_object", "user").order_by("-operation_time")
    serializer_class = AuditLogSerializer
    filterset_class = AuditLogFilterSet
    filter_backends = (DjangoFilterBackend,)
