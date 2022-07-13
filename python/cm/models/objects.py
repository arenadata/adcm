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

# pylint: disable=too-many-lines,unsupported-membership-test,unsupported-delete-operation,
# too-many-instance-attributes
# pylint could not understand that JSON fields are dicts

from __future__ import unicode_literals

import os.path
import signal
import time
from enum import Enum
from itertools import chain
from typing import Iterable

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from cm.config import Job
from cm.errors import AdcmEx
from cm.models.action import Action, SubAction
from cm.models.base import AbstractAction, AbstractSubAction, ADCMEntity, ADCMModel
from cm.models.cluster import Cluster, ClusterObject, ServiceComponent
from cm.models.host import Host, HostProvider
from cm.models.types import ConcernType, CONFIG_FIELD_TYPE, MONITORING_TYPE, PROTO_TYPE
from cm.models.utils import get_default_constraint, get_default_from_edition


def get_model_by_type(object_type):
    if object_type == 'adcm':
        return ADCM
    if object_type == 'cluster':
        return Cluster
    elif object_type == 'provider':
        return HostProvider
    elif object_type == 'service':
        return ClusterObject
    elif object_type == 'component':
        return ServiceComponent
    elif object_type == 'host':
        return Host
    else:
        # This function should return a Model, this is necessary for the correct
        # construction of the schema.
        return Cluster


class ADCM(ADCMEntity):
    name = models.CharField(max_length=16, choices=(('ADCM', 'ADCM'),), unique=True)

    @property
    def bundle_id(self):
        return self.prototype.bundle_id

    @property
    def display_name(self):
        return self.name

    @property
    def serialized_issue(self):
        result = {
            'id': self.id,
            'name': self.name,
            'issue': self.issue,
        }
        return result if result['issue'] else {}


JOB_STATUS = (
    ('created', 'created'),
    ('running', 'running'),
    ('success', 'success'),
    ('failed', 'failed'),
)


class UserProfile(ADCMModel):
    login = models.CharField(max_length=32, unique=True)
    profile = models.JSONField(default=str)


class TaskLog(ADCMModel):
    object_id = models.PositiveIntegerField()
    object_type = models.ForeignKey(ContentType, null=True, on_delete=models.CASCADE)
    task_object = GenericForeignKey('object_type', 'object_id')
    action = models.ForeignKey(Action, on_delete=models.SET_NULL, null=True, default=None)
    pid = models.PositiveIntegerField(blank=True, default=0)
    selector = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=JOB_STATUS)
    config = models.JSONField(null=True, default=None)
    attr = models.JSONField(default=dict)
    hostcomponentmap = models.JSONField(null=True, default=None)
    hosts = models.JSONField(null=True, default=None)
    verbose = models.BooleanField(default=False)
    start_date = models.DateTimeField()
    finish_date = models.DateTimeField()
    lock = models.ForeignKey('ConcernItem', null=True, on_delete=models.SET_NULL, default=None)

    def lock_affected(self, objects: Iterable[ADCMEntity]) -> None:
        if self.lock:
            return
        first_job = JobLog.obj.filter(task=self).order_by('id').first()
        reason = MessageTemplate.get_message_from_template(
            MessageTemplate.KnownNames.LockedByJob.value,
            job=first_job,
            target=self.task_object,
        )
        self.lock = ConcernItem.objects.create(
            type=ConcernType.Lock.value,
            name=None,
            reason=reason,
            blocking=True,
            owner=self.task_object,
            cause=ConcernCause.Job.value,
        )
        self.save()
        for obj in objects:
            obj.add_to_concerns(self.lock)

    def unlock_affected(self) -> None:
        if not self.lock:
            return

        lock = self.lock
        self.lock = None
        self.save()
        lock.delete()

    def cancel(self, event_queue: 'cm.status_api.Event' = None):
        """
        Cancel running task process
        task status will be updated in separate process of task runner
        """
        if self.pid == 0:
            raise AdcmEx(
                'NOT_ALLOWED_TERMINATION',
                'Termination is too early, try to execute later',
            )
        errors = {
            Job.FAILED: ('TASK_IS_FAILED', f'task #{self.pk} is failed'),
            Job.ABORTED: ('TASK_IS_ABORTED', f'task #{self.pk} is aborted'),
            Job.SUCCESS: ('TASK_IS_SUCCESS', f'task #{self.pk} is success'),
        }
        action = self.action
        if action and not action.allow_to_terminate:
            raise AdcmEx(
                'NOT_ALLOWED_TERMINATION',
                f'not allowed termination task #{self.pk} for action #{action.pk}',
            )
        if self.status in [Job.FAILED, Job.ABORTED, Job.SUCCESS]:
            raise AdcmEx(*errors.get(self.status))
        i = 0
        while not JobLog.objects.filter(task=self, status=Job.RUNNING) and i < 10:
            time.sleep(0.5)
            i += 1
        if i == 10:
            raise AdcmEx('NO_JOBS_RUNNING', 'no jobs running')
        self.unlock_affected()
        if event_queue:
            event_queue.send_state()
        os.kill(self.pid, signal.SIGTERM)


