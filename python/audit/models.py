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

from django.contrib.auth.models import User as DjangoUser
from django.db import models

from cm.models import (
    ADCM,
    Bundle,
    Cluster,
    ClusterObject,
    Host,
    HostProvider,
    Prototype,
    ServiceComponent,
)
from rbac.models import Group, Policy, Role, User


class AuditObjectType(models.TextChoices):
    Prototype = "prototype", "prototype"
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
    Fail = "fail", "fail"
    Denied = "denied", "denied"


class AuditSessionLoginResult(models.TextChoices):
    Success = "success", "success"
    WrongPassword = "wrong password", "wrong password"
    AccountDisabled = "account disabled", "account disabled"
    UserNotFound = "user not found", "user not found"


class AuditObject(models.Model):
    object_id = models.PositiveIntegerField()
    object_name = models.CharField(max_length=1000)
    object_type = models.CharField(max_length=1000, choices=AuditObjectType.choices)
    is_deleted = models.BooleanField(default=False)


class AuditLog(models.Model):
    audit_object = models.ForeignKey(AuditObject, on_delete=models.CASCADE, null=True)
    operation_name = models.CharField(max_length=1000)
    operation_type = models.CharField(max_length=1000, choices=AuditLogOperationType.choices)
    operation_result = models.CharField(max_length=1000, choices=AuditLogOperationResult.choices)
    operation_time = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(DjangoUser, on_delete=models.CASCADE, null=True)
    object_changes = models.JSONField(default=dict)


class AuditSession(models.Model):
    user = models.ForeignKey(DjangoUser, on_delete=models.CASCADE, null=True)
    login_result = models.CharField(max_length=1000, choices=AuditSessionLoginResult.choices)
    login_time = models.DateTimeField(auto_now_add=True)
    login_details = models.JSONField(default=dict, null=True)


@dataclass
class AuditOperation:
    name: str
    operation_type: str


MODEL_TO_AUDIT_OBJECT_TYPE_MAP = {
    Cluster: AuditObjectType.Cluster,
    ClusterObject: AuditObjectType.Service,
    ServiceComponent: AuditObjectType.Component,
    Host: AuditObjectType.Host,
    HostProvider: AuditObjectType.Provider,
    Bundle: AuditObjectType.Bundle,
    ADCM: AuditObjectType.ADCM,
    User: AuditObjectType.User,
    Group: AuditObjectType.Group,
    Role: AuditObjectType.Role,
    Policy: AuditObjectType.Policy,
    Prototype: AuditObjectType.Prototype,
}

AUDIT_OBJECT_TYPE_TO_MODEL_MAP = {v: k for k, v in MODEL_TO_AUDIT_OBJECT_TYPE_MAP.items()}

PATH_STR_TO_OBJ_CLASS_MAP = {
    "adcm": ADCM,
    "service": ClusterObject,
    "component": ServiceComponent,
    "provider": HostProvider,
    "host": Host,
    "cluster": Cluster,
}
