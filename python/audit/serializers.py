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


from rest_framework.serializers import (
    CharField,
    HyperlinkedModelSerializer,
    IntegerField,
    SerializerMethodField,
)

from audit.models import AuditLog, AuditSession


class AuditLogSerializer(HyperlinkedModelSerializer):
    object_id = IntegerField(read_only=True, source="audit_object.object_id", allow_null=True)
    object_type = CharField(read_only=True, source="audit_object.object_type", allow_null=True)
    object_name = CharField(read_only=True, source="audit_object.object_name", allow_null=True)
    username = CharField(read_only=True, source="user.username", allow_null=True)
    user_id = SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "object_id",
            "object_type",
            "object_name",
            "operation_type",
            "operation_name",
            "operation_result",
            "operation_time",
            "user_id",
            "username",
            "object_changes",
            "url",
        ]
        extra_kwargs = {"url": {"view_name": "audit:auditlog-detail"}}

    @staticmethod
    def get_user_id(obj: AuditLog) -> str | None:
        if obj.user:
            return obj.user.auth_user_id

        return None


class AuditSessionSerializer(HyperlinkedModelSerializer):
    user_id = SerializerMethodField()

    class Meta:
        model = AuditSession
        fields = [
            "id",
            "user_id",
            "login_result",
            "login_time",
            "login_details",
            "url",
        ]
        extra_kwargs = {
            "url": {"view_name": "audit:auditsession-detail"},
        }

    @staticmethod
    def get_user_id(obj: AuditSession) -> str | None:
        if obj.user:
            return obj.user.auth_user_id

        return None
