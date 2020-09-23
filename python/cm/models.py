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
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.contrib.auth.models import User, Group, Permission
from django.db import models

from cm.errors import AdcmEx

PROTO_TYPE = (
    ('adcm', 'adcm'),
    ('service', 'service'),
    ('cluster', 'cluster'),
    ('host', 'host'),
    ('provider', 'provider'),
)


LICENSE_STATE = (
    ('absent', 'absent'),
    ('accepted', 'accepted'),
    ('unaccepted', 'unaccepted'),
)


class JSONField(models.Field):
    def db_type(self, connection):
        return 'text'

    def from_db_value(self, value, expression, connection):
        if value is not None:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise AdcmEx(
                    'JSON_DB_ERROR',
                    msg=f"Not correct field format '{expression.field.attname}'") from None
        return value

    def get_prep_value(self, value):
        if value is not None:
            return str(json.dumps(value))
        return value

    def to_python(self, value):
        if value is not None:
            return json.loads(value)
        return value

    def value_to_string(self, obj):
        return self.value_from_object(obj)


class Bundle(models.Model):
    name = models.CharField(max_length=160)
    version = models.CharField(max_length=80)
    version_order = models.PositiveIntegerField(default=0)
    edition = models.CharField(max_length=80, default='community')
    license = models.CharField(max_length=16, choices=LICENSE_STATE, default='absent')
    license_path = models.CharField(max_length=160, default=None, null=True)
    license_hash = models.CharField(max_length=64, default=None, null=True)
    hash = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    date = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('name', 'version', 'edition'),)


class Upgrade(models.Model):
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE)
    name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    min_version = models.CharField(max_length=80)
    max_version = models.CharField(max_length=80)
    from_edition = JSONField(default=['community'])
    min_strict = models.BooleanField(default=False)
    max_strict = models.BooleanField(default=False)
    state_available = JSONField(default=[])
    state_on_success = models.CharField(max_length=64, blank=True)


MONITORING_TYPE = (
    ('active', 'active'),
    ('passive', 'passive'),
)


class Prototype(models.Model):
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE)
    type = models.CharField(max_length=16, choices=PROTO_TYPE)
    path = models.CharField(max_length=160, default='')
    name = models.CharField(max_length=160)
    display_name = models.CharField(max_length=160, blank=True)
    version = models.CharField(max_length=80)
    version_order = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=False)
    shared = models.BooleanField(default=False)
    adcm_min_version = models.CharField(max_length=80, default=None, null=True)
    monitoring = models.CharField(max_length=16, choices=MONITORING_TYPE, default='active')
    description = models.TextField(blank=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        unique_together = (('bundle', 'type', 'name', 'version'),)


class ObjectConfig(models.Model):
    current = models.PositiveIntegerField()
    previous = models.PositiveIntegerField()


class ConfigLog(models.Model):
    obj_ref = models.ForeignKey(ObjectConfig, on_delete=models.CASCADE)
    config = JSONField(default={})
    attr = JSONField(default={})
    date = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True)


class ADCM(models.Model):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=16, choices=(('ADCM', 'ADCM'),), unique=True)
    config = models.OneToOneField(ObjectConfig, on_delete=models.CASCADE, null=True)
    state = models.CharField(max_length=64, default='created')
    stack = JSONField(default=[])
    issue = JSONField(default={})


class Cluster(models.Model):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    config = models.OneToOneField(ObjectConfig, on_delete=models.CASCADE, null=True)
    state = models.CharField(max_length=64, default='created')
    stack = JSONField(default=[])
    issue = JSONField(default={})

    def __str__(self):
        return str(self.name)


class HostProvider(models.Model):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    config = models.OneToOneField(ObjectConfig, on_delete=models.CASCADE, null=True)
    state = models.CharField(max_length=64, default='created')
    stack = JSONField(default=[])
    issue = JSONField(default={})

    def __str__(self):
        return str(self.name)


