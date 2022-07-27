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


from rest_framework import serializers
from audit.models import AuditLog, AuditSession


class AuditLogSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    object_id = serializers.IntegerField(read_only=True, source='audit_object.object_id')
    object_type = serializers.CharField(read_only=True, source='audit_object.object_type')
    object_name = serializers.CharField(read_only=True, source='audit_object.object_name')
    operation_type = serializers.CharField(read_only=True)
    operation_name = serializers.CharField(read_only=True)
    operation_result = serializers.CharField(read_only=True)
    operation_time = serializers.DateTimeField(read_only=True)
    user_id = serializers.IntegerField(read_only=True, source='user.id')
    object_changes = serializers.JSONField(read_only=True)

    class Meta:
        model = AuditLog

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class AuditSessionSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    login_result = serializers.CharField(read_only=True)
    login_time = serializers.DateTimeField(read_only=True)
    login_details = serializers.JSONField(read_only=True)

    class Meta:
        model = AuditSession

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass
