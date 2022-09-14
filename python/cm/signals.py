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

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from audit.models import MODEL_TO_AUDIT_OBJECT_TYPE_MAP, AuditObject
from audit.utils import mark_deleted_audit_object
from cm.models import (
    ADCM,
    Bundle,
    Cluster,
    ClusterObject,
    Host,
    HostProvider,
    ServiceComponent,
)
from rbac.models import Group, Policy


@receiver(post_delete, sender=Cluster)
@receiver(post_delete, sender=ClusterObject)
@receiver(post_delete, sender=ServiceComponent)
@receiver(post_delete, sender=Host)
@receiver(post_delete, sender=HostProvider)
@receiver(post_delete, sender=Bundle)
@receiver(post_delete, sender=ADCM)
def mark_deleted_audit_object_handler(sender, instance, **kwargs) -> None:
    mark_deleted_audit_object(instance=instance, object_type=MODEL_TO_AUDIT_OBJECT_TYPE_MAP[sender])


@receiver(pre_save, sender=Cluster)
@receiver(pre_save, sender=Group)
@receiver(pre_save, sender=Policy)
def rename_audit_object(sender, instance, **kwargs) -> None:
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
