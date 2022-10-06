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
from collections.abc import Mapping
from copy import deepcopy
from enum import Enum
from itertools import chain
from typing import Dict, Iterable, List, Optional

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models, transaction
from django.db.models.signals import m2m_changed, post_delete
from django.dispatch import receiver
from django.utils import timezone

from cm.config import FILE_DIR, Job
from cm.errors import AdcmEx
from cm.logger import logger


def validate_line_break_character(value: str) -> None:
    """Check line break character in CharField"""
    if len(value.splitlines()) > 1:
        raise ValidationError("the string field contains a line break character")


class ObjectType(models.TextChoices):
    ADCM = "adcm", "adcm"
    Cluster = "cluster", "cluster"
    Service = "service", "service"
    Component = "component", "component"
    Provider = "provider", "provider"
    Host = "host", "host"


LICENSE_STATE = (
    ("absent", "absent"),
    ("accepted", "accepted"),
    ("unaccepted", "unaccepted"),
)


def get_model_by_type(object_type):
    if object_type == "adcm":
        return ADCM
    if object_type == "cluster":
        return Cluster
    elif object_type == "provider":
        return HostProvider
    elif object_type == "service":
        return ClusterObject
    elif object_type == "component":
        return ServiceComponent
    elif object_type == "host":
        return Host
    else:
        # This function should return a Model, this is necessary for the correct
        # construction of the schema.
        return Cluster


def get_object_cluster(obj):
    if isinstance(obj, Cluster):
        return obj
    if hasattr(obj, "cluster"):
        return obj.cluster
    else:
        return None


def get_default_before_upgrade() -> dict:
    """Return init value for before upgrade"""
    return {"state": None}


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
        except (ObjectDoesNotExist, ValueError, TypeError):
            if not hasattr(self.model, "__error_code__"):
                raise AdcmEx("NO_MODEL_ERROR_CODE", f"model: {self.model.__name__}") from None
            msg = f"{self.model.__name__} {kwargs} does not exist"
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
            not_changeable_fields = getattr(self, "not_changeable_fields", ())
            for field_name in not_changeable_fields:
                if isinstance(getattr(self, field_name), models.Model):
                    field_name = f"{field_name}_id"
                if getattr(self, field_name) != self._loaded_values[field_name]:
                    raise AdcmEx(
                        "NOT_CHANGEABLE_FIELDS",
                        f'{", ".join(not_changeable_fields)} fields cannot be changed',
                    )
        super().save(*args, **kwargs)


class Bundle(ADCMModel):
    name = models.CharField(max_length=160)
    version = models.CharField(max_length=80)
    version_order = models.PositiveIntegerField(default=0)
    edition = models.CharField(max_length=80, default="community")
    license = models.CharField(max_length=16, choices=LICENSE_STATE, default="absent")
    license_path = models.CharField(max_length=160, default=None, null=True)
    license_hash = models.CharField(max_length=64, default=None, null=True)
    hash = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    date = models.DateTimeField(auto_now=True)
    category = models.ForeignKey("ProductCategory", on_delete=models.RESTRICT, null=True)

    __error_code__ = "BUNDLE_NOT_FOUND"

    class Meta:
        unique_together = (("name", "version", "edition"),)


class ProductCategory(ADCMModel):
    """
    Categories are used for some models categorization.
    It's same as Bundle.name but unlinked from it due to simplicity reasons.
    """

    value = models.CharField(max_length=160, unique=True)
    visible = models.BooleanField(default=True)

    @classmethod
    def re_collect(cls) -> None:
        """Re-sync category list with installed bundles"""
        for bundle in Bundle.objects.filter(category=None).all():
            prototype = Prototype.objects.filter(
                bundle=bundle, name=bundle.name, type=ObjectType.Cluster
            ).first()
            if prototype:
                value = prototype.display_name or bundle.name
                bundle.category, _ = cls.objects.get_or_create(value=value)
                bundle.save()
        for category in cls.objects.all():
            if category.bundle_set.count() == 0:
                category.delete()  # TODO: ensure that's enough


def get_default_from_edition():
    return ["community"]


MONITORING_TYPE = (
    ("active", "active"),
    ("passive", "passive"),
)


def get_default_constraint():
    return [0, "+"]