class JobLog(ADCMModel):
    task = models.ForeignKey(TaskLog, on_delete=models.SET_NULL, null=True, default=None)
    action = models.ForeignKey(Action, on_delete=models.SET_NULL, null=True, default=None)
    sub_action = models.ForeignKey(SubAction, on_delete=models.SET_NULL, null=True, default=None)
    pid = models.PositiveIntegerField(blank=True, default=0)
    selector = models.JSONField(default=dict)
    log_files = models.JSONField(default=list)
    status = models.CharField(max_length=16, choices=JOB_STATUS)
    start_date = models.DateTimeField()
    finish_date = models.DateTimeField(db_index=True)

    __error_code__ = 'JOB_NOT_FOUND'


class GroupCheckLog(ADCMModel):
    job = models.ForeignKey(JobLog, on_delete=models.SET_NULL, null=True, default=None)
    title = models.TextField()
    message = models.TextField(blank=True, null=True)
    result = models.BooleanField(blank=True, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['job', 'title'], name='unique_group_job')]


class CheckLog(ADCMModel):
    group = models.ForeignKey(GroupCheckLog, blank=True, null=True, on_delete=models.CASCADE)
    job = models.ForeignKey(JobLog, on_delete=models.SET_NULL, null=True, default=None)
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


class LogStorage(ADCMModel):
    job = models.ForeignKey(JobLog, on_delete=models.CASCADE)
    name = models.TextField(default='')
    body = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=16, choices=LOG_TYPE)
    format = models.CharField(max_length=16, choices=FORMAT_TYPE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['job'], condition=models.Q(type='check'), name='unique_check_job'
            )
        ]


# Stage: Temporary tables to load bundle


class StagePrototype(ADCMModel):
    type = models.CharField(max_length=16, choices=PROTO_TYPE)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, default=None)
    name = models.CharField(max_length=160)
    path = models.CharField(max_length=160, default='')
    display_name = models.CharField(max_length=160, blank=True)
    version = models.CharField(max_length=80)
    edition = models.CharField(max_length=80, default='community')
    license_path = models.CharField(max_length=160, default=None, null=True)
    license_hash = models.CharField(max_length=64, default=None, null=True)
    required = models.BooleanField(default=False)
    shared = models.BooleanField(default=False)
    constraint = models.JSONField(default=get_default_constraint)
    requires = models.JSONField(default=list)
    bound_to = models.JSONField(default=dict)
    adcm_min_version = models.CharField(max_length=80, default=None, null=True)
    description = models.TextField(blank=True)
    monitoring = models.CharField(max_length=16, choices=MONITORING_TYPE, default='active')
    config_group_customization = models.BooleanField(default=False)
    venv = models.CharField(default="default", max_length=160, blank=False)
    allow_maintenance_mode = models.BooleanField(default=False)

    __error_code__ = 'PROTOTYPE_NOT_FOUND'

    def __str__(self):
        return str(self.name)

    class Meta:
        unique_together = (('type', 'parent', 'name', 'version'),)


