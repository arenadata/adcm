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
from django.contrib.auth.models import User as DjangoUser
from django.db import models
from rbac.models import Group, Policy, Role, User


class AuditObjectType(models.TextChoices):
    PROTOTYPE = "prototype", "prototype"
    CLUSTER = "cluster", "cluster"
    SERVICE = "service", "service"
    COMPONENT = "component", "component"
    HOST = "host", "host"
    PROVIDER = "provider", "provider"
    BUNDLE = "bundle", "bundle"
    ADCM = "adcm", "adcm"
    USER = "user", "user"
    GROUP = "group", "group"
    ROLE = "role", "role"
    POLICY = "policy", "policy"


class AuditLogOperationType(models.TextChoices):
    CREATE = "create", "create"
    UPDATE = "update", "update"
    DELETE = "delete", "delete"


class AuditLogOperationResult(models.TextChoices):
    SUCCESS = "success", "success"
    FAIL = "fail", "fail"
    DENIED = "denied", "denied"


class AuditSessionLoginResult(models.TextChoices):
    SUCCESS = "success", "success"
    WRONG_PASSWORD = "wrong password", "wrong password"
    ACCOUNT_DISABLED = "account disabled", "account disabled"
    USER_NOT_FOUND = "user not found", "user not found"


class AuditObject(models.Model):
    object_id = models.PositiveIntegerField()
    object_name = models.CharField(max_length=2000)
    object_type = models.CharField(max_length=2000, choices=AuditObjectType.choices)
    is_deleted = models.BooleanField(default=False)


class AuditLog(models.Model):
    audit_object = models.ForeignKey(AuditObject, on_delete=models.CASCADE, null=True)
    operation_name = models.CharField(max_length=2000)
    operation_type = models.CharField(max_length=2000, choices=AuditLogOperationType.choices)
    operation_result = models.CharField(max_length=2000, choices=AuditLogOperationResult.choices)
    operation_time = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(DjangoUser, on_delete=models.CASCADE, null=True)
    object_changes = models.JSONField(default=dict)


class AuditSession(models.Model):
    user = models.ForeignKey(DjangoUser, on_delete=models.CASCADE, null=True)
    login_result = models.CharField(max_length=2000, choices=AuditSessionLoginResult.choices)
    login_time = models.DateTimeField(auto_now_add=True)
    login_details = models.JSONField(default=dict, null=True)


@dataclass
class AuditOperation:
    name: str
    operation_type: str


MODEL_TO_AUDIT_OBJECT_TYPE_MAP = {
    Cluster: AuditObjectType.CLUSTER,
    ClusterObject: AuditObjectType.SERVICE,
    ServiceComponent: AuditObjectType.COMPONENT,
    Host: AuditObjectType.HOST,
    HostProvider: AuditObjectType.PROVIDER,
    Bundle: AuditObjectType.BUNDLE,
    ADCM: AuditObjectType.ADCM,
    User: AuditObjectType.USER,
    Group: AuditObjectType.GROUP,
    Role: AuditObjectType.ROLE,
    Policy: AuditObjectType.POLICY,
    Prototype: AuditObjectType.PROTOTYPE,
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
