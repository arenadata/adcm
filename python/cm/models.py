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


import os.path
import signal
import time
from collections.abc import Iterable, Mapping
from copy import deepcopy
from enum import Enum
from itertools import chain
from typing import Optional, TypeAlias
from uuid import uuid4

from cm.errors import AdcmEx
from cm.logger import logger
from cm.utils import deep_merge
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver


def validate_line_break_character(value: str) -> None:
    """Check line break character in CharField"""
    if len(value.splitlines()) > 1:
        raise ValidationError("the string field contains a line break character")


class ObjectType(models.TextChoices):
    ADCM = "adcm", "adcm"
    CLUSTER = "cluster", "cluster"
    SERVICE = "service", "service"
    COMPONENT = "component", "component"
    PROVIDER = "provider", "provider"
    HOST = "host", "host"


class MaintenanceMode(models.TextChoices):
    ON = "on", "on"
    OFF = "off", "off"
    CHANGING = "changing", "changing"


MAINTENANCE_MODE_BOTH_CASES_CHOICES = (
    ("on", "on"),
    ("off", "off"),
    ("ON", "ON"),
    ("OFF", "OFF"),
)


class SignatureStatus(models.TextChoices):
    VALID = "valid", "valid"
    INVALID = "invalid", "invalid"
    ABSENT = "absent", "absent"


LICENSE_STATE = (
    ("absent", "absent"),
    ("accepted", "accepted"),
    ("unaccepted", "unaccepted"),
)


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
    by DRF and is reported out as nicely formatted error instead of ugly exception.

    Using ADCMManager can shorten you code significantly. Instead of

    try:
        cluster = Cluster.objects.get(id=id)
    except Cluster.DoesNotExist:
        raise AdcmEx(Cluster {id} is not found)

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
                next(values_iter) if f.attname in field_names else models.DEFERRED for f in cls._meta.concrete_fields
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
    name = models.CharField(max_length=1000)
    version = models.CharField(max_length=1000)
    version_order = models.PositiveIntegerField(default=0)
    edition = models.CharField(max_length=1000, default="community")
    hash = models.CharField(max_length=1000)
    description = models.TextField(blank=True)
    date = models.DateTimeField(auto_now=True)
    category = models.ForeignKey("ProductCategory", on_delete=models.RESTRICT, null=True)
    signature_status = models.CharField(max_length=10, choices=SignatureStatus.choices, default=SignatureStatus.ABSENT)

    __error_code__ = "BUNDLE_NOT_FOUND"

    class Meta:
        unique_together = (("name", "version", "edition"),)


class ProductCategory(ADCMModel):
    """
    Categories are used for some model's categorization.
    It's same as Bundle.name but unlinked from it due to simplicity reasons.
    """

    value = models.CharField(max_length=1000, unique=True)
    visible = models.BooleanField(default=True)

    @classmethod
    def re_collect(cls) -> None:
        """Re-sync category list with installed bundles"""
        for bundle in Bundle.objects.filter(category=None).order_by("id"):
            prototype = Prototype.objects.filter(bundle=bundle, name=bundle.name, type=ObjectType.CLUSTER).first()
            if prototype:
                value = prototype.display_name or bundle.name
                bundle.category, _ = cls.objects.get_or_create(value=value)
                bundle.save()
        for category in cls.objects.order_by("id"):
            if category.bundle_set.count() == 0:
                category.delete()


def get_default_from_edition():
    return ["community"]


MONITORING_TYPE = (
    ("active", "active"),
    ("passive", "passive"),
)

NO_LDAP_SETTINGS = "The Action is not available. You need to fill in the LDAP integration settings."
SERVICE_IN_MM = "The Action is not available. Service in 'Maintenance mode'"
COMPONENT_IN_MM = "The Action is not available. Component in 'Maintenance mode'"
HOST_IN_MM = "The Action is not available. Host in 'Maintenance mode'"
MANY_HOSTS_IN_MM = "The Action is not available. One or more hosts in 'Maintenance mode'"


def get_default_constraint():
    return [0, "+"]


class Prototype(ADCMModel):
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE)
    type = models.CharField(max_length=1000, choices=ObjectType.choices)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, default=None)
    path = models.CharField(max_length=1000, default="")
    name = models.CharField(max_length=1000)
    license = models.CharField(max_length=1000, choices=LICENSE_STATE, default="absent")
    license_path = models.CharField(max_length=1000, default=None, null=True)
    license_hash = models.CharField(max_length=1000, default=None, null=True)
    display_name = models.CharField(max_length=1000, blank=True)
    version = models.CharField(max_length=1000)
    version_order = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=False)
    shared = models.BooleanField(default=False)
    constraint = models.JSONField(default=get_default_constraint)
    requires = models.JSONField(default=list)
    bound_to = models.JSONField(default=dict)
    adcm_min_version = models.CharField(max_length=1000, default=None, null=True)
    monitoring = models.CharField(max_length=1000, choices=MONITORING_TYPE, default="active")
    description = models.TextField(blank=True)
    config_group_customization = models.BooleanField(default=False)
    venv = models.CharField(default="default", max_length=1000, blank=False)
    allow_maintenance_mode = models.BooleanField(default=False)
    allow_flags = models.BooleanField(default=False)

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


