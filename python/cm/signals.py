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

from audit.models import MODEL_TO_AUDIT_OBJECT_TYPE_MAP, AuditObject
from casestyle import kebabcase
from cm.models import ADCMEntity, Cluster, GroupConfig, Host
from cm.status_api import post_event
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.db.transaction import on_commit
from django.dispatch import receiver
from rbac.models import Group, Policy, Role, User


@receiver(signal=pre_save, sender=Cluster)
@receiver(signal=pre_save, sender=Group)
@receiver(signal=pre_save, sender=Policy)
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


@receiver(signal=pre_save, sender=Host)
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


@receiver(signal=post_save, sender=User)
@receiver(signal=post_save, sender=Group)
@receiver(signal=post_save, sender=Policy)
@receiver(signal=post_save, sender=Role)
@receiver(signal=post_save, sender=GroupConfig)
def model_change(sender, **kwargs):
    if kwargs["raw"]:
        return

    action = "update"
    if kwargs.get("created"):
        action = "create"

    on_commit(
        lambda: post_event(
            event=action, obj=kwargs["instance"], details={"module": sender.__module__, "model_name": None}
        ),
    )


@receiver(signal=post_delete, sender=User)
@receiver(signal=post_delete, sender=Group)
@receiver(signal=post_delete, sender=Policy)
@receiver(signal=post_delete, sender=Role)
@receiver(signal=post_delete, sender=GroupConfig)
def model_delete(sender, **kwargs):
    on_commit(
        lambda: post_event(
            event="delete", obj=kwargs["instance"], details={"module": sender.__module__, "model_name": None}
        ),
    )


@receiver(signal=m2m_changed, sender=GroupConfig)
@receiver(signal=m2m_changed, sender=ADCMEntity.concerns.through)
@receiver(signal=m2m_changed, sender=Policy)
@receiver(signal=m2m_changed, sender=Role)
@receiver(signal=m2m_changed, sender=User)
@receiver(signal=m2m_changed, sender=Group)
def m2m_change(sender, **kwargs):
    if hasattr(sender, "get_endpoint"):
        name = sender.get_endpoint()
    else:
        name = kebabcase(sender.__name__)

    if kwargs["action"] == "post_add":
        action = "add"
    elif kwargs["action"] == "post_remove":
        action = "delete"
    else:
        return

    on_commit(
        lambda: post_event(
            event=action, obj=kwargs["instance"], details={"module": sender.__module__, "model_name": name}
        ),
    )