class Prototype(ADCMModel):
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE)
    type = models.CharField(max_length=16, choices=ObjectType.choices)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, default=None)
    path = models.CharField(max_length=160, default="")
    name = models.CharField(max_length=256)
    display_name = models.CharField(max_length=256, blank=True)
    version = models.CharField(max_length=80)
    version_order = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=False)
    shared = models.BooleanField(default=False)
    constraint = models.JSONField(default=get_default_constraint)
    requires = models.JSONField(default=list)
    bound_to = models.JSONField(default=dict)
    adcm_min_version = models.CharField(max_length=80, default=None, null=True)
    monitoring = models.CharField(max_length=16, choices=MONITORING_TYPE, default="active")
    description = models.TextField(blank=True)
    config_group_customization = models.BooleanField(default=False)
    venv = models.CharField(default="default", max_length=160, blank=False)
    allow_maintenance_mode = models.BooleanField(default=False)

    __error_code__ = "PROTOTYPE_NOT_FOUND"

    def __str__(self):
        return str(self.name)

    class Meta:
        unique_together = (("bundle", "type", "parent", "name", "version"),)


class ObjectConfig(ADCMModel):
    current = models.PositiveIntegerField()
    previous = models.PositiveIntegerField()

    __error_code__ = "CONFIG_NOT_FOUND"

    @property
    def object(self):
        """Returns object for ObjectConfig"""
        object_types = [
            "adcm",
            "cluster",
            "clusterobject",
            "servicecomponent",
            "hostprovider",
            "host",
            "group_config",
        ]
        for object_type in object_types:
            if hasattr(self, object_type):
                obj = getattr(self, object_type)
                return obj
        return None


def deep_merge(origin: dict, renovator: Mapping):
    """
    Merge renovator into origin

    >>> o = {'a': 1, 'b': {'c': 1, 'd': 1}}
    >>> r = {'a': 1, 'b': {'c': 2 }}
    >>> deep_merge(o, r) == {'a': 1, 'b': {'c': 2, 'd': 1}}
    """

    for key, value in renovator.items():
        if isinstance(value, Mapping):
            node = origin.setdefault(key, {})
            deep_merge(node, value)
        else:
            origin[key] = value
    return origin


class ConfigLog(ADCMModel):
    obj_ref = models.ForeignKey(ObjectConfig, on_delete=models.CASCADE)
    config = models.JSONField(default=dict)
    attr = models.JSONField(default=dict)
    date = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True)

    __error_code__ = "CONFIG_NOT_FOUND"

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
                        update_config(origin[key], renovator[key], group_keys[key]["fields"])
                    else:
                        if value:
                            origin[key] = renovator[key]

        def update_attr(origin: dict, renovator: dict, group_keys: dict) -> None:
            """
            Updating the original config with a check for the presence of keys in the original
            """
            for key, value in group_keys.items():
                if key in renovator and isinstance(value, Mapping):
                    if value["value"] is not None and value["value"]:
                        origin[key] = renovator[key]

        def clean_attr(attrs: dict, spec: dict) -> None:
            """Clean attr after upgrade cluster"""
            extra_fields = []

            for key in attrs.keys():
                if key not in ["group_keys", "custom_group_keys"]:
                    if key not in spec:
                        extra_fields.append(key)

            for field in extra_fields:
                attrs.pop(field)

        def clean_group_keys(group_keys, spec):
            """Clean group_keys after update cluster"""
            correct_group_keys = {}
            for field, info in spec.items():
                if info["type"] == "group":
                    correct_group_keys[field] = {}
                    correct_group_keys[field]["value"] = group_keys[field]["value"]
                    correct_group_keys[field]["fields"] = {}
                    for key in info["fields"].keys():
                        correct_group_keys[field]["fields"][key] = group_keys[field]["fields"][key]
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
                current_group_keys = current_group_config.attr["group_keys"]
                update_config(config, diff_config, current_group_keys)
                group_config.config = config
                attr = deepcopy(self.attr)
                update_attr(attr, diff_attr, current_group_keys)
                spec = cg.get_config_spec()
                group_keys, custom_group_keys = cg.create_group_keys(spec)
                group_keys = deep_merge(group_keys, current_group_keys)
                group_keys = clean_group_keys(group_keys, spec)
                attr["group_keys"] = group_keys
                attr["custom_group_keys"] = custom_group_keys
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
            self.attr.update({"custom_group_keys": custom_group_keys})

        super().save(*args, **kwargs)