class Host(models.Model):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    fqdn = models.CharField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    provider = models.ForeignKey(HostProvider, on_delete=models.CASCADE, null=True, default=None)
    cluster = models.ForeignKey(Cluster, on_delete=models.SET_NULL, null=True, default=None)
    config = models.OneToOneField(ObjectConfig, on_delete=models.CASCADE, null=True)
    state = models.CharField(max_length=64, default='created')
    stack = JSONField(default=[])
    issue = JSONField(default={})

    def __str__(self):
        return "{}".format(self.fqdn)


class ClusterObject(models.Model):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    config = models.OneToOneField(ObjectConfig, on_delete=models.CASCADE, null=True)
    state = models.CharField(max_length=64, default='created')
    stack = JSONField(default=[])
    issue = JSONField(default={})

    class Meta:
        unique_together = (('cluster', 'prototype'),)


class Component(models.Model):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    display_name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    params = JSONField(default={})
    constraint = JSONField(default=[0, '+'])
    requires = JSONField(default=[])
    monitoring = models.CharField(max_length=16, choices=MONITORING_TYPE, default='active')

    class Meta:
        unique_together = (('prototype', 'name'),)


class ServiceComponent(models.Model):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    service = models.ForeignKey(ClusterObject, on_delete=models.CASCADE)
    component = models.ForeignKey(Component, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('cluster', 'service', 'component'),)


ACTION_TYPE = (
    ('task', 'task'),
    ('job', 'job'),
)

SCRIPT_TYPE = (
    ('ansible', 'ansible'),
    ('task_generator', 'task_generator'),
)


class Action(models.Model):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    display_name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    ui_options = JSONField(default={})

    type = models.CharField(max_length=16, choices=ACTION_TYPE)
    button = models.CharField(max_length=64, default=None, null=True)

    script = models.CharField(max_length=160)
    script_type = models.CharField(max_length=16, choices=SCRIPT_TYPE)

    state_on_success = models.CharField(max_length=64, blank=True)
    state_on_fail = models.CharField(max_length=64, blank=True)
    state_available = JSONField(default=[])

    params = JSONField(default={})
    log_files = JSONField(default=[])

    hostcomponentmap = JSONField(default=[])
    allow_to_terminate = models.BooleanField(default=False)
    partial_execution = models.BooleanField(default=False)

    def __str__(self):
        return "{} {}".format(self.prototype, self.name)

    class Meta:
        unique_together = (('prototype', 'name'),)


class SubAction(models.Model):
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    display_name = models.CharField(max_length=160, blank=True)
    script = models.CharField(max_length=160)
    script_type = models.CharField(max_length=16, choices=SCRIPT_TYPE)
    state_on_fail = models.CharField(max_length=64, blank=True)
    params = JSONField(default={})


class HostComponent(models.Model):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    service = models.ForeignKey(ClusterObject, on_delete=models.CASCADE)
    component = models.ForeignKey(ServiceComponent, on_delete=models.CASCADE)
    state = models.CharField(max_length=64, default='created')

    class Meta:
        unique_together = (('host', 'service', 'component'),)


CONFIG_FIELD_TYPE = (
    ('string', 'string'),
    ('text', 'text'),
    ('password', 'password'),
    ('json', 'json'),
    ('integer', 'integer'),
    ('float', 'float'),
    ('option', 'option'),
    ('variant', 'variant'),
    ('boolean', 'boolean'),
    ('file', 'file'),
    ('list', 'list'),
    ('map', 'map'),
    ('structure', 'structure'),
    ('group', 'group'),
)


class PrototypeConfig(models.Model):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE, null=True, default=None)
    name = models.CharField(max_length=160)
    subname = models.CharField(max_length=160, blank=True)
    default = models.TextField(blank=True)
    type = models.CharField(max_length=16, choices=CONFIG_FIELD_TYPE)
    display_name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    limits = JSONField(default={})
    ui_options = JSONField(blank=True, default={})
    required = models.BooleanField(default=True)

    class Meta:
        unique_together = (('prototype', 'action', 'name', 'subname'),)