class ConfigLog(ADCMModel):
    obj_ref = models.ForeignKey(ObjectConfig, on_delete=models.CASCADE)
    config = models.JSONField(default=dict)
    attr = models.JSONField(default=dict)
    date = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True)

    __error_code__ = "CONFIG_NOT_FOUND"

    @transaction.atomic()
    def save(self, *args, **kwargs):  # pylint: disable=too-many-locals,too-many-statements
        def update_config(origin: dict, renovator: dict, _group_keys: dict) -> None:
            for key, value in _group_keys.items():
                if key in renovator:
                    if isinstance(value, Mapping):
                        origin.setdefault(key, {})
                        update_config(origin[key], renovator[key], _group_keys[key]["fields"])
                    else:
                        if value:
                            origin[key] = renovator[key]

        def update_attr(origin: dict, renovator: dict, _group_keys: dict) -> None:
            for key, value in _group_keys.items():
                if key in renovator and isinstance(value, Mapping):
                    if value["value"] is not None and value["value"]:
                        origin[key] = renovator[key]

        def clean_attr(attrs: dict, _spec: dict) -> None:
            extra_fields = []

            for key in attrs.keys():
                if key not in ["group_keys", "custom_group_keys"]:
                    if key not in _spec:
                        extra_fields.append(key)

            for field in extra_fields:
                attrs.pop(field)

        def clean_group_keys(_group_keys, _spec):
            correct_group_keys = {}
            for field, info in _spec.items():
                if info["type"] == "group":
                    correct_group_keys[field] = {}
                    correct_group_keys[field]["value"] = _group_keys[field]["value"]
                    correct_group_keys[field]["fields"] = {}
                    for key in info["fields"].keys():
                        correct_group_keys[field]["fields"][key] = _group_keys[field]["fields"][key]
                else:
                    correct_group_keys[field] = _group_keys[field]
            return correct_group_keys

        obj = self.obj_ref.object
        if isinstance(obj, (Cluster, ClusterObject, ServiceComponent, HostProvider)):
            # Sync group configs with object config
            for conf_group in obj.group_config.order_by("id"):
                diff_config, diff_attr = conf_group.get_diff_config_attr()
                group_config = ConfigLog()
                current_group_config = ConfigLog.objects.get(id=conf_group.config.current)
                group_config.obj_ref = conf_group.config
                config = deepcopy(self.config)
                current_group_keys = current_group_config.attr["group_keys"]
                update_config(config, diff_config, current_group_keys)
                group_config.config = config
                attr = deepcopy(self.attr)
                update_attr(attr, diff_attr, current_group_keys)
                spec = conf_group.get_config_spec()
                group_keys, custom_group_keys = conf_group.create_group_keys(spec)
                group_keys = deep_merge(group_keys, current_group_keys)
                group_keys = clean_group_keys(group_keys, spec)
                attr["group_keys"] = group_keys
                attr["custom_group_keys"] = custom_group_keys
                clean_attr(attr, spec)

                group_config.attr = attr
                group_config.description = current_group_config.description
                group_config.save()
                conf_group.config.previous = conf_group.config.current
                conf_group.config.current = group_config.id
                conf_group.config.save()
                conf_group.preparing_file_type_field()
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
    state = models.CharField(max_length=1000, default="created")
    _multi_state = models.JSONField(default=dict, db_column="multi_state")
    concerns = models.ManyToManyField("ConcernItem", blank=True, related_name="%(class)s_entities")
    policy_object = GenericRelation("rbac.PolicyObject")

    class Meta:
        abstract = True

    @property
    def locked(self) -> bool:
        """Check if actions could be run over entity"""
        return self.concerns.filter(blocking=True).exists()

    def get_own_issue(self, cause: "ConcernCause") -> Optional["ConcernItem"]:
        """Get object's issue of specified cause or None"""
        return self.concerns.filter(
            type=ConcernType.ISSUE,
            owner_id=self.pk,
            owner_type=self.content_type,
            cause=cause,
        ).first()

    def requires_service_name(self, service_name: str) -> bool:
        for item in self.requires:
            if item.get("service") == service_name:
                return True

        return False

    def __str__(self):
        own_name = getattr(self, "name", None)
        fqdn = getattr(self, "fqdn", None)
        name = own_name or fqdn or self.prototype.name
        return f'{self.prototype.type} #{self.id} "{name}"'

    def set_state(self, state: str) -> None:
        self.state = state or self.state
        self.save()
        logger.info('set %s state to "%s"', self, state)

    def get_id_chain(self) -> dict:
        """
        Get object ID chain for front-end URL generation in message templates
        result looks like {'cluster_id': 12, 'service_id': 34, 'component_id': 45}
        """
        ids = {}
        ids[f"{self.prototype.type}_id"] = self.pk
        for attr in ["cluster_id", "service_id", "provider_id"]:
            value = getattr(self, attr, None)
            if value is not None:
                ids[attr] = value

        return ids

    @property
    def multi_state(self) -> list[str]:
        """Easy to operate self._multi_state representation"""
        return sorted(self._multi_state.keys())

    def set_multi_state(self, multi_state: str) -> None:
        """Append new unique multi_state to entity._multi_state"""
        if multi_state in self._multi_state:
            return

        self._multi_state.update({multi_state: 1})
        self.save()

        logger.info('add "%s" to "%s" multi_state', multi_state, self)

    def unset_multi_state(self, multi_state: str) -> None:
        """Remove specified multi_state from entity._multi_state"""
        if multi_state not in self._multi_state:
            return

        del self._multi_state[multi_state]
        self.save()

        logger.info('remove "%s" from "%s" multi_state', multi_state, self)

    def has_multi_state_intersection(self, multi_states: list[str]) -> bool:
        """Check if entity._multi_state has an intersection with list of multi_states"""
        return bool(set(self._multi_state).intersection(multi_states))

    @property
    def content_type(self):
        model_name = self.__class__.__name__.lower()
        return ContentType.objects.get(app_label="cm", model=model_name)

    def delete(self, using=None, keep_parents=False):
        for concern in self.concerns.filter(owner_type=self.content_type, owner_id=self.id):
            logger.debug("Delete %s", str(concern))
            concern.delete()

        super().delete(using, keep_parents)
        if self.config is not None and not isinstance(self, ServiceComponent):
            self.config.delete()


