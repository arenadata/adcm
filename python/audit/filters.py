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

from audit.models import AuditLog, AuditObjectType, AuditSession


class AuditLogListFilter(drf_filters.FilterSet):
    object_type = drf_filters.ChoiceFilter(
        field_name='audit_object__object_type', choices=AuditObjectType.choices, label='Object type'
    )
    object_name = drf_filters.CharFilter(
        field_name='audit_object__object_name', label='Object name'
    )
    operation_date = drf_filters.DateFilter(
        field_name='operation_time', lookup_expr='date', label='Operation date'
    )
    username = drf_filters.CharFilter(field_name='user__username', label='Username')

    class Meta:
        model = AuditLog
        fields = [
            'operation_type',
            'operation_name',
            'operation_result',
        ]


class AuditSessionListFilter(drf_filters.FilterSet):
    username = drf_filters.CharFilter(field_name='user__username', label='Username')
    login_date = drf_filters.DateFilter(
        field_name='login_time', lookup_expr='date', label='Login date'
    )

    class Meta:
        model = AuditSession
        fields = [
            'login_result',
        ]