class ADCMEntity(ADCMModel):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    config = models.OneToOneField(ObjectConfig, on_delete=models.CASCADE, null=True)
    state = models.CharField(max_length=64, default="created")
    _multi_state = models.JSONField(default=dict, db_column="multi_state")
    concerns = models.ManyToManyField("ConcernItem", blank=True, related_name="%(class)s_entities")
    policy_object = GenericRelation("rbac.PolicyObject")

    class Meta:
        abstract = True

    @property
    def locked(self) -> bool:
        """Check if actions could be run over entity"""
        return self.concerns.filter(blocking=True).exists()

    def add_to_concerns(self, item: "ConcernItem") -> None:
        """Attach entity to ConcernItem to keep up with it"""
        if not item or getattr(item, "id", None) is None:
            return

        if item in self.concerns.all():
            return

        self.concerns.add(item)

    def remove_from_concerns(self, item: "ConcernItem") -> None:
        """Detach entity from ConcernItem when it outdated"""
        if not item or not hasattr(item, "id"):
            return

        if item not in self.concerns.all():
            return

        self.concerns.remove(item)

    def get_own_issue(self, cause: "ConcernCause") -> Optional["ConcernItem"]:
        """Get object's issue of specified cause or None"""
        return self.concerns.filter(
            type=ConcernType.Issue, owner_id=self.pk, owner_type=self.content_type, cause=cause
        ).first()

    def __str__(self):
        own_name = getattr(self, "name", None)
        fqdn = getattr(self, "fqdn", None)
        name = own_name or fqdn or self.prototype.name
        return f'{self.prototype.type} #{self.id} "{name}"'

    def set_state(self, state: str, event=None) -> None:
        self.state = state or self.state
        self.save()
        if event:
            event.set_object_state(self.prototype.type, self.id, state)
        logger.info('set %s state to "%s"', self, state)

    def get_id_chain(self) -> dict:
        """
        Get object ID chain for front-end URL generation in message templates
        result looks like {'cluster': 12, 'service': 34, 'component': 45}
        """
        ids = {}
        ids[self.prototype.type] = self.pk
        for attr in ["cluster", "service", "provider"]:
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
        logger.info('add "%s" to "%s" multi_state', multi_state, self)

    def unset_multi_state(self, multi_state: str, event=None) -> None:
        """Remove specified multi_state from entity._multi_state"""
        if multi_state not in self._multi_state:
            return

        del self._multi_state[multi_state]
        self.save()
        if event:
            event.change_object_multi_state(self.prototype.type, self.id, multi_state)
        logger.info('remove "%s" from "%s" multi_state', multi_state, self)

    def has_multi_state_intersection(self, multi_states: List[str]) -> bool:
        """Check if entity._multi_state has an intersection with list of multi_states"""
        return bool(set(self._multi_state).intersection(multi_states))

    @property
    def content_type(self):
        model_name = self.__class__.__name__.lower()
        return ContentType.objects.get(app_label="cm", model=model_name)

    def delete(self, using=None, keep_parents=False):
        super().delete(using, keep_parents)
        if self.config is not None and not isinstance(self, ServiceComponent):
            self.config.delete()


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
    action = models.OneToOneField("Action", on_delete=models.CASCADE, null=True)

    __error_code__ = "UPGRADE_NOT_FOUND"

    def allowed(self, obj: ADCMEntity) -> bool:
        """Check if upgrade is allowed to be run on object"""
        if self.state_available:
            available = self.state_available
            if obj.state in available:
                return True
            elif available == "any":
                return True
            else:
                return False
        else:
            return self.action.allowed(obj)


class ADCM(ADCMEntity):
    name = models.CharField(max_length=16, choices=(("ADCM", "ADCM"),), unique=True)

    @property
    def bundle_id(self):
        return self.prototype.bundle_id

    @property
    def display_name(self):
        return self.name

    @property
    def serialized_issue(self):
        result = {
            "id": self.id,
            "name": self.name,
            "issue": self.issue,
        }
        return result if result["issue"] else {}


class Cluster(ADCMEntity):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    group_config = GenericRelation(
        "GroupConfig",
        object_id_field="object_id",
        content_type_field="object_type",
        on_delete=models.CASCADE,
    )
    before_upgrade = models.JSONField(default=get_default_before_upgrade)

    __error_code__ = "CLUSTER_NOT_FOUND"

    @property
    def bundle_id(self):
        return self.prototype.bundle_id

    @property
    def edition(self):
        return self.prototype.bundle.edition

    @property
    def license(self):
        return self.prototype.bundle.license

    @property
    def display_name(self):
        return self.name

    @property
    def serialized_issue(self):
        result = {
            "id": self.id,
            "name": self.name,
            "issue": self.issue,
        }
        return result if result["issue"] else {}


class HostProvider(ADCMEntity):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    group_config = GenericRelation(
        "GroupConfig",
        object_id_field="object_id",
        content_type_field="object_type",
        on_delete=models.CASCADE,
    )
    before_upgrade = models.JSONField(default=get_default_before_upgrade)

    __error_code__ = "PROVIDER_NOT_FOUND"

    @property
    def bundle_id(self):
        return self.prototype.bundle_id

    @property
    def edition(self):
        return self.prototype.bundle.edition

    @property
    def license(self):
        return self.prototype.bundle.license

    @property
    def display_name(self):
        return self.name

    @property
    def serialized_issue(self):
        result = {
            "id": self.id,
            "name": self.name,
            "issue": self.issue,
        }
        return result if result["issue"] else {}