class Upgrade(ADCMModel):
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE)
    name = models.CharField(max_length=1000, blank=True)
    display_name = models.CharField(max_length=1000, blank=True)
    description = models.TextField(blank=True)
    min_version = models.CharField(max_length=1000)
    max_version = models.CharField(max_length=1000)
    from_edition = models.JSONField(default=get_default_from_edition)
    min_strict = models.BooleanField(default=False)
    max_strict = models.BooleanField(default=False)
    state_available = models.JSONField(default=list)
    state_on_success = models.CharField(max_length=1000, blank=True)
    action = models.OneToOneField("Action", on_delete=models.CASCADE, null=True)

    __error_code__ = "UPGRADE_NOT_FOUND"

    def allowed(self, obj: ADCMEntity) -> bool:
        if self.state_available:
            available = self.state_available

            if obj.state in available:
                return True
            elif available == "any":
                return True
            else:
                return False
        else:
            if self.action:
                return self.action.allowed(obj=obj)

            return False


class ADCM(ADCMEntity):
    name = models.CharField(max_length=1000, choices=(("ADCM", "ADCM"),), unique=True)
    uuid = models.UUIDField(default=uuid4, editable=False)

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
    name = models.CharField(max_length=1000, unique=True)
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
        return self.prototype.license

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
    name = models.CharField(max_length=1000, unique=True)
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
        return self.prototype.license

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
    fqdn = models.CharField(max_length=1000, unique=True)
    description = models.TextField(blank=True)
    provider = models.ForeignKey(HostProvider, on_delete=models.CASCADE, null=True, default=None)
    cluster = models.ForeignKey(Cluster, on_delete=models.SET_NULL, null=True, default=None)
    maintenance_mode = models.CharField(
        max_length=1000,
        choices=MaintenanceMode.choices,
        default=MaintenanceMode.OFF,
    )
    before_upgrade = models.JSONField(default=get_default_before_upgrade)

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

    @property
    def maintenance_mode_attr(self) -> MaintenanceMode.choices:
        return self.maintenance_mode


class ClusterObject(ADCMEntity):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    service = models.ForeignKey("self", on_delete=models.CASCADE, null=True, default=None)
    group_config = GenericRelation(
        "GroupConfig",
        object_id_field="object_id",
        content_type_field="object_type",
        on_delete=models.CASCADE,
    )
    _maintenance_mode = models.CharField(
        max_length=1000,
        choices=MaintenanceMode.choices,
        default=MaintenanceMode.OFF,
    )
    before_upgrade = models.JSONField(default=get_default_before_upgrade)

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
    def requires(self) -> list:
        return self.prototype.requires

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

    @property
    def maintenance_mode_attr(self) -> MaintenanceMode.choices:
        return self._maintenance_mode

    @property
    def maintenance_mode(self) -> MaintenanceMode.choices:
        if self._maintenance_mode != MaintenanceMode.OFF:
            return self._maintenance_mode

        service_components = ServiceComponent.objects.filter(service=self)
        if service_components:
            if all(
                service_component.maintenance_mode_attr == MaintenanceMode.ON
                for service_component in service_components
            ):
                return MaintenanceMode.ON

            hosts_maintenance_modes = []
            host_ids = HostComponent.objects.filter(service=self).values_list("host_id", flat=True)

            hosts_maintenance_modes.extend(
                Host.objects.filter(id__in=host_ids).values_list("maintenance_mode", flat=True),
            )
            if hosts_maintenance_modes:
                return (
                    MaintenanceMode.ON
                    if all(
                        host_maintenance_mode == MaintenanceMode.ON for host_maintenance_mode in hosts_maintenance_modes
                    )
                    else MaintenanceMode.OFF
                )

        return self._maintenance_mode

    @maintenance_mode.setter
    def maintenance_mode(self, value: MaintenanceMode.choices) -> None:
        self._maintenance_mode = value

    @property
    def is_maintenance_mode_available(self) -> bool:
        return self.cluster.prototype.allow_maintenance_mode

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
    _maintenance_mode = models.CharField(
        max_length=1000,
        choices=MaintenanceMode.choices,
        default=MaintenanceMode.OFF,
    )
    before_upgrade = models.JSONField(default=get_default_before_upgrade)

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

    @property
    def maintenance_mode_attr(self) -> MaintenanceMode.choices:
        return self._maintenance_mode

    @property
    def maintenance_mode(self) -> MaintenanceMode.choices:
        if self._maintenance_mode != MaintenanceMode.OFF:
            return self._maintenance_mode

        if self.service.maintenance_mode_attr == MaintenanceMode.ON:
            return self.service.maintenance_mode_attr

        host_ids = HostComponent.objects.filter(component=self).values_list("host_id", flat=True)
        if host_ids:
            return (
                MaintenanceMode.ON
                if all(Host.objects.get(pk=host_id).maintenance_mode == MaintenanceMode.ON for host_id in host_ids)
                else MaintenanceMode.OFF
            )

        return self._maintenance_mode

    @maintenance_mode.setter
    def maintenance_mode(self, value: MaintenanceMode.choices) -> None:
        self._maintenance_mode = value

    @property
    def is_maintenance_mode_available(self) -> bool:
        return self.cluster.prototype.allow_maintenance_mode

    class Meta:
        unique_together = (("cluster", "service", "prototype"),)


@receiver(post_delete, sender=ServiceComponent)
def auto_delete_config_with_servicecomponent(sender, instance, **kwargs):  # pylint: disable=unused-argument
    if instance.config is not None:
        instance.config.delete()


