# pylint: disable=too-many-lines,unsupported-membership-test,unsupported-delete-operation
#   pylint could not understand that JSON fields are dicts
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

# pylint: disable=too-many-instance-attributes

from __future__ import unicode_literals

from collections.abc import Mapping
from copy import deepcopy
from enum import Enum
from itertools import chain
from typing import Dict, Iterable, List, Optional

from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from cm.errors import AdcmEx
from cm.logger import log


class PrototypeEnum(Enum):
    ADCM = 'adcm'
    Cluster = 'cluster'
    Service = 'service'
    Component = 'component'
    Provider = 'provider'
    Host = 'host'


PROTO_TYPE = (
    ('adcm', 'adcm'),
    ('service', 'service'),
    ('component', 'component'),
    ('cluster', 'cluster'),
    ('host', 'host'),
    ('provider', 'provider'),
)

LICENSE_STATE = (
    ('absent', 'absent'),
    ('accepted', 'accepted'),
    ('unaccepted', 'unaccepted'),
)


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


def get_object_cluster(obj):
    if isinstance(obj, Cluster):
        return obj
    if hasattr(obj, 'cluster'):
        return obj.cluster
    else:
        return None


class ADCMManager(models.Manager):
    """
    Custom model manager catch ObjectDoesNotExist error and re-raise it as custom
    AdcmEx exception. AdcmEx is derived from DRF APIException, so it handled gracefully
    by DRF and is reported out as nicely formated error instead of ugly exception.

    Using ADCMManager can shorten you code significaly. Insted of

    try:
        cluster = Cluster.objects.get(id=id)
    except Cluster.DoesNotExist:
        raise AdcmEx(f'Cluster {id} is not found')

    You can just write

    cluster = Cluster.obj.get(id=id)

    and DRF magic do the rest.

    Please pay attention, to use ADCMManager you need reffer to "obj" model attribute,
    not "objects". "objects" attribute is reffered to standard Django model manager,
    so if you need familiar behavior you can use it as usual.
    """

    def get(self, *args, **kwargs):
        try:
            return super().get(*args, **kwargs)
        except ObjectDoesNotExist:
            if not hasattr(self.model, '__error_code__'):
                raise AdcmEx('NO_MODEL_ERROR_CODE', f'model: {self.model.__name__}') from None
            msg = f'{self.model.__name__} {kwargs} does not exist'
            raise AdcmEx(self.model.__error_code__, msg) from None


class ADCMModel(models.Model):
    objects = models.Manager()
    obj = ADCMManager()

    class Meta:
        abstract = True

    @classmethod
    def from_db(cls, db, field_names, values):
        """
        Saving the current instance values from the database for `not_changeable_fields` feature
        """
        # Default implementation of from_db()
        if len(values) != len(cls._meta.concrete_fields):
            values_iter = iter(values)
            values = [
                next(values_iter) if f.attname in field_names else models.DEFERRED
                for f in cls._meta.concrete_fields
            ]
        instance = cls(*values)
        instance._state.adding = False
        instance._state.db = db
        # customization to store the original field values on the instance
        # pylint: disable=attribute-defined-outside-init
        instance._loaded_values = dict(zip(field_names, values))
        return instance

    def save(self, *args, **kwargs):
        """Checking not changeable fields before saving"""
        if not self._state.adding:
            not_changeable_fields = getattr(self, 'not_changeable_fields', ())
            for field_name in not_changeable_fields:
                if isinstance(getattr(self, field_name), models.Model):
                    field_name = f'{field_name}_id'
                if getattr(self, field_name) != self._loaded_values[field_name]:
                    raise AdcmEx(
                        'NOT_CHANGEABLE_FIELDS',
                        f'{", ".join(not_changeable_fields)} fields cannot be changed',
                    )
        super().save(*args, **kwargs)


class Bundle(ADCMModel):
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

    __error_code__ = 'BUNDLE_NOT_FOUND'

    class Meta:
        unique_together = (('name', 'version', 'edition'),)


def get_default_from_edition():
    return ['community']


class Upgrade(ADCMModel):
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE)
    name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    min_version = models.CharField(max_length=80)
    max_version = models.CharField(max_length=80)
    from_edition = models.JSONField(default=get_default_from_edition)
    min_strict = models.BooleanField(default=False)
    max_strict = models.BooleanField(default=False)
    state_available = models.JSONField(default=list)
    state_on_success = models.CharField(max_length=64, blank=True)

    __error_code__ = 'UPGRADE_NOT_FOUND'


