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

from audit.models import MODEL_TO_AUDIT_OBJECT_TYPE_MAP, AuditObject, AuditUser
from cm.models import (
    ADCM,
    Bundle,
    Cluster,
    ClusterObject,
    Host,
    HostProvider,
    Prototype,
    ServiceComponent,
)
from django.contrib.auth.models import User as AuthUser
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.timezone import now
from rbac.models import Group, Policy, Role
from rbac.models import User as RBACUser


@receiver(signal=post_delete, sender=Cluster)
@receiver(signal=post_delete, sender=ClusterObject)
@receiver(signal=post_delete, sender=ServiceComponent)
@receiver(signal=post_delete, sender=Host)
@receiver(signal=post_delete, sender=HostProvider)
@receiver(signal=post_delete, sender=Bundle)
@receiver(signal=post_delete, sender=ADCM)
@receiver(signal=post_delete, sender=Prototype)
@receiver(signal=post_delete, sender=RBACUser)
@receiver(signal=post_delete, sender=Group)
@receiver(signal=post_delete, sender=Role)
@receiver(signal=post_delete, sender=Policy)
def mark_deleted_audit_object_handler(sender, instance, **kwargs) -> None:  # pylint: disable=unused-argument
    audit_objs = []
    for audit_obj in AuditObject.objects.filter(
        object_id=instance.pk, object_type=MODEL_TO_AUDIT_OBJECT_TYPE_MAP[sender]
    ):
        audit_obj.is_deleted = True
        audit_objs.append(audit_obj)

    AuditObject.objects.bulk_update(objs=audit_objs, fields=["is_deleted"])


@receiver(signal=post_save, sender=AuthUser)
@receiver(signal=post_save, sender=RBACUser)
def create_audit_user(sender, instance, created, **kwargs):  # pylint: disable=unused-argument
    if kwargs["raw"]:
        return

    if created:
        AuditUser.objects.get_or_create(
            username=instance.username,
            created_at=instance.date_joined,
            auth_user_id=AuthUser.objects.get(username=instance.username).pk,
        )


@receiver(signal=post_delete, sender=AuthUser)
@receiver(signal=post_delete, sender=RBACUser)
def set_deleted_at_audit_user(sender, instance, **kwargs):  # pylint: disable=unused-argument
    audit_user = AuditUser.objects.filter(username=instance.username).order_by("-pk").first()
    audit_user.deleted_at = now()
    audit_user.save(update_fields=["deleted_at"])