class PrototypeExport(models.Model):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)

    class Meta:
        unique_together = (('prototype', 'name'),)


class PrototypeImport(models.Model):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    min_version = models.CharField(max_length=80)
    max_version = models.CharField(max_length=80)
    min_strict = models.BooleanField(default=False)
    max_strict = models.BooleanField(default=False)
    default = JSONField(null=True, default=None)
    required = models.BooleanField(default=False)
    multibind = models.BooleanField(default=False)

    class Meta:
        unique_together = (('prototype', 'name'),)


class ClusterBind(models.Model):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    service = models.ForeignKey(ClusterObject, on_delete=models.CASCADE, null=True, default=None)
    source_cluster = models.ForeignKey(
        Cluster, related_name='source_cluster', on_delete=models.CASCADE
    )
    source_service = models.ForeignKey(
        ClusterObject,
        related_name='source_service',
        on_delete=models.CASCADE,
        null=True,
        default=None
    )

    class Meta:
        unique_together = (('cluster', 'service', 'source_cluster', 'source_service'),)


JOB_STATUS = (
    ('created', 'created'),
    ('running', 'running'),
    ('success', 'success'),
    ('failed', 'failed')
)


class UserProfile(models.Model):
    login = models.CharField(max_length=32, unique=True)
    profile = JSONField(default='')


class Role(models.Model):
    name = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    user = models.ManyToManyField(User, blank=True)
    group = models.ManyToManyField(Group, blank=True)


class JobLog(models.Model):
    task_id = models.PositiveIntegerField(default=0)
    action_id = models.PositiveIntegerField()
    sub_action_id = models.PositiveIntegerField(default=0)
    pid = models.PositiveIntegerField(blank=True, default=0)
    selector = JSONField(default={})
    log_files = JSONField(default=[])
    status = models.CharField(max_length=16, choices=JOB_STATUS)
    start_date = models.DateTimeField()
    finish_date = models.DateTimeField(db_index=True)


class TaskLog(models.Model):
    action_id = models.PositiveIntegerField()
    object_id = models.PositiveIntegerField()
    pid = models.PositiveIntegerField(blank=True, default=0)
    selector = JSONField(default={})
    status = models.CharField(max_length=16, choices=JOB_STATUS)
    config = JSONField(null=True, default=None)
    attr = JSONField(default={})
    hostcomponentmap = JSONField(null=True, default=None)
    hosts = JSONField(null=True, default=None)
    start_date = models.DateTimeField()
    finish_date = models.DateTimeField()


class GroupCheckLog(models.Model):
    job_id = models.PositiveIntegerField(default=0)
    title = models.TextField()
    message = models.TextField(blank=True, null=True)
    result = models.BooleanField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['job_id', 'title'], name='unique_group_job')
        ]


class CheckLog(models.Model):
    group = models.ForeignKey(GroupCheckLog, blank=True, null=True, on_delete=models.CASCADE)
    job_id = models.PositiveIntegerField(default=0)
    title = models.TextField()
    message = models.TextField()
    result = models.BooleanField()


LOG_TYPE = (
    ('stdout', 'stdout'),
    ('stderr', 'stderr'),
    ('check', 'check'),
    ('custom', 'custom'),
)

FORMAT_TYPE = (
    ('txt', 'txt'),
    ('json', 'json'),
)


class LogStorage(models.Model):
    job = models.ForeignKey(JobLog, on_delete=models.CASCADE)
    name = models.TextField(default='')
    body = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=16, choices=LOG_TYPE)
    format = models.CharField(max_length=16, choices=FORMAT_TYPE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['job'], condition=models.Q(type='check'), name='unique_check_job')
        ]


# Stage: Temporary tables to load bundle