MONITORING_TYPE = (
    ('active', 'active'),
    ('passive', 'passive'),
)


def get_default_constraint():
    return [0, '+']


class Prototype(ADCMModel):
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE)
    type = models.CharField(max_length=16, choices=PROTO_TYPE)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, default=None)
    path = models.CharField(max_length=160, default='')
    name = models.CharField(max_length=160)
    display_name = models.CharField(max_length=160, blank=True)
    version = models.CharField(max_length=80)
    version_order = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=False)
    shared = models.BooleanField(default=False)
    constraint = models.JSONField(default=get_default_constraint)
    requires = models.JSONField(default=list)
    bound_to = models.JSONField(default=dict)
    adcm_min_version = models.CharField(max_length=80, default=None, null=True)
    monitoring = models.CharField(max_length=16, choices=MONITORING_TYPE, default='active')
    description = models.TextField(blank=True)
    config_group_customization = models.BooleanField(default=False)

    __error_code__ = 'PROTOTYPE_NOT_FOUND'

    def __str__(self):
        return str(self.name)

    class Meta:
        unique_together = (('bundle', 'type', 'parent', 'name', 'version'),)


class ObjectConfig(ADCMModel):
    current = models.PositiveIntegerField()
    previous = models.PositiveIntegerField()

    __error_code__ = 'CONFIG_NOT_FOUND'

    @property
    def object(self):
        """Returns object for ObjectConfig"""
        object_types = [
            'adcm',
            'cluster',
            'clusterobject',
            'servicecomponent',
            'hostprovider',
            'host',
            'group_config',
        ]
        for object_type in object_types:
            if hasattr(self, object_type):
                obj = getattr(self, object_type)
                return obj
        return None


class ConfigLog(ADCMModel):
    obj_ref = models.ForeignKey(ObjectConfig, on_delete=models.CASCADE)
    config = models.JSONField(default=dict)
    attr = models.JSONField(default=dict)
    date = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True)

    __error_code__ = 'CONFIG_NOT_FOUND'

    @transaction.atomic()
    def save(self, *args, **kwargs):
        """Saving config and updating config groups"""

        def update(origin, renovator):
            """
            Updating the original dictionary with a check for the presence of keys in the original
            """
            for key, value in renovator.items():
                if key not in origin:
                    continue
                if isinstance(value, Mapping):
                    origin[key] = update(origin.get(key, {}), value)
                else:
                    origin[key] = value
            return origin

        obj = self.obj_ref.object
        if isinstance(obj, (Cluster, ClusterObject, ServiceComponent, HostProvider)):
            # Sync group configs with object config
            for cg in obj.group_config.all():
                diff = cg.get_group_config()
                group_config = ConfigLog()
                current_group_config = ConfigLog.objects.get(id=cg.config.current)
                group_config.obj_ref = cg.config
                config = deepcopy(self.config)
                update(config, diff)
                group_config.config = config
                attr = deepcopy(self.attr)
                group_keys, custom_group_keys = cg.create_group_keys(
                    self.config, cg.get_config_spec()
                )
                attr.update({'group_keys': group_keys, 'custom_group_keys': custom_group_keys})
                update(attr, current_group_config.attr)
                group_config.attr = attr
                group_config.description = current_group_config.description
                group_config.save()
                cg.config.previous = cg.config.current
                cg.config.current = group_config.id
                cg.config.save()
        if isinstance(obj, GroupConfig):
            # `custom_group_keys` read only field in attr,
            # needs to be replaced when creating an object with ORM
            # for api it is checked in /cm/adcm_config.py:check_custom_group_keys_attr()
            _, custom_group_keys = obj.create_group_keys(self.config, obj.get_config_spec())
            self.attr.update({'custom_group_keys': custom_group_keys})

        super().save(*args, **kwargs)