class Host(ADCMEntity):
    fqdn = models.CharField(max_length=253, unique=True)
    description = models.TextField(blank=True)
    provider = models.ForeignKey(HostProvider, on_delete=models.CASCADE, null=True, default=None)
    cluster = models.ForeignKey(Cluster, on_delete=models.SET_NULL, null=True, default=None)
    maintenance_mode = models.BooleanField(default=False)

    __error_code__ = "HOST_NOT_FOUND"

    @property
    def bundle_id(self):
        return self.prototype.bundle_id

    @property
    def monitoring(self):
        return self.prototype.monitoring

    @property
    def name(self):
        return self.fqdn

    @property
    def display_name(self):
        return self.fqdn

    @property
    def serialized_issue(self):
        result = {"id": self.id, "name": self.fqdn, "issue": self.issue.copy()}
        provider_issue = self.provider.serialized_issue
        if provider_issue:
            result["issue"]["provider"] = provider_issue
        return result if result["issue"] else {}

    @property
    def is_maintenance_mode_available(self) -> bool:
        cluster: Cluster | None = self.cluster
        if not cluster:
            return False
        return cluster.prototype.allow_maintenance_mode


class ClusterObject(ADCMEntity):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    service = models.ForeignKey("self", on_delete=models.CASCADE, null=True, default=None)
    group_config = GenericRelation(
        "GroupConfig",
        object_id_field="object_id",
        content_type_field="object_type",
        on_delete=models.CASCADE,
    )

    __error_code__ = "CLUSTER_SERVICE_NOT_FOUND"

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
    def display_name(self):
        return self.prototype.display_name

    @property
    def description(self):
        return self.prototype.description

    @property
    def monitoring(self):
        return self.prototype.monitoring

    @property
    def serialized_issue(self):
        result = {
            "id": self.id,
            "name": self.display_name,
            "issue": self.issue,
        }
        return result if result["issue"] else {}

    class Meta:
        unique_together = (("cluster", "prototype"),)


class ServiceComponent(ADCMEntity):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    service = models.ForeignKey(ClusterObject, on_delete=models.CASCADE)
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE, null=True, default=None)
    group_config = GenericRelation(
        "GroupConfig",
        object_id_field="object_id",
        content_type_field="object_type",
        on_delete=models.CASCADE,
    )

    __error_code__ = "COMPONENT_NOT_FOUND"

    @property
    def name(self):
        return self.prototype.name

    @property
    def display_name(self):
        return self.prototype.display_name

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
            "id": self.id,
            "name": self.display_name,
            "issue": self.issue,
        }
        return result if result["issue"] else {}

    class Meta:
        unique_together = (("cluster", "service", "prototype"),)


@receiver(post_delete, sender=ServiceComponent)
def auto_delete_config_with_servicecomponent(sender, instance, **kwargs):
    if instance.config is not None:
        instance.config.delete()


