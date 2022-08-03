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

from rest_framework.permissions import AllowAny
from rest_framework.routers import APIRootView
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.utils import SuperuserOnlyMixin
from audit.models import AuditLog, AuditSession
from . import serializers
from . import filters


class AuditRoot(APIRootView):
    """Audit Root"""

    permission_classes = (AllowAny,)
    api_root_dict = {
        'operations': 'audit-operations-list',
        'logins': 'audit-logins-list',
    }


# pylint: disable=too-many-ancestors
class AuditOperationViewSet(SuperuserOnlyMixin, ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('audit_object', 'user').order_by(
        '-operation_time', '-pk'
    )
    model_class = AuditLog
    serializer_class = serializers.AuditLogSerializer
    filterset_class = filters.AuditOperationListFilter


# pylint: disable=too-many-ancestors
class AuditLoginViewSet(SuperuserOnlyMixin, ReadOnlyModelViewSet):
    queryset = AuditSession.objects.select_related('user').order_by('-login_time', '-pk')
    model_class = AuditSession
    serializer_class = serializers.AuditSessionSerializer
    filterset_class = filters.AuditLoginListFilter