class ADCMEntity(ADCMModel):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    config = models.OneToOneField(ObjectConfig, on_delete=models.CASCADE, null=True)
    state = models.CharField(max_length=64, default='created')
    _multi_state = models.JSONField(default=dict, db_column='multi_state')
    concerns = models.ManyToManyField('ConcernItem', blank=True, related_name='%(class)s_entities')

    class Meta:
        abstract = True

    @property
    def locked(self) -> bool:
        """Check if actions could be run over entity"""
        return self.concerns.filter(blocking=True).exists()

    def add_to_concerns(self, item: 'ConcernItem') -> None:
        """Attach entity to ConcernItem to keep up with it"""
        if not item or getattr(item, 'id', None) is None:
            return

        if item in self.concerns.all():
            return

        self.concerns.add(item)

    def remove_from_concerns(self, item: 'ConcernItem') -> None:
        """Detach entity from ConcernItem when it outdated"""
        if not item or not hasattr(item, 'id'):
            return

        if item not in self.concerns.all():
            return

        self.concerns.remove(item)

    def get_own_issue(self, issue_type: 'IssueType') -> Optional['ConcernItem']:
        """Get object's issue of specified type or None"""
        issue_name = issue_type.gen_issue_name(self)
        for issue in self.concerns.filter(type=ConcernType.Issue, name=issue_name):
            return issue

    @property
    def display_name(self):
        """Unified `display name` for object's string representation"""
        own_name = getattr(self, 'name', None)
        fqdn = getattr(self, 'fqdn', None)
        return own_name or fqdn or self.prototype.display_name or self.prototype.name

    def __str__(self):
        own_name = getattr(self, 'name', None)
        fqdn = getattr(self, 'fqdn', None)
        name = own_name or fqdn or self.prototype.name
        return f'{self.prototype.type} #{self.id} "{name}"'

    def set_state(self, state: str, event=None) -> None:
        self.state = state or self.state
        self.save()
        if event:
            event.set_object_state(self.prototype.type, self.id, state)
        log.info('set %s state to "%s"', self, state)

    def get_id_chain(self) -> dict:
        """
        Get object ID chain for front-end URL generation in message templates
        result looks like {'cluster': 12, 'service': 34, 'component': 45}
        """
        ids = {}
        ids[self.prototype.type] = self.pk
        for attr in ['cluster', 'service', 'provider']:
            value = getattr(self, attr, None)
            if value:
                ids[attr] = value.pk

        return ids

    @property
    def multi_state(self) -> List[str]:
        """Easy to operate self._multi_state representation"""
        return sorted(self._multi_state.keys())

    def set_multi_state(self, multi_state: str, event=None) -> None:
        """Append new unique multi_state to entity._multi_state"""
        if multi_state in self._multi_state:
            return

        self._multi_state.update({multi_state: 1})
        self.save()
        if event:
            event.change_object_multi_state(self.prototype.type, self.id, multi_state)
        log.info('add "%s" to "%s" multi_state', multi_state, self)

    def unset_multi_state(self, multi_state: str, event=None) -> None:
        """Remove specified multi_state from entity._multi_state"""
        if multi_state not in self._multi_state:
            return

        del self._multi_state[multi_state]
        self.save()
        if event:
            event.change_object_multi_state(self.prototype.type, self.id, multi_state)
        log.info('remove "%s" from "%s" multi_state', multi_state, self)

    def has_multi_state_intersection(self, multi_states: List[str]) -> bool:
        """Check if entity._multi_state has an intersection with list of multi_states"""
        return bool(set(self._multi_state).intersection(multi_states))


class ADCM(ADCMEntity):
    name = models.CharField(max_length=16, choices=(('ADCM', 'ADCM'),), unique=True)

    @property
    def bundle_id(self):
        return self.prototype.bundle_id

    @property
    def serialized_issue(self):
        result = {
            'id': self.id,
            'name': self.name,
            'issue': self.issue,
        }
        return result if result['issue'] else {}


class Cluster(ADCMEntity):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    group_config = GenericRelation(
        'GroupConfig',
        object_id_field='object_id',
        content_type_field='object_type',
        on_delete=models.CASCADE,
    )

    __error_code__ = 'CLUSTER_NOT_FOUND'

    @property
    def bundle_id(self):
        return self.prototype.bundle_id

    @property
    def edition(self):
        return self.prototype.bundle.edition

    @property
    def license(self):
        return self.prototype.bundle.license

    def __str__(self):
        return f'{self.name} ({self.id})'

    @property
    def serialized_issue(self):
        result = {
            'id': self.id,
            'name': self.name,
            'issue': self.issue,
        }
        return result if result['issue'] else {}


