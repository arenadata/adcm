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
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
    AuditSessionLoginResult,
)
from django_filters.constants import EMPTY_VALUES
from django_filters.rest_framework import (
    CharFilter,
    ChoiceFilter,
    DateTimeFilter,
    NumberFilter,
    OrderingFilter,
)

from api_v2.filters import AdvancedFilterSet


class AuditLogFilter(
    AdvancedFilterSet,
    char_fields=("operation_result", "operation_type", ("username", "user__username")),
    number_fields=("id",),
):
    # Advanced filters
    object_id__eq = NumberFilter(field_name="audit_object__object_id", lookup_expr="exact", label="object_id__eq")
    object_type__eq = CharFilter(field_name="audit_object__object_type", lookup_expr="exact", label="object_type__eq")
    # ---

    # Deprecate filters, saved for backward compatibility.
    operation_result = ChoiceFilter(
        field_name="operation_result", label="Filter by operation result.", choices=AuditLogOperationResult.choices
    )
    operation_type = ChoiceFilter(
        field_name="operation_type", label="Filter by operation type.", choices=AuditLogOperationType.choices
    )
    username = CharFilter(
        field_name="user__username", label="Case insensitive and partial filter by user name.", lookup_expr="icontains"
    )
    # ---
    id = NumberFilter(field_name="id", label="Filter by id.")
    object_name = CharFilter(
        field_name="audit_object__object_name",
        label="Case insensitive and partial filter by object name.",
        lookup_expr="icontains",
    )
    object_type = ChoiceFilter(
        field_name="audit_object__object_type",
        choices=AuditObjectType.choices,
        label="Filter by object type.",
    )
    name = CharFilter(field_name="operation_name", label="Filter by name.", lookup_expr="exact")
    result = ChoiceFilter(
        field_name="operation_result", label="Filter by operation result.", choices=AuditLogOperationResult.choices
    )
    type = ChoiceFilter(
        field_name="operation_type", label="Filter by operation type.", choices=AuditLogOperationType.choices
    )
    time_from = DateTimeFilter(field_name="operation_time", lookup_expr="gte", label="Filter by time from.")
    time_to = DateTimeFilter(field_name="operation_time", lookup_expr="lte", label="Filter by time to.")
    user_name = CharFilter(
        field_name="user__username", label="Case insensitive and partial filter by user name.", lookup_expr="icontains"
    )
    ordering = OrderingFilter(
        fields={
            "audit_object__object_name": "objectName",
            "audit_object__object_type": "objectType",
            "operation_name": "name",
            "operation_result": "result",
            "operation_type": "type",
            "operation_time": "time",
            "user__username": "userName",
        },
        field_labels={
            "audit_object__object_name": "Object name",
            "audit_object__object_type": "Object type",
            "operation_name": "Name",
            "operation_result": "Result",
            "operation_type": "Type",
            "operation_time": "Time",
            "user__username": "User name",
        },
        label="ordering",
    )


class AuditSessionOrderingFilter(OrderingFilter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra["choices"] += [
            ("time", "Login time"),
            ("-time", "Login time (descending)"),
        ]

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        for i in range(len(value)):
            if value[i] == "time":
                value[i] = "loginTime"
            if value[i] == "-time":
                value[i] = "-loginTime"

        return super().filter(qs, value)


class AuditSessionFilter(
    AdvancedFilterSet,
    char_fields=(("username", "login_details__username"), "login_result"),
    number_fields=("id",),
):
    # Deprecate filters, saved for backward compatibility.
    login = CharFilter(
        field_name="login_details__username",
        label="Case insensitive and partial filter by user login.",
        lookup_expr="icontains",
    )
    login_result = ChoiceFilter(
        field_name="login_result", label="Filter by login result.", choices=AuditSessionLoginResult.choices
    )
    # ---
    id = NumberFilter(field_name="id", label="Filter by id.")
    user_name = CharFilter(field_name="user__username", label="Filter by user name.", lookup_expr="exact")
    details_username = CharFilter(
        field_name="login_details__username",
        label="Case insensitive and partial filter by user login.",
        lookup_expr="icontains",
    )
    result = ChoiceFilter(field_name="login_result", label="Filter by result.", choices=AuditSessionLoginResult.choices)
    time = DateTimeFilter(field_name="login_time", lookup_expr="exact", label="Filter by time.")
    time_from = DateTimeFilter(field_name="login_time", lookup_expr="gte", label="Filter by time from.")
    time_to = DateTimeFilter(field_name="login_time", lookup_expr="lte", label="Filter by time to.")
    ordering = AuditSessionOrderingFilter(
        fields={
            "login_time": "loginTime",
            "user_name": "userName",
            "result": "result",
            "time": "time",
        },
        field_labels={
            "login_time": "Login time",
            "user_name": "User name",
            "result": "Result",
            "time": "Time",
        },
        label="ordering",
    )