class StagePrototype(models.Model):
    type = models.CharField(max_length=16, choices=PROTO_TYPE)
    name = models.CharField(max_length=160)
    path = models.CharField(max_length=160, default='')
    display_name = models.CharField(max_length=160, blank=True)
    version = models.CharField(max_length=80)
    edition = models.CharField(max_length=80, default='community')
    license_path = models.CharField(max_length=160, default=None, null=True)
    license_hash = models.CharField(max_length=64, default=None, null=True)
    required = models.BooleanField(default=False)
    shared = models.BooleanField(default=False)
    adcm_min_version = models.CharField(max_length=80, default=None, null=True)
    description = models.TextField(blank=True)
    monitoring = models.CharField(max_length=16, choices=MONITORING_TYPE, default='active')

    def __str__(self):
        return str(self.name)

    class Meta:
        unique_together = (('type', 'name', 'version'),)


class StageUpgrade(models.Model):
    name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    min_version = models.CharField(max_length=80)
    max_version = models.CharField(max_length=80)
    min_strict = models.BooleanField(default=False)
    max_strict = models.BooleanField(default=False)
    from_edition = JSONField(default=['community'])
    state_available = JSONField(default=[])
    state_on_success = models.CharField(max_length=64, blank=True)


class StageComponent(models.Model):
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    display_name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    params = JSONField(default={})
    constraint = JSONField(default=[0, '+'])
    requires = JSONField(default=[])
    monitoring = models.CharField(max_length=16, choices=MONITORING_TYPE, default='active')

    class Meta:
        unique_together = (('prototype', 'name'),)


class StageAction(models.Model):
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    display_name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    ui_options = JSONField(default={})

    type = models.CharField(max_length=16, choices=ACTION_TYPE)
    button = models.CharField(max_length=64, default=None, null=True)

    script = models.CharField(max_length=160)
    script_type = models.CharField(max_length=16, choices=SCRIPT_TYPE)

    state_on_success = models.CharField(max_length=64, blank=True)
    state_on_fail = models.CharField(max_length=64, blank=True)
    state_available = JSONField(default=[])

    params = JSONField(default={})
    log_files = JSONField(default=[])

    hostcomponentmap = JSONField(default=[])
    allow_to_terminate = models.BooleanField(default=False)
    partial_execution = models.BooleanField(default=False)

    def __str__(self):
        return "{}:{}".format(self.prototype, self.name)

    class Meta:
        unique_together = (('prototype', 'name'),)


class StageSubAction(models.Model):
    action = models.ForeignKey(StageAction, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    display_name = models.CharField(max_length=160, blank=True)
    script = models.CharField(max_length=160)
    script_type = models.CharField(max_length=16, choices=SCRIPT_TYPE)
    state_on_fail = models.CharField(max_length=64, blank=True)
    params = JSONField(default={})


class StagePrototypeConfig(models.Model):
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)
    action = models.ForeignKey(StageAction, on_delete=models.CASCADE, null=True, default=None)
    name = models.CharField(max_length=160)
    subname = models.CharField(max_length=160, blank=True)
    default = models.TextField(blank=True)
    type = models.CharField(max_length=16, choices=CONFIG_FIELD_TYPE)
    display_name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    limits = JSONField(default={})
    ui_options = JSONField(blank=True, default={})   # JSON
    required = models.BooleanField(default=True)

    class Meta:
        unique_together = (('prototype', 'action', 'name', 'subname'),)


class StagePrototypeExport(models.Model):
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)

    class Meta:
        unique_together = (('prototype', 'name'),)


class StagePrototypeImport(models.Model):
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    min_version = models.CharField(max_length=80)
    max_version = models.CharField(max_length=80)
    min_strict = models.BooleanField(default=False)
    max_strict = models.BooleanField(default=False)
    default = JSONField(null=True, default=None)
    required = models.BooleanField(default=False)
    multibind = models.BooleanField(default=False)

    class Meta:
        unique_together = (('prototype', 'name'),)


class DummyData(models.Model):
    date = models.DateTimeField(auto_now=True)