class HostProvider(ADCMEntity):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    group_config = GenericRelation(
        'GroupConfig',
        object_id_field='object_id',
        content_type_field='object_type',
        on_delete=models.CASCADE,
    )

    __error_code__ = 'PROVIDER_NOT_FOUND'

    @property
    def bundle_id(self):
        return self.prototype.bundle_id

    @property
    def edition(self):
        return self.prototype.bundle.edition

    @property
    def license(self):
        return self.prototype.bundle.license

    def __str__(self):
        return str(self.name)

    @property
    def serialized_issue(self):
        result = {
            'id': self.id,
            'name': self.name,
            'issue': self.issue,
        }
        return result if result['issue'] else {}


class Host(ADCMEntity):
    fqdn = models.CharField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    provider = models.ForeignKey(HostProvider, on_delete=models.CASCADE, null=True, default=None)
    cluster = models.ForeignKey(Cluster, on_delete=models.SET_NULL, null=True, default=None)

    __error_code__ = 'HOST_NOT_FOUND'

    @property
    def bundle_id(self):
        return self.prototype.bundle_id

    @property
    def monitoring(self):
        return self.prototype.monitoring

    def __str__(self):
        return f"{self.fqdn}"

    @property
    def serialized_issue(self):
        result = {'id': self.id, 'name': self.fqdn, 'issue': self.issue.copy()}
        provider_issue = self.provider.serialized_issue
        if provider_issue:
            result['issue']['provider'] = provider_issue
        return result if result['issue'] else {}


class ClusterObject(ADCMEntity):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    service = models.ForeignKey("self", on_delete=models.CASCADE, null=True, default=None)
    group_config = GenericRelation(
        'GroupConfig',
        object_id_field='object_id',
        content_type_field='object_type',
        on_delete=models.CASCADE,
    )

    __error_code__ = 'CLUSTER_SERVICE_NOT_FOUND'

    @property
    def bundle_id(self):
        return self.prototype.bundle_id

    @property
    def version(self):
        return self.prototype.version

    @property
    def name(self):
        return self.prototype.name

    @property
    def description(self):
        return self.prototype.description

    @property
    def monitoring(self):
        return self.prototype.monitoring

    @property
    def serialized_issue(self):
        result = {
            'id': self.id,
            'name': self.display_name,
            'issue': self.issue,
        }
        return result if result['issue'] else {}

    class Meta:
        unique_together = (('cluster', 'prototype'),)


class ServiceComponent(ADCMEntity):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    service = models.ForeignKey(ClusterObject, on_delete=models.CASCADE)
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE, null=True, default=None)
    group_config = GenericRelation(
        'GroupConfig',
        object_id_field='object_id',
        content_type_field='object_type',
        on_delete=models.CASCADE,
    )

    __error_code__ = 'COMPONENT_NOT_FOUND'

    @property
    def name(self):
        return self.prototype.name

    @property
    def description(self):
        return self.prototype.description

    @property
    def constraint(self):
        return self.prototype.constraint

    @property
    def requires(self):
        return self.prototype.requires

    @property
    def bound_to(self):
        return self.prototype.bound_to

    @property
    def monitoring(self):
        return self.prototype.monitoring

    @property
    def serialized_issue(self):
        result = {
            'id': self.id,
            'name': self.display_name,
            'issue': self.issue,
        }
        return result if result['issue'] else {}

    class Meta:
        unique_together = (('cluster', 'service', 'prototype'),)