class StageUpgrade(ADCMModel):
    name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    min_version = models.CharField(max_length=80)
    max_version = models.CharField(max_length=80)
    min_strict = models.BooleanField(default=False)
    max_strict = models.BooleanField(default=False)
    from_edition = models.JSONField(default=get_default_from_edition)
    state_available = models.JSONField(default=list)
    state_on_success = models.CharField(max_length=64, blank=True)
    action = models.OneToOneField('StageAction', on_delete=models.CASCADE, null=True)


class StageAction(AbstractAction):  # pylint: disable=too-many-instance-attributes
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)


class StageSubAction(AbstractSubAction):
    action = models.ForeignKey(StageAction, on_delete=models.CASCADE)


class StagePrototypeConfig(ADCMModel):
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)
    action = models.ForeignKey(StageAction, on_delete=models.CASCADE, null=True, default=None)
    name = models.CharField(max_length=160)
    subname = models.CharField(max_length=160, blank=True)
    default = models.TextField(blank=True)
    type = models.CharField(max_length=16, choices=CONFIG_FIELD_TYPE)
    display_name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    limits = models.JSONField(default=dict)
    ui_options = models.JSONField(blank=True, default=dict)
    required = models.BooleanField(default=True)
    group_customization = models.BooleanField(null=True)

    class Meta:
        unique_together = (('prototype', 'action', 'name', 'subname'),)


class StagePrototypeExport(ADCMModel):
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)

    class Meta:
        unique_together = (('prototype', 'name'),)


class StagePrototypeImport(ADCMModel):
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    min_version = models.CharField(max_length=80)
    max_version = models.CharField(max_length=80)
    min_strict = models.BooleanField(default=False)
    max_strict = models.BooleanField(default=False)
    default = models.JSONField(null=True, default=None)
    required = models.BooleanField(default=False)
    multibind = models.BooleanField(default=False)

    class Meta:
        unique_together = (('prototype', 'name'),)


class MessageTemplate(ADCMModel):
    """
    Templates for `ConcernItem.reason
    There are two sources of templates - they are pre-created in migrations or loaded from bundles

    expected template format is
        {
            'message': 'Lorem ${ipsum} dolor sit ${amet}',
            'placeholder': {
                'lorem': {'type': 'cluster'},
                'amet': {'type': 'action'}
            }
        }

    placeholder fill functions have unified interface:
      @classmethod
      def _func(cls, placeholder_name, **kwargs) -> dict

    TODO: load from bundle
    TODO: check consistency on creation
    TODO: separate JSON processing logic from model
    """

    name = models.CharField(max_length=160, unique=True)
    template = models.JSONField()

    class KnownNames(Enum):
        LockedByJob = 'locked by running job on target'  # kwargs=(job, target)
        ConfigIssue = 'object config issue'  # kwargs=(source, )
        RequiredServiceIssue = 'required service issue'  # kwargs=(source, )
        RequiredImportIssue = 'required import issue'  # kwargs=(source, )
        HostComponentIssue = 'host component issue'  # kwargs=(source, )

    class PlaceHolderType(Enum):
        Action = 'action'
        ADCMEntity = 'adcm_entity'
        ADCM = 'adcm'
        Cluster = 'cluster'
        Service = 'service'
        Component = 'component'
        Provider = 'provider'
        Host = 'host'
        Job = 'job'

    @classmethod
    def get_message_from_template(cls, name: str, **kwargs) -> dict:
        """Find message template by its name and fill placeholders"""
        tpl = cls.obj.get(name=name).template
        filled_placeholders = {}
        try:
            for ph_name, ph_data in tpl['placeholder'].items():
                filled_placeholders[ph_name] = cls._fill_placeholder(ph_name, ph_data, **kwargs)
        except (KeyError, AttributeError, TypeError, AssertionError) as ex:
            if isinstance(ex, KeyError):
                msg = f'Message templating KeyError: "{ex.args[0]}" not found'
            elif isinstance(ex, AttributeError):
                msg = f'Message templating AttributeError: "{ex.args[0]}"'
            elif isinstance(ex, TypeError):
                msg = f'Message templating TypeError: "{ex.args[0]}"'
            elif isinstance(ex, AssertionError):
                msg = 'Message templating AssertionError: expected kwarg were not found'
            else:
                msg = None
            raise AdcmEx('MESSAGE_TEMPLATING_ERROR', msg=msg) from ex
        tpl['placeholder'] = filled_placeholders
        return tpl

    @classmethod
    def _fill_placeholder(cls, ph_name: str, ph_data: dict, **ph_source_data) -> dict:
        type_map = {
            cls.PlaceHolderType.Action.value: cls._action_placeholder,
            cls.PlaceHolderType.ADCMEntity.value: cls._adcm_entity_placeholder,
            cls.PlaceHolderType.ADCM.value: cls._adcm_entity_placeholder,
            cls.PlaceHolderType.Cluster.value: cls._adcm_entity_placeholder,
            cls.PlaceHolderType.Service.value: cls._adcm_entity_placeholder,
            cls.PlaceHolderType.Component.value: cls._adcm_entity_placeholder,
            cls.PlaceHolderType.Provider.value: cls._adcm_entity_placeholder,
            cls.PlaceHolderType.Host.value: cls._adcm_entity_placeholder,
            cls.PlaceHolderType.Job.value: cls._job_placeholder,
        }
        return type_map[ph_data['type']](ph_name, **ph_source_data)

    @classmethod
    def _action_placeholder(cls, _, **kwargs) -> dict:
        action = kwargs.get('action')
        assert action
        target = kwargs.get('target')
        assert target

        ids = target.get_id_chain()
        ids['action'] = action.pk
        return {
            'type': cls.PlaceHolderType.Action.value,
            'name': action.display_name,
            'ids': ids,
        }

    @classmethod
    def _adcm_entity_placeholder(cls, ph_name, **kwargs) -> dict:
        obj = kwargs.get(ph_name)
        assert obj

        return {
            'type': obj.prototype.type,
            'name': obj.display_name,
            'ids': obj.get_id_chain(),
        }

    @classmethod
    def _job_placeholder(cls, _, **kwargs) -> dict:
        job = kwargs.get('job')
        assert job
        action = job.sub_action or job.action

        return {
            'type': cls.PlaceHolderType.Job.value,
            'name': action.display_name or action.name,
            'ids': job.id,
        }


