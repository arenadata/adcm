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

from itertools import chain
from typing import Iterable, List, Optional

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from cm.errors import AdcmEx
from cm.logger import log
from cm.models.types import ActionType, ConcernCause, ConcernType, LICENSE_STATE, MONITORING_TYPE, PROTO_TYPE, \
    PrototypeEnum, SCRIPT_TYPE
from cm.models.utils import get_any, get_default_constraint, get_default_from_edition


class ADCMManager(models.Manager):
    """
    Custom model manager catch ObjectDoesNotExist error and re-raise it as custom
    AdcmEx exception. AdcmEx is derived from DRF APIException, so it handled gracefully
    by DRF and is reported out as nicely formatted error instead of ugly exception.

    Using ADCMManager can shorten you code significantly. Instead of

    try:
        cluster = Cluster.objects.get(id=id)
    except Cluster.DoesNotExist:
        raise AdcmEx(f'Cluster {id} is not found')

    You can just write

    cluster = Cluster.obj.get(id=id)

    and DRF magic do the rest.

    Please pay attention, to use ADCMManager you need refer to "obj" model attribute,
    not "objects". "objects" attribute is referred to standard Django model manager,
    so if you need familiar behavior you can use it as usual.
    """

    def get(self, *args, **kwargs):
        try:
            return super().get(*args, **kwargs)
        except (ObjectDoesNotExist, ValueError, TypeError):
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
    category = models.ForeignKey('ProductCategory', on_delete=models.RESTRICT, null=True)

    __error_code__ = 'BUNDLE_NOT_FOUND'

    class Meta:
        unique_together = (('name', 'version', 'edition'),)


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
    venv = models.CharField(default="default", max_length=160, blank=False)
    allow_maintenance_mode = models.BooleanField(default=False)

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


class ADCMEntity(ADCMModel):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    config = models.OneToOneField(ObjectConfig, on_delete=models.CASCADE, null=True)
    state = models.CharField(max_length=64, default='created')
    _multi_state = models.JSONField(default=dict, db_column='multi_state')
    concerns = models.ManyToManyField('ConcernItem', blank=True, related_name='%(class)s_entities')
    policy_object = GenericRelation('rbac.PolicyObject')

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
        """Detach entity from ConcernItem when it is outdated"""
        if not item or not hasattr(item, 'id'):
            return

        if item not in self.concerns.all():
            return

        self.concerns.remove(item)

    def get_own_issue(self, cause: 'ConcernCause') -> Optional['ConcernItem']:
        """Get object's issue of specified cause or None"""
        return self.concerns.filter(
            type=ConcernType.Issue, owner_id=self.pk, owner_type=self.content_type, cause=cause
        ).first()

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
        ids = {self.prototype.type: self.pk}
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

    @property
    def content_type(self):
        model_name = self.__class__.__name__.lower()
        return ContentType.objects.get(app_label='cm', model=model_name)

    def delete(self, using=None, keep_parents=False):
        super().delete(using, keep_parents)
        if self.config is not None:
            self.config.delete()


class ProductCategory(ADCMModel):
    """
    Categories are used for some models' categorization.
    It's same as Bundle.name but unlinked from it due to simplicity reasons.
    """

    value = models.CharField(max_length=160, unique=True)
    visible = models.BooleanField(default=True)

    @classmethod
    def re_collect(cls) -> None:
        """Re-sync category list with installed bundles"""
        for bundle in Bundle.objects.filter(category=None).all():
            prototype = Prototype.objects.filter(
                bundle=bundle, name=bundle.name, type=PrototypeEnum.Cluster.value
            ).first()
            if prototype:
                value = prototype.display_name or bundle.name
                bundle.category, _ = cls.objects.get_or_create(value=value)
                bundle.save()
        for category in cls.objects.all():
            if category.bundle_set.count() == 0:
                category.delete()  # TODO: ensure that's enough


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
    action = models.OneToOneField('Action', on_delete=models.CASCADE, null=True)

    __error_code__ = 'UPGRADE_NOT_FOUND'


class AbstractAction(ADCMModel):
    """Abstract base class for both Action and StageAction"""

    prototype = None

    name = models.CharField(max_length=160)
    display_name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    ui_options = models.JSONField(default=dict)

    type = models.CharField(max_length=16, choices=ActionType.choices)
    button = models.CharField(max_length=64, default=None, null=True)

    script = models.CharField(max_length=160)
    script_type = models.CharField(max_length=16, choices=SCRIPT_TYPE)

    state_available = models.JSONField(default=list)
    state_unavailable = models.JSONField(default=list)
    state_on_success = models.CharField(max_length=64, blank=True)
    state_on_fail = models.CharField(max_length=64, blank=True)

    multi_state_available = models.JSONField(default=get_any)
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
    allow_in_maintenance_mode = models.BooleanField(default=False)

    _venv = models.CharField(default="default", db_column="venv", max_length=160, blank=False)

    @property
    def venv(self):
        """Property which return a venv for ansible to run.

        Bundle developer could mark one action with exact venv he needs,
        or mark all actions on prototype.
        """
        if self._venv == "default":
            if self.prototype is not None:
                return self.prototype.venv
        return self._venv

    @venv.setter
    def venv(self, value: str):
        self._venv = value

    class Meta:
        abstract = True
        unique_together = (('prototype', 'name'),)

    def __str__(self):
        return f"{self.prototype} {self.display_name or self.name}"


class AbstractSubAction(ADCMModel):
    action = None

    name = models.CharField(max_length=160)
    display_name = models.CharField(max_length=160, blank=True)
    script = models.CharField(max_length=160)
    script_type = models.CharField(max_length=16, choices=SCRIPT_TYPE)
    state_on_fail = models.CharField(max_length=64, blank=True)
    multi_state_on_fail_set = models.JSONField(default=list)
    multi_state_on_fail_unset = models.JSONField(default=list)
    params = models.JSONField(default=dict)

    class Meta:
        abstract = True


class DummyData(ADCMModel):
    date = models.DateTimeField(auto_now=True)


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