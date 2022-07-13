from django.db.models.signals import m2m_changed, post_delete
from django.dispatch import receiver

from cm.models.cluster import ServiceComponent
from cm.models.objects import GroupConfig, Host


@receiver(post_delete, sender=ServiceComponent)
def auto_delete_config_with_servicecomponent(sender, instance, **kwargs):
    if instance.config is not None:
        instance.config.delete()


@receiver(m2m_changed, sender=GroupConfig.hosts.through)
def verify_host_candidate_for_group_config(sender, **kwargs):
    """Checking host candidate for group config before add to group"""
    group_config = kwargs.get('instance')
    action = kwargs.get('action')
    host_ids = kwargs.get('pk_set')

    if action == 'pre_add':
        for host_id in host_ids:
            host = Host.objects.get(id=host_id)
            group_config.check_host_candidate(host)