class GroupConfig(ADCMModel):
    object_id = models.PositiveIntegerField()
    object_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object = GenericForeignKey("object_type", "object_id")
    name = models.CharField(max_length=1000, validators=[validate_line_break_character])
    description = models.TextField(blank=True)
    hosts = models.ManyToManyField(Host, blank=True, related_name="group_config")
    config = models.OneToOneField(ObjectConfig, on_delete=models.CASCADE, null=True, related_name="group_config")

    __error_code__ = "GROUP_CONFIG_NOT_FOUND"

    not_changeable_fields = ("id", "object_id", "object_type")

    @property
    def prototype(self):
        return self.object.prototype

    class Meta:
        unique_together = ["object_id", "name", "object_type"]

    def get_config_spec(self):
        """Return spec for config"""
        spec = {}
        for field in PrototypeConfig.objects.filter(prototype=self.object.prototype, action__isnull=True).order_by(
            "id",
        ):
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
        group_keys: dict[str, bool] = None,
        custom_group_keys: dict[str, bool] = None,
    ):
        """
        Returns a map of fields that are included in a group,
        as well as a map of fields that cannot be included in a group
        """

        if group_keys is None:
            group_keys = {}

        if custom_group_keys is None:
            custom_group_keys = {}

        for config_key, config_value in config_spec.items():
            if config_value["type"] == "group":
                value = None

                if "activatable" in config_value["limits"]:
                    value = False

                group_keys.setdefault(config_key, {"value": value, "fields": {}})
                custom_group_keys.setdefault(config_key, {"value": config_value["group_customization"], "fields": {}})
                self.create_group_keys(
                    config_value["fields"],
                    group_keys[config_key]["fields"],
                    custom_group_keys[config_key]["fields"],
                )
            else:
                group_keys[config_key] = False
                custom_group_keys[config_key] = config_value["group_customization"]

        return group_keys, custom_group_keys

    def get_diff_config_attr(self):
        def get_diff(_config, _attr, _group_keys, diff_config=None, diff_attr=None):
            if diff_config is None:
                diff_config = {}

            if diff_attr is None:
                diff_attr = {}

            for group_key, group_value in _group_keys.items():
                if isinstance(group_value, Mapping):
                    if group_value["value"] is not None and group_value["value"]:
                        diff_attr[group_key] = _attr[group_key]

                    diff_config.setdefault(group_key, {})
                    get_diff(
                        _config[group_key],
                        _attr,
                        _group_keys[group_key]["fields"],
                        diff_config[group_key],
                        diff_attr,
                    )
                    if not diff_config[group_key]:
                        diff_config.pop(group_key)
                else:
                    if group_value:
                        diff_config[group_key] = _config[group_key]

            return diff_config, diff_attr

        config_log = ConfigLog.obj.get(id=self.config.current)
        config = config_log.config
        attr = config_log.attr
        group_keys = config_log.attr.get("group_keys", {})

        return get_diff(config, attr, group_keys)

    def get_group_keys(self):
        config_log = ConfigLog.objects.get(id=self.config.current)

        return config_log.attr.get("group_keys", {})

    def merge_config(self, object_config: dict, group_config: dict, group_keys: dict, config=None):
        """Merge object config with group config based group_keys"""

        if config is None:
            config = {}

        for group_key, group_value in group_keys.items():
            if isinstance(group_value, Mapping):
                config.setdefault(group_key, {})
                self.merge_config(
                    object_config[group_key],
                    group_config[group_key],
                    group_keys[group_key]["fields"],
                    config[group_key],
                )
            else:
                if group_value and group_key in group_config:
                    config[group_key] = group_config[group_key]
                else:
                    if group_key in object_config:
                        config[group_key] = object_config[group_key]

        return config

    @staticmethod
    def merge_attr(object_attr: dict, group_attr: dict, group_keys: dict, attr=None):
        """Merge object attr with group attr based group_keys"""

        if attr is None:
            attr = {}

        for group_key, group_value in group_keys.items():
            if isinstance(group_value, Mapping) and group_key in object_attr:
                if group_value["value"]:
                    attr[group_key] = group_attr[group_key]
                else:
                    attr[group_key] = object_attr[group_key]

        return attr

    def get_config_attr(self):
        """Return attr for group config without group_keys and custom_group_keys params"""

        config_log = ConfigLog.obj.get(id=self.config.current)
        attr = {k: v for k, v in config_log.attr.items() if k not in ("group_keys", "custom_group_keys")}

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
            hosts = self.object.host_set.order_by("id")
        elif isinstance(self.object, ClusterObject):
            hosts = Host.objects.filter(cluster=self.object.cluster, hostcomponent__service=self.object).distinct()
        elif isinstance(self.object, ServiceComponent):
            hosts = Host.objects.filter(cluster=self.object.cluster, hostcomponent__component=self.object).distinct()
        else:
            raise AdcmEx("GROUP_CONFIG_TYPE_ERROR")

        return hosts.exclude(group_config__in=self.object.group_config.all())

    def check_host_candidate(self, host_ids: list[int]):
        if self.hosts.filter(pk__in=host_ids).exists():
            raise AdcmEx("GROUP_CONFIG_HOST_EXISTS")

        if set(host_ids).difference({host.pk for host in self.host_candidate()}):
            raise AdcmEx("GROUP_CONFIG_HOST_ERROR")

    def preparing_file_type_field(self, config=None):
        """Creating file for file type field"""

        if self.config is None:
            return

        if config is None:
            config = ConfigLog.objects.get(id=self.config.current).config

        fields = PrototypeConfig.objects.filter(
            prototype=self.object.prototype,
            action__isnull=True,
            type="file",
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
                ],
            )
            filepath = str(settings.FILE_DIR / filename)

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

                with open(filepath, "w", encoding=settings.ENCODING_UTF_8) as f:
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


class ActionType(models.TextChoices):
    TASK = "task", "task"
    JOB = "job", "job"


