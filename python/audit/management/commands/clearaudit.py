import csv
import os
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from cm.logger import log_cron_task as log
from cm.adcm_config import get_adcm_config
from audit.models import AuditLog, AuditObject, AuditSession


# pylint: disable=protected-access
class Command(BaseCommand):
    encoding = 'utf-8'
    config_key = 'audit_data_retention'
    archive_path = '/adcm/data/audit/archive.tgz'
    archive_model_postfix_map = {
        AuditLog._meta.object_name: 'operations',
        AuditSession._meta.object_name: 'logins',
    }

    def handle(self, *args, **options):
        _, config = get_adcm_config(self.config_key)
        if config['retention_period'] <= 0:
            self.__log('Disabled')
            return

        threshold_date = timezone.now() - timedelta(days=config['retention_period'])
        self.__log(f'Started. Threshold date: {threshold_date}')

        target_operations = AuditLog.objects.filter(operation_time__lt=threshold_date)
        target_logins = AuditSession.objects.filter(login_time__lt=threshold_date)

        if config['data_archiving']:
            self.__log(f'Target audit records will be archived to `{self.archive_path}`')
            self.__archive(target_operations, target_logins)
        else:
            self.__log('Archiving is disabled')

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

    def __archive(self, *querysets):
        base_archive_dir = os.path.dirname(self.archive_path)
        os.makedirs(base_archive_dir, exist_ok=True)
        csv_files = self.__prepare_csvs(*querysets, base_dir=base_archive_dir)
        pass  # TODO
        for csv_file in csv_files:
            os.remove(csv_file)

    def __prepare_csvs(self, *querysets, base_dir):
        now = timezone.now().date()

        csv_files = []
        for qs in querysets:
            if not qs.exists():
                continue

            tmp_cvf_name = self.__get_csv_name(qs, now, base_dir)
            with open(tmp_cvf_name, 'wt', newline='', encoding=self.encoding) as csv_file:
                writer = csv.writer(csv_file)

                field_names = [f.name for f in qs.model._meta.get_fields()]
                writer.writerow(field_names)  # header

                for obj in qs:
                    row = [str(getattr(obj, fn)) for fn in field_names]
                    writer.writerow(row)

            csv_files.append(tmp_cvf_name)

        return csv_files

    def __get_csv_name(self, queryset, now, base_dir):
        tmp_cvf_name = os.path.join(
            base_dir,
            f'audit_{now}_{self.archive_model_postfix_map[queryset.model._meta.object_name]}.csv',
        )
        if os.path.exists(tmp_cvf_name):
            os.remove(tmp_cvf_name)

        return tmp_cvf_name

    def __log(self, msg):
        msg = 'Audit cleanup/archiving: ' + str(msg)
        self.stdout.write(msg)
        log.info(msg)