class GroupConfig(ADCMModel):
    object_id = models.PositiveIntegerField()
    object_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object = GenericForeignKey("object_type", "object_id")
    name = models.CharField(max_length=30, validators=[validate_line_break_character])
    description = models.TextField(blank=True)
    hosts = models.ManyToManyField(Host, blank=True, related_name="group_config")
    config = models.OneToOneField(
        ObjectConfig, on_delete=models.CASCADE, null=True, related_name="group_config"
    )

    __error_code__ = "GROUP_CONFIG_NOT_FOUND"

    not_changeable_fields = ("id", "object_id", "object_type")

    class Meta:
        unique_together = ["object_id", "name", "object_type"]

    def get_config_spec(self):
        """Return spec for config"""
        spec = {}
        for field in PrototypeConfig.objects.filter(
            prototype=self.object.prototype, action__isnull=True
        ).order_by("id"):
            group_customization = field.group_customization
            if group_customization is None:
                group_customization = self.object.prototype.config_group_customization
            field_spec = {
                "type": field.type,
                "group_customization": group_customization,
                "limits": field.limits,
            }
            if field.subname == "":
                if field.type == "group":
                    field_spec.update({"fields": {}})
                spec[field.name] = field_spec
            else:
                spec[field.name]["fields"][field.subname] = field_spec
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
            if v["type"] == "group":
                value = None
                if "activatable" in v["limits"]:
                    value = False
                group_keys.setdefault(k, {"value": value, "fields": {}})
                custom_group_keys.setdefault(k, {"value": v["group_customization"], "fields": {}})
                self.create_group_keys(
                    v["fields"], group_keys[k]["fields"], custom_group_keys[k]["fields"]
                )
            else:
                group_keys[k] = False
                custom_group_keys[k] = v["group_customization"]
        return group_keys, custom_group_keys

    def get_diff_config_attr(self):
        def get_diff(config, attr, group_keys, diff_config=None, diff_attr=None):
            if diff_config is None:
                diff_config = {}
            if diff_attr is None:
                diff_attr = {}
            for k, v in group_keys.items():
                if isinstance(v, Mapping):
                    if v["value"] is not None and v["value"]:
                        diff_attr[k] = attr[k]
                    diff_config.setdefault(k, {})
                    get_diff(config[k], attr, group_keys[k]["fields"], diff_config[k], diff_attr)
                    if not diff_config[k]:
                        diff_config.pop(k)
                else:
                    if v:
                        diff_config[k] = config[k]
            return diff_config, diff_attr

        cl = ConfigLog.obj.get(id=self.config.current)
        config = cl.config
        attr = cl.attr
        group_keys = cl.attr.get("group_keys", {})
        return get_diff(config, attr, group_keys)

    def get_group_keys(self):
        cl = ConfigLog.objects.get(id=self.config.current)
        return cl.attr.get("group_keys", {})

    def merge_config(self, object_config: dict, group_config: dict, group_keys: dict, config=None):
        """Merge object config with group config based group_keys"""

        if config is None:
            config = {}
        for k, v in group_keys.items():
            if isinstance(v, Mapping):
                config.setdefault(k, {})
                self.merge_config(
                    object_config[k], group_config[k], group_keys[k]["fields"], config[k]
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
                if v["value"]:
                    attr[k] = group_attr[k]
                else:
                    attr[k] = object_attr[k]
        return attr

    def get_config_attr(self):
        """Return attr for group config without group_keys and custom_group_keys params"""
        cl = ConfigLog.obj.get(id=self.config.current)
        attr = {k: v for k, v in cl.attr.items() if k not in ("group_keys", "custom_group_keys")}
        return attr

    def get_config_and_attr(self):
        """Return merge object config with group config and merge attr"""

        object_cl = ConfigLog.objects.get(id=self.object.config.current)
        object_config = object_cl.config
        object_attr = object_cl.attr
        group_cl = ConfigLog.objects.get(id=self.config.current)
        group_config = group_cl.config
        group_keys = group_cl.attr.get("group_keys", {})
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
            raise AdcmEx("GROUP_CONFIG_TYPE_ERROR")
        return hosts.exclude(group_config__in=self.object.group_config.all())

    def check_host_candidate(self, host):
        """Checking host candidate for group"""
        if host not in self.host_candidate():
            raise AdcmEx("GROUP_CONFIG_HOST_ERROR")

    def preparing_file_type_field(self, config=None):
        """Creating file for file type field"""

        if self.config is None:
            return
        if config is None:
            config = ConfigLog.objects.get(id=self.config.current).config
        fields = PrototypeConfig.objects.filter(
            prototype=self.object.prototype, action__isnull=True, type="file"
        ).order_by("id")
        for field in fields:
            filename = ".".join(
                [
                    self.object.prototype.type,
                    str(self.object.id),
                    "group",
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
                if field.name == "ansible_ssh_private_key_file":
                    if value != "":
                        if value[-1] == "-":
                            value += "\n"
                with open(filepath, "w", encoding="utf-8") as f:
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
                attr.update({"group_keys": group_keys, "custom_group_keys": custom_group_keys})
                config_log.attr = attr
                config_log.description = parent_config_log.description
                config_log.save()
                self.config.current = config_log.pk
                self.config.save()
        super().save(*args, **kwargs)
        self.preparing_file_type_field()


@receiver(m2m_changed, sender=GroupConfig.hosts.through)
def verify_host_candidate_for_group_config(sender, **kwargs):
    """Checking host candidate for group config before add to group"""
    group_config = kwargs.get("instance")
    action = kwargs.get("action")
    host_ids = kwargs.get("pk_set")

    if action == "pre_add":
        for host_id in host_ids:
            host = Host.objects.get(id=host_id)
            group_config.check_host_candidate(host)


class ActionType(models.TextChoices):
    Task = "task", "task"
    Job = "job", "job"


SCRIPT_TYPE = (
    ("ansible", "ansible"),
    ("task_generator", "task_generator"),
)


def get_any():
    """Get `any` literal for JSON field default value"""
    return "any"


class AbstractAction(ADCMModel):
    """Abstract base class for both Action and StageAction"""

    prototype = None

    name = models.CharField(max_length=1000)
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
        unique_together = (("prototype", "name"),)

    def __str__(self):
        return f"{self.prototype} {self.display_name or self.name}"


class Action(AbstractAction):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)

    __error_code__ = "ACTION_NOT_FOUND"

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
        target_ids["action"] = self.pk
        result = {
            "type": self.prototype.type + "_action_run",
            "name": self.display_name or self.name,
            "ids": target_ids,
        }
        return result

    def allowed(self, obj: ADCMEntity) -> bool:
        """Check if action is allowed to be run on object"""
        if self.state_unavailable == "any" or self.multi_state_unavailable == "any":
            return False

        if isinstance(self.state_unavailable, list) and obj.state in self.state_unavailable:
            return False

        if isinstance(self.multi_state_unavailable, list) and obj.has_multi_state_intersection(
            self.multi_state_unavailable
        ):
            return False

        state_allowed = False
        if self.state_available == "any":
            state_allowed = True
        elif isinstance(self.state_available, list) and obj.state in self.state_available:
            state_allowed = True

        multi_state_allowed = False
        if self.multi_state_available == "any":
            multi_state_allowed = True
        elif isinstance(self.multi_state_available, list) and obj.has_multi_state_intersection(
            self.multi_state_available
        ):
            multi_state_allowed = True

        return state_allowed and multi_state_allowed


class AbstractSubAction(ADCMModel):
    action = None

    name = models.CharField(max_length=1000)
    display_name = models.CharField(max_length=160, blank=True)
    script = models.CharField(max_length=160)
    script_type = models.CharField(max_length=16, choices=SCRIPT_TYPE)
    state_on_fail = models.CharField(max_length=64, blank=True)
    multi_state_on_fail_set = models.JSONField(default=list)
    multi_state_on_fail_unset = models.JSONField(default=list)
    params = models.JSONField(default=dict)

    class Meta:
        abstract = True


class SubAction(AbstractSubAction):
    action = models.ForeignKey(Action, on_delete=models.CASCADE)


class HostComponent(ADCMModel):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    service = models.ForeignKey(ClusterObject, on_delete=models.CASCADE)
    component = models.ForeignKey(ServiceComponent, on_delete=models.CASCADE)
    state = models.CharField(max_length=64, default="created")

    class Meta:
        unique_together = (("host", "service", "component"),)


CONFIG_FIELD_TYPE = (
    ("string", "string"),
    ("text", "text"),
    ("password", "password"),
    ("secrettext", "secrettext"),
    ("json", "json"),
    ("integer", "integer"),
    ("float", "float"),
    ("option", "option"),
    ("variant", "variant"),
    ("boolean", "boolean"),
    ("file", "file"),
    ("list", "list"),
    ("map", "map"),
    ("structure", "structure"),
    ("group", "group"),
)


class PrototypeConfig(ADCMModel):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE, null=True, default=None)
    name = models.CharField(max_length=256)
    subname = models.CharField(max_length=256, blank=True)
    default = models.TextField(blank=True)
    type = models.CharField(max_length=16, choices=CONFIG_FIELD_TYPE)
    display_name = models.CharField(max_length=256, blank=True)
    description = models.TextField(blank=True)
    limits = models.JSONField(default=dict)
    ui_options = models.JSONField(blank=True, default=dict)
    required = models.BooleanField(default=True)
    group_customization = models.BooleanField(null=True)

    class Meta:
        unique_together = (("prototype", "action", "name", "subname"),)


class PrototypeExport(ADCMModel):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)

    class Meta:
        unique_together = (("prototype", "name"),)


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
        unique_together = (("prototype", "name"),)