SCRIPT_TYPE = (
    ("ansible", "ansible"),
    ("task_generator", "task_generator"),
)


def get_any():
    """Get `any` literal for JSON field default value"""

    return "any"


class AbstractAction(ADCMModel):
    prototype = None

    name = models.CharField(max_length=1000)
    display_name = models.CharField(max_length=1000, blank=True)
    description = models.TextField(blank=True)
    ui_options = models.JSONField(default=dict)

    type = models.CharField(max_length=1000, choices=ActionType.choices)
    script = models.CharField(max_length=1000)
    script_type = models.CharField(max_length=1000, choices=SCRIPT_TYPE)

    state_available = models.JSONField(default=list)
    state_unavailable = models.JSONField(default=list)
    state_on_success = models.CharField(max_length=1000, blank=True)
    state_on_fail = models.CharField(max_length=1000, blank=True)

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
    config_jinja = models.CharField(max_length=1000, blank=True, null=True)

    _venv = models.CharField(default="default", db_column="venv", max_length=1000, blank=False)

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
        target_ids["action_id"] = self.pk
        result = {
            "type": f"{self.prototype.type}_action_run",
            "name": self.display_name or self.name,
            "params": target_ids,
        }
        return result

    def allowed(self, obj: ADCMEntity) -> bool:
        """Check if action is allowed to be run on object"""
        if self.state_unavailable == "any" or self.multi_state_unavailable == "any":
            return False

        if isinstance(self.state_unavailable, list) and obj.state in self.state_unavailable:
            return False

        if isinstance(self.multi_state_unavailable, list) and obj.has_multi_state_intersection(
            self.multi_state_unavailable,
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
            self.multi_state_available,
        ):
            multi_state_allowed = True

        return state_allowed and multi_state_allowed

    def get_start_impossible_reason(self, obj: ADCMEntity) -> str | None:
        # pylint: disable=too-many-branches, too-many-return-statements

        if obj.prototype.type == "adcm":
            obj: ADCM

            current_configlog = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
            if not current_configlog.attr["ldap_integration"]["active"]:
                return NO_LDAP_SETTINGS

        if obj.prototype.type == "cluster":
            obj: Cluster

            if not self.allow_in_maintenance_mode:
                if Host.objects.filter(cluster=obj, maintenance_mode=MaintenanceMode.ON).exists():
                    return MANY_HOSTS_IN_MM

                related_services = ClusterObject.objects.filter(cluster=obj)

                if any(service.maintenance_mode == MaintenanceMode.ON for service in related_services):
                    return SERVICE_IN_MM

                if any(
                    component.maintenance_mode == MaintenanceMode.ON
                    for component in ServiceComponent.objects.filter(service__in=related_services)
                ):
                    return COMPONENT_IN_MM

        elif obj.prototype.type == "service":
            obj: ClusterObject

            if not self.allow_in_maintenance_mode:
                if obj.maintenance_mode == MaintenanceMode.ON:
                    return SERVICE_IN_MM

                if any(
                    component.maintenance_mode == MaintenanceMode.ON
                    for component in ServiceComponent.objects.filter(service=obj)
                ):
                    return COMPONENT_IN_MM

                if HostComponent.objects.filter(
                    service=obj,
                    cluster=obj.cluster,
                    host__maintenance_mode=MaintenanceMode.ON,
                ).exists():
                    return MANY_HOSTS_IN_MM

        elif obj.prototype.type == "component":
            obj: ServiceComponent

            if not self.allow_in_maintenance_mode:
                if obj.maintenance_mode == MaintenanceMode.ON:
                    return COMPONENT_IN_MM

                if HostComponent.objects.filter(
                    component=obj,
                    cluster=obj.cluster,
                    service=obj.service,
                    host__maintenance_mode=MaintenanceMode.ON,
                ).exists():
                    return MANY_HOSTS_IN_MM

        elif obj.prototype.type == "host":
            obj: Host

            if not self.allow_in_maintenance_mode:
                if obj.maintenance_mode == MaintenanceMode.ON:
                    return HOST_IN_MM

        return None


class AbstractSubAction(ADCMModel):
    action = None

    name = models.CharField(max_length=1000)
    display_name = models.CharField(max_length=1000, blank=True)
    script = models.CharField(max_length=1000)
    script_type = models.CharField(max_length=1000, choices=SCRIPT_TYPE)
    state_on_fail = models.CharField(max_length=1000, blank=True)
    multi_state_on_fail_set = models.JSONField(default=list)
    multi_state_on_fail_unset = models.JSONField(default=list)
    params = models.JSONField(default=dict)
    allow_to_terminate = models.BooleanField(null=True, default=None)

    class Meta:
        abstract = True


class SubAction(AbstractSubAction):
    action = models.ForeignKey(Action, on_delete=models.CASCADE)

    @property
    def allowed_to_terminate(self) -> bool:
        if self.allow_to_terminate is None:
            return self.action.allow_to_terminate
        return self.allow_to_terminate


class HostComponent(ADCMModel):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE)
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    service = models.ForeignKey(ClusterObject, on_delete=models.CASCADE)
    component = models.ForeignKey(ServiceComponent, on_delete=models.CASCADE)
    state = models.CharField(max_length=1000, default="created")

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
    ("secretfile", "secretfile"),
    ("list", "list"),
    ("map", "map"),
    ("secretmap", "secretmap"),
    ("structure", "structure"),
    ("group", "group"),
)


