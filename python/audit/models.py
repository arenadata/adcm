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

from django.db import models
from rbac.models import User


class AuditObjectType(models.TextChoices):
    Cluster = "cluster", "cluster"
    Service = "service", "service"
    Component = "component", "component"
    Host = "host", "host"
    Provider = "provider", "provider"
    Bundle = "bundle", "bundle"
    ADCM = "adcm", "adcm"
    User = "user", "user"
    Group = "group", "group"
    Role = "role", "role"
    Policy = "policy", "policy"


class AuditLogOperationType(models.TextChoices):
    Create = "create", "create"
    Update = "update", "update"
    Delete = "delete", "delete"


class AuditLogOperationResult(models.TextChoices):
    Success = "success", "success"
    Failed = "failed", "failed"
    InProgress = "in_progress", "in_progress"


class AuditObject(models.Model):
    object_id = models.PositiveIntegerField()
    object_name = models.CharField(max_length=160)
    object_type = models.CharField(max_length=16, choices=AuditObjectType.choices)
    is_deleted = models.BooleanField(default=False)


class AuditLog(models.Model):
    audit_object_id = models.ForeignKey(AuditObject, on_delete=models.CASCADE)
    operation_name = models.CharField(max_length=160)
    operation_type = models.CharField(max_length=16, choices=AuditLogOperationType.choices)
    operation_result = models.CharField(max_length=16, choices=AuditLogOperationResult.choices)
    operation_time = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class AuditObjectChanges(models.Model):
    audit_object_id = models.ForeignKey(AuditObject, on_delete=models.CASCADE)
    object_attr = models.CharField(max_length=160)
    attr_old_value = models.CharField(max_length=160)
    attr_new_value = models.CharField(max_length=160)
    change_time = models.DateTimeField(auto_now_add=True)
    audit_log = models.ForeignKey(AuditLog, on_delete=models.CASCADE)
