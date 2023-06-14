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
from django.db.models.signals import post_delete
from django.dispatch import receiver


@receiver(signal=post_delete, sender=Cluster)
@receiver(signal=post_delete, sender=ClusterObject)
@receiver(signal=post_delete, sender=ServiceComponent)
@receiver(signal=post_delete, sender=Host)
@receiver(signal=post_delete, sender=HostProvider)
@receiver(signal=post_delete, sender=Bundle)
@receiver(signal=post_delete, sender=ADCM)
@receiver(signal=post_delete, sender=Prototype)
def mark_deleted_audit_object_handler(sender, instance, **kwargs) -> None:  # pylint: disable=unused-argument
    audit_objs = []
    for audit_obj in AuditObject.objects.filter(
        object_id=instance.pk, object_type=MODEL_TO_AUDIT_OBJECT_TYPE_MAP[sender]
    ):
        audit_obj.is_deleted = True
        audit_objs.append(audit_obj)

    AuditObject.objects.bulk_update(objs=audit_objs, fields=["is_deleted"])