class PrototypeConfig(ADCMModel):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE, null=True, default=None)
    name = models.CharField(max_length=1000)
    subname = models.CharField(max_length=1000, blank=True)
    default = models.TextField(blank=True)
    type = models.CharField(max_length=1000, choices=CONFIG_FIELD_TYPE)
    display_name = models.CharField(max_length=1000, blank=True)
    description = models.TextField(blank=True)
    limits = models.JSONField(default=dict)
    ui_options = models.JSONField(blank=True, default=dict)
    required = models.BooleanField(default=True)
    group_customization = models.BooleanField(null=True)

    class Meta:
        ordering = ["id"]
        unique_together = (("prototype", "action", "name", "subname"),)


class PrototypeExport(ADCMModel):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=1000)

    class Meta:
        unique_together = (("prototype", "name"),)


class PrototypeImport(ADCMModel):
    prototype = models.ForeignKey(Prototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=1000)
    min_version = models.CharField(max_length=1000)
    max_version = models.CharField(max_length=1000)
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
    source_cluster = models.ForeignKey(Cluster, related_name="source_cluster", on_delete=models.CASCADE)
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


class JobStatus(models.TextChoices):
    CREATED = "created", "created"
    SUCCESS = "success", "success"
    FAILED = "failed", "failed"
    RUNNING = "running", "running"
    LOCKED = "locked", "locked"
    ABORTED = "aborted", "aborted"


class UserProfile(ADCMModel):
    login = models.CharField(max_length=1000, unique=True)
    profile = models.JSONField(default=str)


class TaskLog(ADCMModel):
    object_id = models.PositiveIntegerField()
    object_type = models.ForeignKey(ContentType, null=True, on_delete=models.CASCADE)
    task_object = GenericForeignKey("object_type", "object_id")
    action = models.ForeignKey(Action, on_delete=models.SET_NULL, null=True, default=None)
    pid = models.PositiveIntegerField(blank=True, default=0)
    selector = models.JSONField(default=dict)
    status = models.CharField(max_length=1000, choices=JobStatus.choices)
    config = models.JSONField(null=True, default=None)
    attr = models.JSONField(default=dict)
    hostcomponentmap = models.JSONField(null=True, default=None)
    post_upgrade_hc_map = models.JSONField(null=True, default=None)
    restore_hc_on_fail = models.BooleanField(default=True)
    hosts = models.JSONField(null=True, default=None)
    verbose = models.BooleanField(default=False)
    start_date = models.DateTimeField(null=True, default=None)
    finish_date = models.DateTimeField(null=True, default=None)
    lock = models.ForeignKey("ConcernItem", null=True, on_delete=models.SET_NULL, default=None)

    __error_code__ = "TASK_NOT_FOUND"

    def cancel(self, obj_deletion=False):
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
            JobStatus.FAILED: ("TASK_IS_FAILED", f"task #{self.pk} is failed"),
            JobStatus.ABORTED: ("TASK_IS_ABORTED", f"task #{self.pk} is aborted"),
            JobStatus.SUCCESS: ("TASK_IS_SUCCESS", f"task #{self.pk} is success"),
        }
        action = self.action
        if action and not action.allow_to_terminate and not obj_deletion:
            raise AdcmEx(
                "NOT_ALLOWED_TERMINATION",
                f"not allowed termination task #{self.pk} for action #{action.pk}",
            )
        if self.status in [JobStatus.FAILED, JobStatus.ABORTED, JobStatus.SUCCESS]:
            raise AdcmEx(*errors.get(self.status))
        i = 0
        while not JobLog.objects.filter(task=self, status=JobStatus.RUNNING) and i < 10:
            time.sleep(0.5)
            i += 1
        if i == 10:
            raise AdcmEx("NO_JOBS_RUNNING", "no jobs running")

        try:
            os.kill(self.pid, signal.SIGTERM)
        except OSError as e:
            raise AdcmEx("NOT_ALLOWED_TERMINATION", f"Failed to terminate process: {e}") from e

    @property
    def duration(self) -> float | None:
        if self.finish_date is None or self.start_date is None:
            return None

        return (self.finish_date - self.start_date).total_seconds()


class JobLog(ADCMModel):
    task = models.ForeignKey(TaskLog, on_delete=models.SET_NULL, null=True, default=None)
    action = models.ForeignKey(Action, on_delete=models.SET_NULL, null=True, default=None)
    sub_action = models.ForeignKey(SubAction, on_delete=models.SET_NULL, null=True, default=None)
    pid = models.PositiveIntegerField(blank=True, default=0)
    selector = models.JSONField(default=dict)
    log_files = models.JSONField(default=list)
    status = models.CharField(max_length=1000, choices=JobStatus.choices)
    start_date = models.DateTimeField(null=True, default=None)
    finish_date = models.DateTimeField(db_index=True, null=True, default=None)

    __error_code__ = "JOB_NOT_FOUND"

    class Meta:
        ordering = ["id"]

    def cook_reason(self):
        return MessageTemplate.get_message_from_template(
            KnownNames.LOCKED_BY_JOB.value,
            job=self,
            target=self.task.task_object,
        )

    def cancel(self):
        if self.sub_action and not self.sub_action.allowed_to_terminate:
            raise AdcmEx("JOB_TERMINATION_ERROR", f"Job #{self.pk} can not be terminated")

        if self.status != JobStatus.RUNNING or self.pid == 0:
            raise AdcmEx(
                "JOB_TERMINATION_ERROR",
                f"Can't terminate job #{self.pk}, pid: {self.pid} with status {self.status}",
            )
        try:
            os.kill(self.pid, signal.SIGTERM)
        except OSError as e:
            raise AdcmEx("NOT_ALLOWED_TERMINATION", f"Failed to terminate process: {e}") from e

    @property
    def duration(self) -> float | None:
        if self.finish_date is None or self.start_date is None:
            return None

        return (self.finish_date - self.start_date).total_seconds()


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
    type = models.CharField(max_length=1000, choices=LOG_TYPE)
    format = models.CharField(max_length=1000, choices=FORMAT_TYPE)

    __error_code__ = "LOG_NOT_FOUND"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["job"], condition=models.Q(type="check"), name="unique_check_job"),
        ]