class ClusterBind(ADCMModel):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    service = models.ForeignKey(ClusterObject, on_delete=models.CASCADE, null=True, default=None)
    source_cluster = models.ForeignKey(
        Cluster, related_name="source_cluster", on_delete=models.CASCADE
    )
    source_service = models.ForeignKey(
        ClusterObject,
        related_name="source_service",
        on_delete=models.CASCADE,
        null=True,
        default=None,
    )

    __error_code__ = "BIND_NOT_FOUND"

    class Meta:
        unique_together = (("cluster", "service", "source_cluster", "source_service"),)


JOB_STATUS = (
    ("created", "created"),
    ("running", "running"),
    ("success", "success"),
    ("failed", "failed"),
)


class UserProfile(ADCMModel):
    login = models.CharField(max_length=32, unique=True)
    profile = models.JSONField(default=str)


class TaskLog(ADCMModel):
    object_id = models.PositiveIntegerField()
    object_type = models.ForeignKey(ContentType, null=True, on_delete=models.CASCADE)
    task_object = GenericForeignKey("object_type", "object_id")
    action = models.ForeignKey(Action, on_delete=models.SET_NULL, null=True, default=None)
    pid = models.PositiveIntegerField(blank=True, default=0)
    selector = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=JOB_STATUS)
    config = models.JSONField(null=True, default=None)
    attr = models.JSONField(default=dict)
    hostcomponentmap = models.JSONField(null=True, default=None)
    post_upgrade_hc_map = models.JSONField(null=True, default=None)
    hosts = models.JSONField(null=True, default=None)
    verbose = models.BooleanField(default=False)
    start_date = models.DateTimeField()
    finish_date = models.DateTimeField()
    lock = models.ForeignKey("ConcernItem", null=True, on_delete=models.SET_NULL, default=None)

    def lock_affected(self, objects: Iterable[ADCMEntity]) -> None:
        if self.lock:
            return
        first_job = JobLog.obj.filter(task=self).order_by("id").first()
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

    def cancel(self, event_queue: "cm.status_api.Event" = None, obj_deletion=False):
        """
        Cancel running task process
        task status will be updated in separate process of task runner
        """
        if self.pid == 0:
            raise AdcmEx(
                "NOT_ALLOWED_TERMINATION",
                "Termination is too early, try to execute later",
            )
        errors = {
            Job.FAILED: ("TASK_IS_FAILED", f"task #{self.pk} is failed"),
            Job.ABORTED: ("TASK_IS_ABORTED", f"task #{self.pk} is aborted"),
            Job.SUCCESS: ("TASK_IS_SUCCESS", f"task #{self.pk} is success"),
        }
        action = self.action
        if action and not action.allow_to_terminate and not obj_deletion:
            raise AdcmEx(
                "NOT_ALLOWED_TERMINATION",
                f"not allowed termination task #{self.pk} for action #{action.pk}",
            )
        if self.status in [Job.FAILED, Job.ABORTED, Job.SUCCESS]:
            raise AdcmEx(*errors.get(self.status))
        i = 0
        while not JobLog.objects.filter(task=self, status=Job.RUNNING) and i < 10:
            time.sleep(0.5)
            i += 1
        if i == 10:
            raise AdcmEx("NO_JOBS_RUNNING", "no jobs running")
        self.unlock_affected()
        if event_queue:
            event_queue.send_state()
        os.kill(self.pid, signal.SIGTERM)

    @staticmethod
    def get_adcm_tasks_qs():
        return TaskLog.objects.filter(
            object_type=ContentType.objects.get(app_label="cm", model="adcm")
        )


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

    __error_code__ = "JOB_NOT_FOUND"

    @staticmethod
    def get_adcm_jobs_qs():
        return JobLog.objects.filter(task__in=TaskLog.get_adcm_tasks_qs())


