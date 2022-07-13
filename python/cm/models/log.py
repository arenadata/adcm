import os
import signal
import time
from collections.abc import Mapping
from copy import deepcopy
from enum import Enum
from typing import Dict, Iterable

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from cm.config import FILE_DIR, Job
from cm.errors import AdcmEx
from cm.models.action import Action, SubAction
from cm.models.base import ADCMEntity, ADCMModel, ConcernItem, DummyData, ObjectConfig
from cm.models.cluster import Cluster, ClusterObject, ServiceComponent
from cm.models.host import Host, HostProvider
from cm.models.prototype import PrototypeConfig
from cm.models.types import ConcernCause, ConcernType, JOB_STATUS
from cm.models.utils import deep_merge


def validate_line_break_character(value: str) -> None:
    """Check line break character in CharField"""
    if len(value.splitlines()) > 1:
        raise ValidationError('the string field contains a line break character')


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


class GroupConfig(ADCMModel):
    object_id = models.PositiveIntegerField()
    object_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object = GenericForeignKey('object_type', 'object_id')
    name = models.CharField(max_length=30, validators=[validate_line_break_character])
    description = models.TextField(blank=True)
    hosts = models.ManyToManyField(Host, blank=True, related_name='group_config')
    config = models.OneToOneField(
        ObjectConfig, on_delete=models.CASCADE, null=True, related_name='group_config'
    )

    __error_code__ = 'GROUP_CONFIG_NOT_FOUND'

    not_changeable_fields = ('id', 'object_id', 'object_type')

    class Meta:
        unique_together = ['object_id', 'name', 'object_type']

    def get_config_spec(self):
        """Return spec for config"""
        spec = {}
        for field in PrototypeConfig.objects.filter(
            prototype=self.object.prototype, action__isnull=True
        ).order_by('id'):
            group_customization = field.group_customization
            if group_customization is None:
                group_customization = self.object.prototype.config_group_customization
            field_spec = {
                'type': field.type,
                'group_customization': group_customization,
                'limits': field.limits,
            }
            if field.subname == '':
                if field.type == 'group':
                    field_spec.update({'fields': {}})
                spec[field.name] = field_spec
            else:
                spec[field.name]['fields'][field.subname] = field_spec
        return spec

    def create_group_keys(
        self,
        config_spec: dict,
        group_keys: Dict[str, bool] = None,
        custom_group_keys: Dict[str, bool] = None,
    ):
        """
        Returns a map of fields that are included in a group,
        as well as a map of fields that cannot be included in a group
        """
        if group_keys is None:
            group_keys = {}
        if custom_group_keys is None:
            custom_group_keys = {}
        for k, v in config_spec.items():
            if v['type'] == 'group':
                value = None
                if 'activatable' in v['limits']:
                    value = False
                group_keys.setdefault(k, {'value': value, 'fields': {}})
                custom_group_keys.setdefault(k, {'value': v['group_customization'], 'fields': {}})
                self.create_group_keys(
                    v['fields'], group_keys[k]['fields'], custom_group_keys[k]['fields']
                )
            else:
                group_keys[k] = False
                custom_group_keys[k] = v['group_customization']
        return group_keys, custom_group_keys

    def get_diff_config_attr(self):
        def get_diff(config, attr, group_keys, diff_config=None, diff_attr=None):
            if diff_config is None:
                diff_config = {}
            if diff_attr is None:
                diff_attr = {}
            for k, v in group_keys.items():
                if isinstance(v, Mapping):
                    if v['value'] is not None and v['value']:
                        diff_attr[k] = attr[k]
                    diff_config.setdefault(k, {})
                    get_diff(config[k], attr, group_keys[k]['fields'], diff_config[k], diff_attr)
                    if not diff_config[k]:
                        diff_config.pop(k)
                else:
                    if v:
                        diff_config[k] = config[k]
            return diff_config, diff_attr

        cl = ConfigLog.obj.get(id=self.config.current)
        config = cl.config
        attr = cl.attr
        group_keys = cl.attr.get('group_keys', {})
        return get_diff(config, attr, group_keys)

    def get_group_keys(self):
        cl = ConfigLog.objects.get(id=self.config.current)
        return cl.attr.get('group_keys', {})

    def merge_config(self, object_config: dict, group_config: dict, group_keys: dict, config=None):
        """Merge object config with group config based group_keys"""

        if config is None:
            config = {}
        for k, v in group_keys.items():
            if isinstance(v, Mapping):
                config.setdefault(k, {})
                self.merge_config(
                    object_config[k], group_config[k], group_keys[k]['fields'], config[k]
                )
            else:
                if v and k in group_config:
                    config[k] = group_config[k]
                else:
                    if k in object_config:
                        config[k] = object_config[k]
        return config

    @staticmethod
    def merge_attr(object_attr: dict, group_attr: dict, group_keys: dict, attr=None):
        """Merge object attr with group attr based group_keys"""

        if attr is None:
            attr = {}

        for k, v in group_keys.items():
            if isinstance(v, Mapping) and k in object_attr:
                if v['value']:
                    attr[k] = group_attr[k]
                else:
                    attr[k] = object_attr[k]
        return attr

    def get_config_attr(self):
        """Return attr for group config without group_keys and custom_group_keys params"""
        cl = ConfigLog.obj.get(id=self.config.current)
        attr = {k: v for k, v in cl.attr.items() if k not in ('group_keys', 'custom_group_keys')}
        return attr

    def get_config_and_attr(self):
        """Return merge object config with group config and merge attr"""

        object_cl = ConfigLog.objects.get(id=self.object.config.current)
        object_config = object_cl.config
        object_attr = object_cl.attr
        group_cl = ConfigLog.objects.get(id=self.config.current)
        group_config = group_cl.config
        group_keys = group_cl.attr.get('group_keys', {})
        group_attr = self.get_config_attr()
        config = self.merge_config(object_config, group_config, group_keys)
        attr = self.merge_attr(object_attr, group_attr, group_keys)
        self.preparing_file_type_field(config)
        return config, attr

    def host_candidate(self):
        """Returns candidate hosts valid to add to the group"""
        if isinstance(self.object, (Cluster, HostProvider)):
            hosts = self.object.host_set.all()
        elif isinstance(self.object, ClusterObject):
            hosts = Host.objects.filter(
                cluster=self.object.cluster, hostcomponent__service=self.object
            ).distinct()
        elif isinstance(self.object, ServiceComponent):
            hosts = Host.objects.filter(
                cluster=self.object.cluster, hostcomponent__component=self.object
            ).distinct()
        else:
            raise AdcmEx('GROUP_CONFIG_TYPE_ERROR')
        return hosts.exclude(group_config__in=self.object.group_config.all())

    def check_host_candidate(self, host):
        """Checking host candidate for group"""
        if host not in self.host_candidate():
            raise AdcmEx('GROUP_CONFIG_HOST_ERROR')

    def preparing_file_type_field(self, config=None):
        """Creating file for file type field"""

        if self.config is None:
            return
        if config is None:
            config = ConfigLog.objects.get(id=self.config.current).config
        fields = PrototypeConfig.objects.filter(
            prototype=self.object.prototype, action__isnull=True, type='file'
        ).order_by('id')
        for field in fields:
            filename = '.'.join(
                [
                    self.object.prototype.type,
                    str(self.object.id),
                    'group',
                    str(self.id),
                    field.name,
                    field.subname,
                ]
            )
            filepath = os.path.join(FILE_DIR, filename)

            if field.subname:
                value = config[field.name][field.subname]
            else:
                value = config[field.name]
            if value is not None:
                # See cm.adcm_config.py:313
                if field.name == 'ansible_ssh_private_key_file':
                    if value != '':
                        if value[-1] == '-':
                            value += '\n'
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(value)
                os.chmod(filepath, 0o0600)
            else:
                if os.path.exists(filename):
                    os.remove(filename)

    @transaction.atomic()
    def save(self, *args, **kwargs):
        if self._state.adding:
            obj = self.object_type.model_class().obj.get(id=self.object_id)
            if obj.config is not None:
                parent_config_log = ConfigLog.obj.get(id=obj.config.current)
                self.config = ObjectConfig.objects.create(current=0, previous=0)
                config_log = ConfigLog()
                config_log.obj_ref = self.config
                config_log.config = deepcopy(parent_config_log.config)
                attr = deepcopy(parent_config_log.attr)
                group_keys, custom_group_keys = self.create_group_keys(self.get_config_spec())
                attr.update({'group_keys': group_keys, 'custom_group_keys': custom_group_keys})
                config_log.attr = attr
                config_log.description = parent_config_log.description
                config_log.save()
                self.config.current = config_log.pk
                self.config.save()
        super().save(*args, **kwargs)
        self.preparing_file_type_field()