class ConcernCause(models.TextChoices):
    Config = 'config', 'config'
    Job = 'job', 'job'
    HostComponent = 'host-component', 'host-component'
    Import = 'import', 'import'
    Service = 'service', 'service'


class ConcernItem(ADCMModel):
    """
    Representation for object's lock/issue/flag
    Man-to-many from ADCMEntities
    One-to-one from TaskLog
    ...

    `type` is literally type of concern
    `name` is used for (un)setting flags from ansible playbooks
    `reason` is used to display/notify on front-end, text template and data for URL generation
        should be generated from pre-created templates model `MessageTemplate`
    `blocking` blocks actions from running
    `owner` is object-origin of concern
    `cause` is owner's parameter causing concern
    `related_objects` are back-refs from affected ADCMEntities.concerns
    """

    type = models.CharField(max_length=8, choices=ConcernType.choices, default=ConcernType.Lock)
    name = models.CharField(max_length=160, null=True, unique=True)
    reason = models.JSONField(default=dict)
    blocking = models.BooleanField(default=True)
    owner_id = models.PositiveIntegerField(null=True)
    owner_type = models.ForeignKey(ContentType, null=True, on_delete=models.CASCADE)
    owner = GenericForeignKey('owner_type', 'owner_id')
    cause = models.CharField(max_length=16, null=True, choices=ConcernCause.choices)

    @property
    def related_objects(self) -> Iterable[ADCMEntity]:
        """List of objects that has that item in concerns"""
        return chain(
            self.adcm_entities.all(),
            self.cluster_entities.all(),
            self.clusterobject_entities.all(),
            self.servicecomponent_entities.all(),
            self.hostprovider_entities.all(),
            self.host_entities.all(),
        )

    def delete(self, using=None, keep_parents=False):
        """Explicit remove many-to-many references before deletion in order to emit signals"""
        for entity in self.related_objects:
            entity.remove_from_concerns(self)
        return super().delete(using, keep_parents)
