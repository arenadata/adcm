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

from audit.models import AuditLog, AuditObjectType, AuditSession
from django_filters.rest_framework import (
    CharFilter,
    ChoiceFilter,
    DateFilter,
    FilterSet,
    IsoDateTimeFromToRangeFilter,
)


class AuditLogListFilter(FilterSet):
    object_type = ChoiceFilter(
        field_name="audit_object__object_type",
        choices=AuditObjectType.choices,
        label="Object type",
    )
    object_name = CharFilter(field_name="audit_object__object_name", label="Object name")
    operation_date = DateFilter(field_name="operation_time", lookup_expr="date", label="Operation date")
    username = CharFilter(field_name="user__username", label="Username")
    operation_time = IsoDateTimeFromToRangeFilter()

    class Meta:
        model = AuditLog
        fields = [
            "operation_type",
            "operation_name",
            "operation_result",
        ]


class AuditSessionListFilter(FilterSet):
    username = CharFilter(field_name="user__username", label="Username")
    login_date = DateFilter(field_name="login_time", lookup_expr="date", label="Login date")
    login_time = IsoDateTimeFromToRangeFilter()

    class Meta:
        model = AuditSession
        fields = [
            "login_result",
        ]
