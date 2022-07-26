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

from django_filters import rest_framework as drf_filters
from audit.models import AuditLog, AuditSession


class AuditOperationListFilter(drf_filters.FilterSet):
    operation_date = drf_filters.DateFilter(
        field_name='operation_time', lookup_expr='date', label='Operation date'
    )

    class Meta:
        model = AuditLog
        fields = [
            'audit_object__object_type',
            'audit_object__object_name',
            'operation_type',
            'operation_name',
            'operation_result',
            'operation_date',
            'user__username',
        ]


class AuditLoginListFilter(drf_filters.FilterSet):
    login_date = drf_filters.DateFilter(
        field_name='login_time', lookup_expr='date', label='Login date'
    )

    class Meta:
        model = AuditSession
        fields = ['user__username', 'login_result', 'login_date']
