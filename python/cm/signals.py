from audit.utils import mark_deleted_audit_object
from cm.models import (
    Bundle,
    Cluster,
    ClusterObject,
    ConfigLog,
    GroupConfig,
    Host,
    HostProvider,
    ADCM,
    ServiceComponent,
)
from django.db.models.signals import post_delete
from django.dispatch import receiver


@receiver(post_delete, sender=ADCM)
@receiver(post_delete, sender=Bundle)
@receiver(post_delete, sender=Cluster)
@receiver(post_delete, sender=ClusterObject)
@receiver(post_delete, sender=ConfigLog)
@receiver(post_delete, sender=GroupConfig)
@receiver(post_delete, sender=Host)
@receiver(post_delete, sender=HostProvider)
@receiver(post_delete, sender=ServiceComponent)
def mark_deleted_audit_object_handler(sender, instance, **kwargs):
    mark_deleted_audit_object(instance)
