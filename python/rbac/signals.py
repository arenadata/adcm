from audit.utils import mark_deleted_audit_object
from django.db.models.signals import post_delete
from django.dispatch import receiver
from rbac.models import Group, Policy, Role, User
from rest_framework.authtoken.models import Token


@receiver(post_delete, sender=User)
@receiver(post_delete, sender=Group)
@receiver(post_delete, sender=Policy)
@receiver(post_delete, sender=Role)
@receiver(post_delete, sender=Token)
def mark_deleted_audit_object_handler(sender, instance, **kwargs):
    mark_deleted_audit_object(instance)