class StagePrototype(ADCMModel):
    type = models.CharField(max_length=1000, choices=ObjectType.choices)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, default=None)
    name = models.CharField(max_length=1000)
    path = models.CharField(max_length=1000, default="")
    display_name = models.CharField(max_length=1000, blank=True)
    version = models.CharField(max_length=1000)
    edition = models.CharField(max_length=1000, default="community")
    license = models.CharField(max_length=1000, choices=LICENSE_STATE, default="absent")
    license_path = models.CharField(max_length=1000, default=None, null=True)
    license_hash = models.CharField(max_length=1000, default=None, null=True)
    required = models.BooleanField(default=False)
    shared = models.BooleanField(default=False)
    constraint = models.JSONField(default=get_default_constraint)
    requires = models.JSONField(default=list)
    bound_to = models.JSONField(default=dict)
    adcm_min_version = models.CharField(max_length=1000, default=None, null=True)
    description = models.TextField(blank=True)
    monitoring = models.CharField(max_length=1000, choices=MONITORING_TYPE, default="active")
    config_group_customization = models.BooleanField(default=False)
    venv = models.CharField(default="default", max_length=1000, blank=False)
    allow_maintenance_mode = models.BooleanField(default=False)
    allow_flags = models.BooleanField(default=False)

    __error_code__ = "PROTOTYPE_NOT_FOUND"

    def __str__(self):
        return str(self.name)

    class Meta:
        unique_together = (("type", "parent", "name", "version"),)


class StageUpgrade(ADCMModel):
    name = models.CharField(max_length=1000, blank=True)
    display_name = models.CharField(max_length=1000, blank=True)
    description = models.TextField(blank=True)
    min_version = models.CharField(max_length=1000)
    max_version = models.CharField(max_length=1000)
    min_strict = models.BooleanField(default=False)
    max_strict = models.BooleanField(default=False)
    from_edition = models.JSONField(default=get_default_from_edition)
    state_available = models.JSONField(default=list)
    state_on_success = models.CharField(max_length=1000, blank=True)
    action = models.OneToOneField("StageAction", on_delete=models.CASCADE, null=True)


class StageAction(AbstractAction):
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)


class StageSubAction(AbstractSubAction):
    action = models.ForeignKey(StageAction, on_delete=models.CASCADE)


class StagePrototypeConfig(ADCMModel):
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)
    action = models.ForeignKey(StageAction, on_delete=models.CASCADE, null=True, default=None)
    name = models.CharField(max_length=1000)
    subname = models.CharField(max_length=1000, blank=True)
    default = models.TextField(blank=True)
    type = models.CharField(max_length=1000, choices=CONFIG_FIELD_TYPE)
    display_name = models.CharField(max_length=1000, blank=True)
    description = models.TextField(blank=True)
    limits = models.JSONField(default=dict)
    ui_options = models.JSONField(blank=True, default=dict)
    required = models.BooleanField(default=True)
    group_customization = models.BooleanField(null=True)

    class Meta:
        ordering = ["id"]
        unique_together = (("prototype", "action", "name", "subname"),)


class StagePrototypeExport(ADCMModel):
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=1000)

    class Meta:
        unique_together = (("prototype", "name"),)


class StagePrototypeImport(ADCMModel):
    prototype = models.ForeignKey(StagePrototype, on_delete=models.CASCADE)
    name = models.CharField(max_length=1000)
    min_version = models.CharField(max_length=1000)
    max_version = models.CharField(max_length=1000)
    min_strict = models.BooleanField(default=False)
    max_strict = models.BooleanField(default=False)
    default = models.JSONField(null=True, default=None)
    required = models.BooleanField(default=False)
    multibind = models.BooleanField(default=False)

    class Meta:
        unique_together = (("prototype", "name"),)


class KnownNames(Enum):
    LOCKED_BY_JOB = "locked by running job on target"  # kwargs=(job, target)
    CONFIG_ISSUE = "object config issue"  # kwargs=(source, )
    REQUIRED_SERVICE_ISSUE = "required service issue"  # kwargs=(source, )
    REQUIRED_IMPORT_ISSUE = "required import issue"  # kwargs=(source, )
    HOST_COMPONENT_ISSUE = "host component issue"  # kwargs=(source, )
    UNSATISFIED_REQUIREMENT_ISSUE = "unsatisfied service requirement"  # kwargs=(source, )
    CONFIG_FLAG = "outdated configuration flag"  # kwargs=(source, )


