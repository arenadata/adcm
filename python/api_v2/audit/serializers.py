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
from rest_framework.fields import CharField, DateTimeField, SerializerMethodField
from rest_framework.serializers import ModelSerializer


class AuditSessionSerializer(ModelSerializer):
    user = SerializerMethodField()
    result = CharField(source="login_result")
    time = DateTimeField(source="login_time")

    class Meta:
        model = AuditSession
        fields = ("id", "user", "result", "time")

    @staticmethod
    def get_user(obj: AuditSession) -> dict:
        return {"name": obj.user.username}


class AuditLogSerializer(ModelSerializer):
    time = DateTimeField(source="operation_time")
    name = CharField(read_only=True, source="operation_name")
    type = CharField(read_only=True, source="operation_type")
    result = CharField(read_only=True, source="operation_result")
    user = SerializerMethodField()
    object = SerializerMethodField()

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

    @staticmethod
    def get_user(obj: AuditLog) -> dict | None:
        if not obj.user:
            return None
        return {"name": obj.user.username}

    @staticmethod
    def get_object(obj: AuditLog) -> dict | None:
        if not obj.audit_object:
            return None

        return {
            "id": obj.audit_object.object_id,
            "type": obj.audit_object.object_type,
            "name": obj.audit_object.object_name,
        }
