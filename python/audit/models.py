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
    ActionHostGroup,
    Bundle,
    Cluster,
    ClusterObject,
    Host,
    HostProvider,
    Prototype,
    ServiceComponent,
)
from django.conf import settings
from django.db.models import (
    CASCADE,
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKey,
    JSONField,
    Model,
    PositiveBigIntegerField,
    PositiveIntegerField,
    TextChoices,
)
from rbac.models import Group, Policy, Role, User


class AuditObjectType(TextChoices):
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
    ACTION_HOST_GROUP = "action-host-group", "action-host-group"


class AuditLogOperationType(TextChoices):
    CREATE = "create", "create"
    UPDATE = "update", "update"
    DELETE = "delete", "delete"


class AuditLogOperationResult(TextChoices):
    SUCCESS = "success", "success"
    FAIL = "fail", "fail"
    DENIED = "denied", "denied"


class AuditSessionLoginResult(TextChoices):
    SUCCESS = "success", "success"
    WRONG_PASSWORD = "wrong password", "wrong password"
    ACCOUNT_DISABLED = "account disabled", "account disabled"
    USER_NOT_FOUND = "user not found", "user not found"


class AuditObject(Model):
    object_id = PositiveIntegerField()
    object_name = CharField(max_length=2000)
    object_type = CharField(max_length=2000, choices=AuditObjectType.choices)
    is_deleted = BooleanField(default=False)


class AuditUser(Model):
    username = CharField(max_length=settings.USERNAME_MAX_LENGTH, null=False, blank=False)
    auth_user_id = PositiveBigIntegerField()
    created_at = DateTimeField(null=True)
    deleted_at = DateTimeField(null=True)


class AuditLog(Model):
    audit_object = ForeignKey(AuditObject, on_delete=CASCADE, null=True)
    operation_name = CharField(max_length=2000)
    operation_type = CharField(max_length=2000, choices=AuditLogOperationType.choices)
    operation_result = CharField(max_length=2000, choices=AuditLogOperationResult.choices)
    operation_time = DateTimeField(auto_now_add=True)
    user = ForeignKey(AuditUser, on_delete=CASCADE, null=True)
    object_changes = JSONField(default=dict)
    address = CharField(max_length=255, null=True)
    agent = CharField(max_length=255, blank=True, default="")


class AuditSession(Model):
    user = ForeignKey(AuditUser, on_delete=CASCADE, null=True)
    login_result = CharField(max_length=2000, choices=AuditSessionLoginResult.choices)
    login_time = DateTimeField(auto_now_add=True)
    login_details = JSONField(default=dict, null=True)
    address = CharField(max_length=255, null=True)
    agent = CharField(max_length=255, blank=True, default="")


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
    ActionHostGroup: AuditObjectType.ACTION_HOST_GROUP,
}

AUDIT_OBJECT_TYPE_TO_MODEL_MAP = {v: k for k, v in MODEL_TO_AUDIT_OBJECT_TYPE_MAP.items()}

PATH_STR_TO_OBJ_CLASS_MAP = {
    "adcm": ADCM,
    "service": ClusterObject,
    "services": ClusterObject,
    "component": ServiceComponent,
    "components": ServiceComponent,
    "provider": HostProvider,
    "hostproviders": HostProvider,
    "host": Host,
    "hosts": Host,
    "cluster": Cluster,
    "clusters": Cluster,
    "action-host-groups": ActionHostGroup,
}