class GroupCheckLog(ADCMModel):
    job = models.ForeignKey(JobLog, on_delete=models.SET_NULL, null=True, default=None)
    title = models.TextField()
    message = models.TextField(blank=True, null=True)
    result = models.BooleanField(blank=True, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["job", "title"], name="unique_group_job")]


class CheckLog(ADCMModel):
    group = models.ForeignKey(GroupCheckLog, blank=True, null=True, on_delete=models.CASCADE)
    job = models.ForeignKey(JobLog, on_delete=models.SET_NULL, null=True, default=None)
    title = models.TextField()
    message = models.TextField()
    result = models.BooleanField()


LOG_TYPE = (
    ("stdout", "stdout"),
    ("stderr", "stderr"),
    ("check", "check"),
    ("custom", "custom"),
)

FORMAT_TYPE = (
    ("txt", "txt"),
    ("json", "json"),
)


class LogStorage(ADCMModel):
    job = models.ForeignKey(JobLog, on_delete=models.CASCADE)
    name = models.TextField(default="")
    body = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=16, choices=LOG_TYPE)
    format = models.CharField(max_length=16, choices=FORMAT_TYPE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["job"], condition=models.Q(type="check"), name="unique_check_job"
            )
        ]


# Stage: Temporary tables to load bundle


class StagePrototype(ADCMModel):
    type = models.CharField(max_length=16, choices=ObjectType.choices)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, default=None)
    name = models.CharField(max_length=256)
    path = models.CharField(max_length=160, default="")
    display_name = models.CharField(max_length=1000, blank=True)
    version = models.CharField(max_length=80)
    edition = models.CharField(max_length=80, default="community")
    license_path = models.CharField(max_length=160, default=None, null=True)
    license_hash = models.CharField(max_length=64, default=None, null=True)
    required = models.BooleanField(default=False)
    shared = models.BooleanField(default=False)
    constraint = models.JSONField(default=get_default_constraint)
    requires = models.JSONField(default=list)
    bound_to = models.JSONField(default=dict)
    adcm_min_version = models.CharField(max_length=80, default=None, null=True)
    description = models.TextField(blank=True)
    monitoring = models.CharField(max_length=16, choices=MONITORING_TYPE, default="active")
    config_group_customization = models.BooleanField(default=False)
    venv = models.CharField(default="default", max_length=160, blank=False)
    allow_maintenance_mode = models.BooleanField(default=False)

    __error_code__ = "PROTOTYPE_NOT_FOUND"

    def __str__(self):
        return str(self.name)

    class Meta:
        unique_together = (("type", "parent", "name", "version"),)


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
    action = models.OneToOneField("StageAction", on_delete=models.CASCADE, null=True)


