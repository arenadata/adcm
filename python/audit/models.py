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

from dataclasses import dataclass

from django.contrib.auth.models import User
from django.db import models


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


class AuditSessionLoginResult(models.TextChoices):
    Success = "success", "success"
    WrongPassword = "wrong_password", "wrong_password"
    AccountDisabled = "account_disabled", "account_disabled"
    UserNotFound = "user_not_found", "user_not_found"


class AuditObject(models.Model):
    object_id = models.PositiveIntegerField()
    object_name = models.CharField(max_length=160)
    object_type = models.CharField(max_length=16, choices=AuditObjectType.choices)
    is_deleted = models.BooleanField(default=False)


class AuditLog(models.Model):
    audit_object = models.ForeignKey(AuditObject, on_delete=models.CASCADE, null=True)
    operation_name = models.CharField(max_length=160)
    operation_type = models.CharField(max_length=16, choices=AuditLogOperationType.choices)
    operation_result = models.CharField(max_length=16, choices=AuditLogOperationResult.choices)
    operation_time = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    object_changes = models.JSONField(default=dict)


class AuditSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    login_result = models.CharField(max_length=64, choices=AuditSessionLoginResult.choices)
    login_time = models.DateTimeField(auto_now_add=True)


@dataclass
class AuditOperation:
    name: str
    operation_type: str
    object_type: str


AUDIT_OPERATION_MAP = {
    "LoadBundle": {
        "POST": AuditOperation(
            name=f"{AuditObjectType.Bundle.label.capitalize()} loaded",
            operation_type=AuditLogOperationType.Create.label,
            object_type=AuditObjectType.Bundle.label,
        ),
    },
    "UploadBundle": {
        "POST": AuditOperation(
            name=f"{AuditObjectType.Bundle.label.capitalize()} uploaded",
            operation_type=AuditLogOperationType.Create.label,
            object_type=AuditObjectType.Bundle.label,
        ),
    },
    "ClusterList": {
        "POST": AuditOperation(
            name=f"{AuditObjectType.Cluster.label.capitalize()} "
                 f"{AuditLogOperationType.Create.label}d",
            operation_type=AuditLogOperationType.Create.label,
            object_type=AuditObjectType.Cluster.label,
        ),
    },
    "ConfigLogViewSet": {
        "POST": AuditOperation(
            name="???",
            operation_type=AuditLogOperationType.Create.label,
            object_type="???",
        ),
    },
    "HostList": {
        "POST": AuditOperation(
            name=f"{AuditObjectType.Host.label.capitalize()} {AuditLogOperationType.Create.label}d",
            operation_type=AuditLogOperationType.Create.label,
            object_type=AuditObjectType.Host.label,
        ),
    },
}