class GroupConfig(ADCMModel):
    object_id = models.PositiveIntegerField()
    object_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object = GenericForeignKey('object_type', 'object_id')
    name = models.CharField(max_length=30)
    description = models.TextField(blank=True)
    hosts = models.ManyToManyField(Host, blank=True, related_name='group_config')
    config = models.OneToOneField(
        ObjectConfig, on_delete=models.CASCADE, null=False, related_name='group_config'
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
            field_spec = {'type': field.type, 'group_customization': group_customization}
            if field.subname == '':
                if field.type == 'group':
                    field_spec.update({'fields': {}})
                spec[field.name] = field_spec
            else:
                spec[field.name]['fields'][field.subname] = field_spec
        return spec

    def create_group_keys(
        self,
        config: dict,
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
        for k in config.keys():
            if config_spec[k]['type'] == 'group':
                group_keys.setdefault(k, {})
                custom_group_keys.setdefault(k, {})
                self.create_group_keys(
                    config.get(k, {}), config_spec[k]['fields'], group_keys[k], custom_group_keys[k]
                )
            else:
                group_keys[k] = False
                custom_group_keys[k] = config_spec[k]['group_customization']
        return group_keys, custom_group_keys

    def get_group_config(self):
        def get_diff(config, group_keys, diff=None):
            if diff is None:
                diff = {}
            for k, v in group_keys.items():
                if isinstance(v, Mapping):
                    diff.setdefault(k, {})
                    get_diff(config[k], group_keys[k], diff[k])
                    if not diff[k]:
                        diff.pop(k)
                else:
                    if v:
                        diff[k] = config[k]
            return diff

        cl = ConfigLog.obj.get(id=self.config.current)
        config = cl.config
        group_keys = cl.attr.get('group_keys', {})
        return get_diff(config, group_keys)

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

    @transaction.atomic()
    def save(self, *args, **kwargs):
        obj = self.object_type.model_class().obj.get(id=self.object_id)
        if self._state.adding:
            if obj.config is not None:
                parent_config_log = ConfigLog.obj.get(id=obj.config.current)
                self.config = ObjectConfig.objects.create(current=0, previous=0)
                config_log = ConfigLog()
                config_log.obj_ref = self.config
                config_log.config = deepcopy(parent_config_log.config)
                attr = deepcopy(parent_config_log.attr)
                config_spec = self.get_config_spec()
                group_keys, custom_group_keys = self.create_group_keys(
                    config_log.config, config_spec
                )
                attr.update({'group_keys': group_keys, 'custom_group_keys': custom_group_keys})
                config_log.attr = attr
                config_log.description = parent_config_log.description
                config_log.save()
                self.config.current = config_log.pk
                self.config.save()
        super().save(*args, **kwargs)


@receiver(m2m_changed, sender=GroupConfig.hosts.through)
def verify_host_candidate_for_group_config(sender, **kwargs):
    """Checking host candidate for group config before add to group"""
    group_config = kwargs.get('instance')
    action = kwargs.get('action')
    host_ids = kwargs.get('pk_set')

    if action == 'pre_add':
        for host_id in host_ids:
            host = Host.objects.get(id=host_id)
            group_config.check_host_candidate(host)


ACTION_TYPE = (
    ('task', 'task'),
    ('job', 'job'),
)

SCRIPT_TYPE = (
    ('ansible', 'ansible'),
    ('task_generator', 'task_generator'),
)


class AbstractAction(ADCMModel):
    """Abstract base class for both Action and StageAction"""

    prototype = None

    name = models.CharField(max_length=160)
    display_name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    ui_options = models.JSONField(default=dict)

    type = models.CharField(max_length=16, choices=ACTION_TYPE)
    button = models.CharField(max_length=64, default=None, null=True)

    script = models.CharField(max_length=160)
    script_type = models.CharField(max_length=16, choices=SCRIPT_TYPE)

    state_available = models.JSONField(default=list)
    state_unavailable = models.JSONField(default=list)
    state_on_success = models.CharField(max_length=64, blank=True)
    state_on_fail = models.CharField(max_length=64, blank=True)

    multi_state_available = models.JSONField(default=list)
    multi_state_unavailable = models.JSONField(default=list)
    multi_state_on_success_set = models.JSONField(default=list)
    multi_state_on_success_unset = models.JSONField(default=list)
    multi_state_on_fail_set = models.JSONField(default=list)
    multi_state_on_fail_unset = models.JSONField(default=list)

    params = models.JSONField(default=dict)
    log_files = models.JSONField(default=list)

    hostcomponentmap = models.JSONField(default=list)
    allow_to_terminate = models.BooleanField(default=False)
    partial_execution = models.BooleanField(default=False)
    host_action = models.BooleanField(default=False)

    class Meta:
        abstract = True
        unique_together = (('prototype', 'name'),)

    def __str__(self):
        return f"{self.prototype} {self.display_name or self.name}"


class Action(AbstractAction):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)

    __error_code__ = 'ACTION_NOT_FOUND'

    @property
    def prototype_name(self):
        return self.prototype.name

    @property
    def prototype_version(self):
        return self.prototype.version

    @property
    def prototype_type(self):
        return self.prototype.type

    def get_id_chain(self, target_ids: dict) -> dict:
        """Get action ID chain for front-end URL generation in message templates"""
        target_ids['action'] = self.pk
        result = {
            'type': self.prototype.type + '_action_run',
            'name': self.display_name or self.name,
            'ids': target_ids,
        }
        return result

    def allowed(self, obj: ADCMEntity) -> bool:
        """Check if action is allowed to be run on object"""
        if isinstance(self.state_unavailable, list) and obj.state in self.state_unavailable:
            return False

        if isinstance(self.multi_state_unavailable, list) and obj.has_multi_state_intersection(
            self.multi_state_unavailable
        ):
            return False

        state_allowed = False
        if self.state_available == 'any':
            state_allowed = True
        elif isinstance(self.state_available, list) and obj.state in self.state_available:
            state_allowed = True

        multi_state_allowed = False
        if self.multi_state_available == 'any':
            multi_state_allowed = True
        elif isinstance(self.multi_state_available, list) and obj.has_multi_state_intersection(
            self.multi_state_available
        ):
            multi_state_allowed = True

        return state_allowed and multi_state_allowed


class SubAction(ADCMModel):
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    display_name = models.CharField(max_length=160, blank=True)
    script = models.CharField(max_length=160)
    script_type = models.CharField(max_length=16, choices=SCRIPT_TYPE)
    state_on_fail = models.CharField(max_length=64, blank=True)
    params = models.JSONField(default=dict)


class HostComponent(ADCMModel):
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
    ('secrettext', 'secrettext'),
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


class PrototypeConfig(ADCMModel):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE, null=True, default=None)
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