class StageAction(AbstractAction):  # pylint: disable=too-many-instance-attributes
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)


class StageSubAction(AbstractSubAction):
    action = models.ForeignKey(StageAction, on_delete=models.CASCADE)


class StagePrototypeConfig(ADCMModel):
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)
    action = models.ForeignKey(StageAction, on_delete=models.CASCADE, null=True, default=None)
    name = models.CharField(max_length=256)
    subname = models.CharField(max_length=256, blank=True)
    default = models.TextField(blank=True)
    type = models.CharField(max_length=16, choices=CONFIG_FIELD_TYPE)
    display_name = models.CharField(max_length=256, blank=True)
    description = models.TextField(blank=True)
    limits = models.JSONField(default=dict)
    ui_options = models.JSONField(blank=True, default=dict)
    required = models.BooleanField(default=True)
    group_customization = models.BooleanField(null=True)

    class Meta:
        unique_together = (("prototype", "action", "name", "subname"),)


class StagePrototypeExport(ADCMModel):
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)

    class Meta:
        unique_together = (("prototype", "name"),)


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
        unique_together = (("prototype", "name"),)


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
        LockedByJob = "locked by running job on target"  # kwargs=(job, target)
        ConfigIssue = "object config issue"  # kwargs=(source, )
        RequiredServiceIssue = "required service issue"  # kwargs=(source, )
        RequiredImportIssue = "required import issue"  # kwargs=(source, )
        HostComponentIssue = "host component issue"  # kwargs=(source, )

    class PlaceHolderType(Enum):
        Action = "action"
        ADCMEntity = "adcm_entity"
        ADCM = "adcm"
        Cluster = "cluster"
        Service = "service"
        Component = "component"
        Provider = "provider"
        Host = "host"
        Job = "job"

    @classmethod
    def get_message_from_template(cls, name: str, **kwargs) -> dict:
        """Find message template by its name and fill placeholders"""
        tpl = cls.obj.get(name=name).template
        filled_placeholders = {}
        try:
            for ph_name, ph_data in tpl["placeholder"].items():
                filled_placeholders[ph_name] = cls._fill_placeholder(ph_name, ph_data, **kwargs)
        except (KeyError, AttributeError, TypeError, AssertionError) as ex:
            if isinstance(ex, KeyError):
                msg = f'Message templating KeyError: "{ex.args[0]}" not found'
            elif isinstance(ex, AttributeError):
                msg = f'Message templating AttributeError: "{ex.args[0]}"'
            elif isinstance(ex, TypeError):
                msg = f'Message templating TypeError: "{ex.args[0]}"'
            elif isinstance(ex, AssertionError):
                msg = "Message templating AssertionError: expected kwarg were not found"
            else:
                msg = None
            raise AdcmEx("MESSAGE_TEMPLATING_ERROR", msg=msg) from ex
        tpl["placeholder"] = filled_placeholders
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
        return type_map[ph_data["type"]](ph_name, **ph_source_data)

    @classmethod
    def _action_placeholder(cls, _, **kwargs) -> dict:
        action = kwargs.get("action")
        assert action
        target = kwargs.get("target")
        assert target

        ids = target.get_id_chain()
        ids["action"] = action.pk
        return {
            "type": cls.PlaceHolderType.Action.value,
            "name": action.display_name,
            "ids": ids,
        }

    @classmethod
    def _adcm_entity_placeholder(cls, ph_name, **kwargs) -> dict:
        obj = kwargs.get(ph_name)
        assert obj

        return {
            "type": obj.prototype.type,
            "name": obj.display_name,
            "ids": obj.get_id_chain(),
        }

    @classmethod
    def _job_placeholder(cls, _, **kwargs) -> dict:
        job = kwargs.get("job")
        assert job
        action = job.sub_action or job.action

        return {
            "type": cls.PlaceHolderType.Job.value,
            "name": action.display_name or action.name,
            "ids": job.id,
        }


class ConcernType(models.TextChoices):
    Lock = "lock", "lock"
    Issue = "issue", "issue"
    Flag = "flag", "flag"


class ConcernCause(models.TextChoices):
    Config = "config", "config"
    Job = "job", "job"
    HostComponent = "host-component", "host-component"
    Import = "import", "import"
    Service = "service", "service"


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
    owner = GenericForeignKey("owner_type", "owner_id")
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
