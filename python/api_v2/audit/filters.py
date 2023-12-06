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
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
    AuditSession,
    AuditSessionLoginResult,
)
from django_filters.rest_framework import (
    CharFilter,
    ChoiceFilter,
    DateTimeFilter,
    FilterSet,
    OrderingFilter,
)


class AuditLogFilterSet(FilterSet):
    object_name = CharFilter(field_name="audit_object__object_name", label="Object name", lookup_expr="icontains")
    object_type = ChoiceFilter(
        field_name="audit_object__object_type",
        choices=AuditObjectType.choices,
        label="Object type",
    )
    operation_result = ChoiceFilter(
        field_name="operation_result", label="Operation result", choices=AuditLogOperationResult.choices
    )
    operation_type = ChoiceFilter(
        field_name="operation_type", label="Operation type", choices=AuditLogOperationType.choices
    )
    time_from = DateTimeFilter(field_name="operation_time", lookup_expr="gte")
    time_to = DateTimeFilter(field_name="operation_time", lookup_expr="lte")
    username = CharFilter(field_name="user__username", label="Username", lookup_expr="icontains")
    ordering = OrderingFilter(
        fields={
            "audit_object__object_name": "objectName",
            "audit_object__object_type": "objectType",
            "operation_result": "result",
            "operation_type": "type",
            "operation_time": "time",
            "user__username": "userName",
        },
        field_labels={
            "audit_object__object_name": "Object name",
            "audit_object__object_type": "Object type",
            "operation_result": "result",
            "operation_type": "Type",
            "operation_time": "Time",
            "user__username": "User name",
        },
        label="ordering",
    )

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "object_name",
            "object_type",
            "operation_result",
            "operation_type",
            "time_from",
            "time_to",
            "username",
            "ordering",
        ]


class AuditSessionFilterSet(FilterSet):
    login = CharFilter(field_name="user__username", label="Login", lookup_expr="icontains")
    login_result = ChoiceFilter(
        field_name="login_result", label="Login result", choices=AuditSessionLoginResult.choices
    )
    time_from = DateTimeFilter(field_name="login_time", lookup_expr="gte", label="Time from")
    time_to = DateTimeFilter(field_name="login_time", lookup_expr="lte", label="Time to")
    ordering = OrderingFilter(
        fields={"login_time": "loginTime"}, field_labels={"login_time": "Login time"}, label="ordering"
    )

    class Meta:
        model = AuditSession
        fields = ["id", "login", "login_result", "time_from", "time_to", "ordering"]