class PlaceHolderType(Enum):
    ACTION = "action"
    JOB = "job"
    ADCM_ENTITY = "adcm_entity"
    ADCM = "adcm"
    CLUSTER = "cluster"
    SERVICE = "service"
    COMPONENT = "component"
    PROVIDER = "provider"
    HOST = "host"
    PROTOTYPE = "prototype"


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
    """

    name = models.CharField(max_length=1000, unique=True)
    template = models.JSONField()

    @classmethod
    def get_message_from_template(cls, name: KnownNames, **kwargs) -> dict:
        """Find message template by its name and fill placeholders"""

        tpl = cls.obj.get(name=name).template
        filled_placeholders = {}
        try:
            for ph_name, ph_data in tpl["placeholder"].items():
                filled_placeholders[ph_name] = cls._fill_placeholder(ph_name, ph_data, **kwargs)
        except (KeyError, AttributeError, TypeError, AssertionError) as e:
            if isinstance(e, KeyError):
                msg = f'Message templating KeyError: "{e.args[0]}" not found'
            elif isinstance(e, AttributeError):
                msg = f'Message templating AttributeError: "{e.args[0]}"'
            elif isinstance(e, TypeError):
                msg = f'Message templating TypeError: "{e.args[0]}"'
            elif isinstance(e, AssertionError):
                msg = "Message templating AssertionError: expected kwarg were not found"
            else:
                msg = None
            raise AdcmEx("MESSAGE_TEMPLATING_ERROR", msg=msg) from e

        tpl["placeholder"] = filled_placeholders

        return tpl

    @classmethod
    def _fill_placeholder(cls, ph_name: str, ph_data: dict, **ph_source_data) -> dict:
        type_map = {
            PlaceHolderType.ACTION.value: cls._action_placeholder,
            PlaceHolderType.ADCM_ENTITY.value: cls._adcm_entity_placeholder,
            PlaceHolderType.ADCM.value: cls._adcm_entity_placeholder,
            PlaceHolderType.CLUSTER.value: cls._adcm_entity_placeholder,
            PlaceHolderType.SERVICE.value: cls._adcm_entity_placeholder,
            PlaceHolderType.COMPONENT.value: cls._adcm_entity_placeholder,
            PlaceHolderType.PROVIDER.value: cls._adcm_entity_placeholder,
            PlaceHolderType.HOST.value: cls._adcm_entity_placeholder,
            PlaceHolderType.JOB.value: cls._job_placeholder,
            PlaceHolderType.PROTOTYPE.value: cls._prototype_placeholder,
        }
        return type_map[ph_data["type"]](ph_name, **ph_source_data)

    @classmethod
    def _action_placeholder(cls, _, **kwargs) -> dict:
        action = kwargs.get("action")
        target = kwargs.get("target")
        if not target or not action:
            return {}

        ids = target.get_id_chain()
        ids["action_id"] = action.pk
        return {
            "type": PlaceHolderType.ACTION.value,
            "name": action.display_name,
            "params": ids,
        }

    @classmethod
    def _prototype_placeholder(cls, _, **kwargs) -> dict:
        proto = kwargs.get("target")

        if proto:
            return {
                "params": {"prototype_id": proto.id},
                "type": "prototype",
                "name": proto.display_name or proto.name,
            }

        return {}

    @classmethod
    def _adcm_entity_placeholder(cls, ph_name, **kwargs) -> dict:
        obj = kwargs.get(ph_name)
        if not obj:
            return {}

        return {
            "type": obj.prototype.type,
            "name": obj.display_name,
            "params": obj.get_id_chain(),
        }

    @classmethod
    def _job_placeholder(cls, _, **kwargs) -> dict:
        job = kwargs.get("job")
        action = job.sub_action or job.action

        if not job:
            return {}

        return {
            "type": PlaceHolderType.JOB.value,
            "name": action.display_name or action.name,
            "params": {"job_id": job.task.id},
        }


class ConcernType(models.TextChoices):
    LOCK = "lock", "lock"
    ISSUE = "issue", "issue"
    FLAG = "flag", "flag"


class ConcernCause(models.TextChoices):
    CONFIG = "config", "config"
    JOB = "job", "job"
    HOSTCOMPONENT = "host-component", "host-component"
    IMPORT = "import", "import"
    SERVICE = "service", "service"
    REQUIREMENT = "requirement", "requirement"


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
    `related_objects` are back-refs from affected `ADCMEntities.concerns`
    """

    type = models.CharField(max_length=1000, choices=ConcernType.choices, default=ConcernType.LOCK)
    name = models.CharField(max_length=1000, null=True, unique=True)
    reason = models.JSONField(default=dict)
    blocking = models.BooleanField(default=True)
    owner_id = models.PositiveIntegerField(null=True)
    owner_type = models.ForeignKey(ContentType, null=True, on_delete=models.CASCADE)
    owner = GenericForeignKey("owner_type", "owner_id")
    cause = models.CharField(max_length=1000, null=True, choices=ConcernCause.choices)

    @property
    def related_objects(self) -> Iterable[ADCMEntity]:
        """List of objects that has that item in concerns"""
        return chain(
            self.adcm_entities.order_by("id"),
            self.cluster_entities.order_by("id"),
            self.clusterobject_entities.order_by("id"),
            self.servicecomponent_entities.order_by("id"),
            self.hostprovider_entities.order_by("id"),
            self.host_entities.order_by("id"),
        )


class ADCMEntityStatus(models.TextChoices):
    UP = "up", "up"
    DOWN = "down", "down"


MainObject: TypeAlias = Cluster | ClusterObject | ServiceComponent | HostProvider | Host

_CMObjects = ADCM | MainObject | Bundle | Prototype | ConfigLog | GroupConfig | Action | Upgrade | TaskLog | JobLog

CM_MODEL_MAP: dict[str, type[_CMObjects]] = {
    "adcm": ADCM,
    "cluster": Cluster,
    "clusters": Cluster,
    "service": ClusterObject,
    "services": ClusterObject,
    "component": ServiceComponent,
    "components": ServiceComponent,
    "provider": HostProvider,
    "providers": HostProvider,
    "hostprovider": HostProvider,
    "hostproviders": HostProvider,
    "host": Host,
    "hosts": Host,
    "config": ConfigLog,
    "action": Action,
    "upgrade": Upgrade,
    "task": TaskLog,
    "job": JobLog,
    "group_config": GroupConfig,
    "config-group": GroupConfig,
    "config-groups": GroupConfig,
    "prototype": Prototype,
    "prototypes": Prototype,
    "bundle": Bundle,
    "bundles": Bundle,
}


def get_cm_model_by_type(object_type: str) -> type[_CMObjects]:
    return CM_MODEL_MAP[object_type]


def get_model_by_type(object_type):
    try:
        return get_cm_model_by_type(object_type=object_type)
    except KeyError:
        # This function should return a Model, this is necessary for the correct
        # construction of the schema.
        return Cluster
