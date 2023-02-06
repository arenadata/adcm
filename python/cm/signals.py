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

import casestyle
from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from audit.models import MODEL_TO_AUDIT_OBJECT_TYPE_MAP, AuditObject
from audit.utils import mark_deleted_audit_object
from cm.logger import logger
from cm.models import (
    ADCM,
    ADCMEntity,
    Bundle,
    Cluster,
    ClusterObject,
    GroupConfig,
    Host,
    HostProvider,
    Prototype,
    ServiceComponent,
)
from cm.status_api import post_event
from rbac.models import Group, Policy, Role, User


@receiver(post_delete, sender=Cluster)
@receiver(post_delete, sender=ClusterObject)
@receiver(post_delete, sender=ServiceComponent)
@receiver(post_delete, sender=Host)
@receiver(post_delete, sender=HostProvider)
@receiver(post_delete, sender=Bundle)
@receiver(post_delete, sender=ADCM)
@receiver(post_delete, sender=Prototype)
def mark_deleted_audit_object_handler(sender, instance, **kwargs) -> None:
    mark_deleted_audit_object(instance=instance, object_type=MODEL_TO_AUDIT_OBJECT_TYPE_MAP[sender])


@receiver(pre_save, sender=Cluster)
@receiver(pre_save, sender=Group)
@receiver(pre_save, sender=Policy)
def rename_audit_object(sender, instance, **kwargs) -> None:
    if kwargs["raw"]:
        return

    if instance.pk and sender.objects.get(pk=instance.pk).name == instance.name:
        return

    audit_obj = AuditObject.objects.filter(
        object_id=instance.pk,
        object_type=MODEL_TO_AUDIT_OBJECT_TYPE_MAP[sender],
    ).first()
    if not audit_obj:
        return

    audit_obj.object_name = instance.name
    audit_obj.save(update_fields=["object_name"])


@receiver(pre_save, sender=Host)
def rename_audit_object_host(sender, instance, **kwargs) -> None:
    if kwargs["raw"]:
        return

    if instance.pk and sender.objects.get(pk=instance.pk).fqdn == instance.fqdn:
        return

    audit_obj = AuditObject.objects.filter(
        object_id=instance.pk,
        object_type=MODEL_TO_AUDIT_OBJECT_TYPE_MAP[sender],
    ).first()
    if not audit_obj:
        return

    audit_obj.object_name = instance.fqdn
    audit_obj.save(update_fields=["object_name"])


def get_names(sender, **kwargs):
    """getting model name, module name and object"""
    if hasattr(sender, "get_endpoint"):
        name = sender.get_endpoint()
    else:
        name = casestyle.kebabcase(sender.__name__)
    return name, sender.__module__, kwargs["instance"]


def _post_event(action: str, module: str, obj) -> None:
    transaction.on_commit(lambda: post_event(event=action, obj=obj, details={"module": module}))


@receiver(post_save, sender=User)
@receiver(post_save, sender=Group)
@receiver(post_save, sender=Policy)
@receiver(post_save, sender=Role)
@receiver(post_save, sender=GroupConfig)
def model_change(sender, **kwargs):
    """post_save handler"""
    name, module, obj = get_names(sender, **kwargs)
    if "filter_out" in kwargs:
        if kwargs["filter_out"](module, name, obj):
            return

    action = "update"
    if kwargs.get("created"):
        action = "create"

    logger.info("%s %s %s #%s", action, module, name, obj.pk)
    _post_event(action=action, module=module, obj=obj)


@receiver(post_delete, sender=User)
@receiver(post_delete, sender=Group)
@receiver(post_delete, sender=Policy)
@receiver(post_delete, sender=Role)
@receiver(post_delete, sender=GroupConfig)
def model_delete(sender, **kwargs):
    """post_delete handler"""
    name, module, obj = get_names(sender, **kwargs)

    if "filter_out" in kwargs:
        if kwargs["filter_out"](module, name, obj):
            return

    action = "delete"
    logger.info("%s %s %s #%s", action, module, name, obj.pk)
    _post_event(action=action, module=module, obj=obj)


@receiver(m2m_changed, sender=GroupConfig)
@receiver(m2m_changed, sender=ADCMEntity.concerns.through)
@receiver(m2m_changed, sender=Policy)
@receiver(m2m_changed, sender=Role)
@receiver(m2m_changed, sender=User)
@receiver(m2m_changed, sender=Group)
def m2m_change(sender, **kwargs):
    """m2m_changed handler"""
    name, module, obj = get_names(sender, **kwargs)
    if "filter_out" in kwargs:
        if kwargs["filter_out"](module, name, obj):
            return

    if kwargs["action"] == "post_add":
        action = "add"
    elif kwargs["action"] == "post_remove":
        action = "delete"
    else:
        return

    logger.info("%s %s %s #%s", action, module, name, obj.pk)
    _post_event(action=action, module=module, obj=obj)