class PrototypeExport(ADCMModel):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)

    class Meta:
        unique_together = (('prototype', 'name'),)


class PrototypeImport(ADCMModel):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
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


class ClusterBind(ADCMModel):
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
        default=None,
    )

    __error_code__ = 'BIND_NOT_FOUND'

    class Meta:
        unique_together = (('cluster', 'service', 'source_cluster', 'source_service'),)


JOB_STATUS = (
    ('created', 'created'),
    ('running', 'running'),
    ('success', 'success'),
    ('failed', 'failed'),
)


class UserProfile(ADCMModel):
    login = models.CharField(max_length=32, unique=True)
    profile = models.JSONField(default=str)


class Role(ADCMModel):
    name = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    user = models.ManyToManyField(User, blank=True)
    group = models.ManyToManyField(Group, blank=True)


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

        reason = MessageTemplate.get_message_from_template(
            MessageTemplate.KnownNames.LockedByAction.value,
            action=self.action,
            target=self.task_object,
        )
        self.lock = ConcernItem.objects.create(
            type=ConcernType.Lock.value, name=None, reason=reason, blocking=True
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


class StageAction(AbstractAction):
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)


class StageSubAction(ADCMModel):
    action = models.ForeignKey(StageAction, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    display_name = models.CharField(max_length=160, blank=True)
    script = models.CharField(max_length=160)
    script_type = models.CharField(max_length=16, choices=SCRIPT_TYPE)
    state_on_fail = models.CharField(max_length=64, blank=True)
    params = models.JSONField(default=dict)


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


class DummyData(ADCMModel):
    date = models.DateTimeField(auto_now=True)


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
        LockedByAction = 'locked by action on target'  # kwargs=(action, target)
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


class IssueType(Enum):
    Config = 'config'
    RequiredService = 'required_service'
    RequiredImport = 'required_import'
    HostComponent = 'host_component'

    def gen_issue_name(self, obj: ADCMEntity) -> str:
        """Generate unique issue name for object"""
        return f'{self.name} issue on {obj.prototype.type} {obj.pk}'


class ConcernType(models.TextChoices):
    Lock = 'lock', 'lock'
    Issue = 'issue', 'issue'
    Flag = 'flag', 'flag'


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
    `related_objects` are back-refs from affected ADCMEntities.concerns
    """

    type = models.CharField(max_length=8, choices=ConcernType.choices, default=ConcernType.Lock)
    name = models.CharField(max_length=160, null=True, unique=True)
    reason = models.JSONField(default=dict)
    blocking = models.BooleanField(default=True)

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