class ConfigLog(ADCMModel):
    obj_ref = models.ForeignKey(ObjectConfig, on_delete=models.CASCADE)
    config = models.JSONField(default=dict)
    attr = models.JSONField(default=dict)
    date = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True)

    __error_code__ = 'CONFIG_NOT_FOUND'

    @transaction.atomic()
    def save(self, *args, **kwargs):  # pylint: disable=too-many-locals,too-many-statements
        """Saving config and updating config groups"""

        def update_config(origin: dict, renovator: dict, group_keys: dict) -> None:
            """
            Updating the original config with a check for the presence of keys in the original
            """
            for key, value in group_keys.items():
                if key in renovator:
                    if isinstance(value, Mapping):
                        origin.setdefault(key, {})
                        update_config(origin[key], renovator[key], group_keys[key]['fields'])
                    else:
                        if value:
                            origin[key] = renovator[key]

        def update_attr(origin: dict, renovator: dict, group_keys: dict) -> None:
            """
            Updating the original config with a check for the presence of keys in the original
            """
            for key, value in group_keys.items():
                if key in renovator and isinstance(value, Mapping):
                    if value['value'] is not None and value['value']:
                        origin[key] = renovator[key]

        def clean_attr(attrs: dict, spec: dict) -> None:
            """Clean attr after upgrade cluster"""
            extra_fields = []

            for key in attrs.keys():
                if key not in ['group_keys', 'custom_group_keys']:
                    if key not in spec:
                        extra_fields.append(key)

            for field in extra_fields:
                attrs.pop(field)

        def clean_group_keys(group_keys, spec):
            """Clean group_keys after update cluster"""
            correct_group_keys = {}
            for field, info in spec.items():
                if info['type'] == 'group':
                    correct_group_keys[field] = {}
                    correct_group_keys[field]['value'] = group_keys[field]['value']
                    correct_group_keys[field]['fields'] = {}
                    for key in info['fields'].keys():
                        correct_group_keys[field]['fields'][key] = group_keys[field]['fields'][key]
                else:
                    correct_group_keys[field] = group_keys[field]
            return correct_group_keys

        DummyData.objects.filter(id=1).update(date=timezone.now())
        obj = self.obj_ref.object
        if isinstance(obj, (Cluster, ClusterObject, ServiceComponent, HostProvider)):
            # Sync group configs with object config
            for cg in obj.group_config.all():
                # TODO: We need refactoring for upgrade cluster
                diff_config, diff_attr = cg.get_diff_config_attr()
                group_config = ConfigLog()
                current_group_config = ConfigLog.objects.get(id=cg.config.current)
                group_config.obj_ref = cg.config
                config = deepcopy(self.config)
                current_group_keys = current_group_config.attr['group_keys']
                update_config(config, diff_config, current_group_keys)
                group_config.config = config
                attr = deepcopy(self.attr)
                update_attr(attr, diff_attr, current_group_keys)
                spec = cg.get_config_spec()
                group_keys, custom_group_keys = cg.create_group_keys(spec)
                group_keys = deep_merge(group_keys, current_group_keys)
                group_keys = clean_group_keys(group_keys, spec)
                attr['group_keys'] = group_keys
                attr['custom_group_keys'] = custom_group_keys
                clean_attr(attr, spec)

                group_config.attr = attr
                group_config.description = current_group_config.description
                group_config.save()
                cg.config.previous = cg.config.current
                cg.config.current = group_config.id
                cg.config.save()
                cg.preparing_file_type_field()

        if isinstance(obj, GroupConfig):
            # `custom_group_keys` read only field in attr,
            # needs to be replaced when creating an object with ORM
            # for api it is checked in /cm/adcm_config.py:check_custom_group_keys_attr()
            _, custom_group_keys = obj.create_group_keys(obj.get_config_spec())
            self.attr.update({'custom_group_keys': custom_group_keys})

        super().save(*args, **kwargs)


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