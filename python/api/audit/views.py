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

from rest_framework.mixins import ListModelMixin

from api.base_view import DetailView, GenericUIViewSet
from api.utils import SuperuserOnlyMixin
from audit.models import AuditLog, AuditSession
from . import serializers
from . import filters


class AuditOperationListView(SuperuserOnlyMixin, ListModelMixin, GenericUIViewSet):
    """
    get:
    List of all AuditLog entities
    """

    queryset = AuditLog.objects.select_related('audit_object', 'user').order_by(
        '-operation_time', '-pk'
    )
    model_class = AuditLog
    serializer_class = serializers.AuditLogSerializer
    filterset_class = filters.AuditOperationListFilter


class AuditOperationDetailView(SuperuserOnlyMixin, DetailView):
    queryset = AuditLog.objects.select_related('audit_object', 'user').all()
    model_class = AuditLog
    serializer_class = serializers.AuditLogSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    error_code = 'AUDIT_OPERATION_NOT_FOUND'


class AuditLoginListView(SuperuserOnlyMixin, ListModelMixin, GenericUIViewSet):
    """
    get:
    List of all AuditSession entities
    """

    queryset = AuditSession.objects.select_related('user').order_by('-login_time', '-pk')
    model_class = AuditSession
    serializer_class = serializers.AuditSessionSerializer
    filterset_class = filters.AuditLoginListFilter


class AuditLoginDetailView(SuperuserOnlyMixin, DetailView):
    queryset = AuditSession.objects.select_related('user').all()
    model_class = AuditSession
    serializer_class = serializers.AuditSessionSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    error_code = 'AUDIT_LOGIN_NOT_FOUND'
