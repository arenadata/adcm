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
    AuditObject,
    AuditObjectType,
    AuditSession,
    AuditSessionLoginResult,
    AuditUser,
)
from rest_framework.fields import CharField, ChoiceField, DateTimeField, DictField, IntegerField
from rest_framework.serializers import ModelSerializer


class AuditObjectSerializer(ModelSerializer):
    id = IntegerField(source="object_id")
    type = ChoiceField(choices=AuditObjectType, source="object_type")
    name = CharField(source="object_name")

    class Meta:
        model = AuditObject
        fields = ["id", "type", "name"]


class AuditUserShortSerializer(ModelSerializer):
    name = CharField(read_only=True, source="username")

    class Meta:
        model = AuditUser
        fields = ["name"]


class AuditLogSerializer(ModelSerializer):
    time = DateTimeField(source="operation_time")
    name = CharField(source="operation_name")
    type = ChoiceField(choices=AuditLogOperationType, source="operation_type")
    result = ChoiceField(choices=AuditLogOperationResult, source="operation_result")
    object = AuditObjectSerializer(source="audit_object", allow_null=True)
    user = AuditUserShortSerializer(allow_null=True)
    object_changes = DictField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "name",
            "type",
            "result",
            "time",
            "object",
            "user",
            "object_changes",
        ]


class AuditSessionSerializer(ModelSerializer):
    user = AuditUserShortSerializer(read_only=True, allow_null=True)
    result = ChoiceField(choices=AuditSessionLoginResult, source="login_result")
    time = DateTimeField(source="login_time")
    details = DictField(source="login_details")

    class Meta:
        model = AuditSession
        fields = ("id", "user", "result", "time", "details")
