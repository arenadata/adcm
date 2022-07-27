from datetime import timedelta
from pprint import pformat

from django.core.management.base import BaseCommand
from django.utils import timezone

from cm.logger import log_cron_task as log
from cm.models import ADCM, ConfigLog
from cm.adcm_config import get_adcm_config
from audit.models import AuditLog, AuditObject, AuditSession


class Command(BaseCommand):
    config_key = 'audit_data_retention'
    archive_path = None  # TODO

    def handle(self, *args, **options):
        _, config = get_adcm_config(self.config_key)
        if config['retention_period'] <= 0:
            self.__log('Audit cleanup is disabled')
            return

        threshold_date = timezone.now() - timedelta(days=config['retention_period'])
        self.__log(f'Audit cleanup started. Threshold date: {threshold_date}')

        target_operations = AuditLog.objects.filter(operation_time__lt=threshold_date)
        target_logins = AuditSession.objects.filter(login_time__lt=threshold_date)

        if config['data_archiving']:
            self.__log(f'Target audit records will be archived to `{self.archive_path}`')
            pass  # TODO: archive .tgz
        else:
            self.__log(f'Archiving is disabled')

        self.__log(f'Deleting {target_operations.count()} AuditLog')
        target_operations.delete()
        self.__log(f'Deleting {target_logins.count()} AuditSession')
        target_logins.delete()

        objects_pk_to_delete = set()
        for ao in AuditObject.objects.filter(is_deleted=True):
            if not ao.auditlog_set.exists():
                objects_pk_to_delete.add(ao.pk)
        target_objects = AuditObject.objects.filter(pk__in=objects_pk_to_delete)

        self.__log(f'Deleting {target_objects.count()} AuditObject')
        target_objects.delete()

    def __log(self, msg):
        msg = str(msg)
        self.stdout.write(msg)
        log.info(msg)
