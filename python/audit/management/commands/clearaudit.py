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

import csv
import os
from datetime import timedelta
from shutil import rmtree
from tarfile import TarFile

from audit.models import AuditLog, AuditLogOperationResult, AuditObject, AuditSession
from audit.utils import make_audit_log
from cm.adcm_config import get_adcm_config
from cm.logger import log_cron_task as log
from django.core.management.base import BaseCommand
from django.utils import timezone


# pylint: disable=protected-access
class Command(BaseCommand):
    encoding = "utf-8"
    config_key = "audit_data_retention"
    archive_base_dir = "/adcm/data/audit/"
    archive_tmp_dir = "/adcm/data/audit/tmp"
    archive_name = "audit_archive.tar.gz"
    tarfile_cfg = dict(
        read=dict(
            name=os.path.join(archive_base_dir, archive_name),
            mode="r:gz",
            encoding="utf-8",
        ),
        write=dict(
            name=os.path.join(archive_base_dir, archive_name),
            mode="w:gz",
            encoding="utf-8",
            compresslevel=9,
        ),
    )

    archive_model_postfix_map = {
        AuditLog: "operations",
        AuditSession: "logins",
        AuditObject: "objects",
    }

    def handle(self, *args, **options):
        try:
            _, config = get_adcm_config(self.config_key)
            if config["retention_period"] <= 0:
                self.__log("Disabled")
                return

            threshold_date = timezone.now() - timedelta(days=config["retention_period"])
            self.__log(f"Started. Threshold date: {threshold_date}")

            # get delete candidates
            target_operations = AuditLog.objects.filter(operation_time__lt=threshold_date)
            target_logins = AuditSession.objects.filter(login_time__lt=threshold_date)
            objects_pk_to_delete = set()
            for ao in AuditObject.objects.filter(is_deleted=True):
                if not ao.auditlog_set.exclude(
                    pk__in=target_operations.values_list("pk", flat=True)
                ).exists():
                    objects_pk_to_delete.add(ao.pk)
            target_objects = AuditObject.objects.filter(pk__in=objects_pk_to_delete)

            cleared = False
            if any(qs.exists() for qs in (target_operations, target_logins, target_objects)):
                make_audit_log("audit", AuditLogOperationResult.Success, "launched")

            if config["data_archiving"]:
                archive_path = os.path.join(self.archive_base_dir, self.archive_name)
                self.__log(f"Target audit records will be archived to `{archive_path}`")
                self.__archive(target_operations, target_logins, target_objects)
            else:
                self.__log("Archiving is disabled")

            cleared = self.__delete(target_operations, target_logins, target_objects)

            self.__log("Finished.")
            if cleared:
                make_audit_log("audit", AuditLogOperationResult.Success, "completed")

        except Exception as e:  # pylint: disable=broad-except
            make_audit_log("audit", AuditLogOperationResult.Fail, "completed")
            self.__log(e, "exception")

    def __archive(self, *querysets):
        os.makedirs(self.archive_base_dir, exist_ok=True)
        os.makedirs(self.archive_tmp_dir, exist_ok=True)

        qs_model_names = ", ".join([qs.model._meta.object_name for qs in querysets])
        self.__log(f"Archiving {qs_model_names}")

        self.__extract_to_tmp_dir()
        csv_files = self.__prepare_csvs(*querysets, base_dir=self.archive_tmp_dir)
        if not csv_files:
            self.__log("No targets for archiving")
        else:
            csv_filenames = ", ".join([f"`{os.path.basename(filepath)}`" for filepath in csv_files])
            self.__log(f"Files `{csv_filenames}` will be added to archive `{self.archive_name}`")
        self.__archive_tmp_dir()

    def __delete(self, *querysets):
        was_deleted = False
        for qs in querysets:
            self.__log(f"Deleting {qs.count()} {qs.model._meta.object_name}")
            if qs.exists():
                qs.delete()
                was_deleted = True
        return was_deleted

    def __extract_to_tmp_dir(self):
        if not os.path.exists(self.tarfile_cfg["read"]["name"]):
            return
        with TarFile.open(**self.tarfile_cfg["read"]) as tar:
            tar.extractall(path=self.archive_tmp_dir)
        os.remove(self.tarfile_cfg["read"]["name"])

    def __archive_tmp_dir(self):
        with TarFile.open(**self.tarfile_cfg["write"]) as tar:
            for f in os.listdir(self.archive_tmp_dir):
                tar.add(name=os.path.join(self.archive_tmp_dir, f), arcname=f)
        rmtree(self.archive_tmp_dir, ignore_errors=True)

    def __prepare_csvs(self, *querysets, base_dir):
        now = timezone.now().date()

        csv_files = []
        for qs in querysets:
            if not qs.exists():
                continue

            tmp_cvf_name = self.__get_csv_name(qs, now, base_dir)
            with open(tmp_cvf_name, "wt", newline="", encoding=self.encoding) as csv_file:
                writer = csv.writer(csv_file)

                fields = [f.column for f in qs.model._meta.fields]
                writer.writerow(fields)  # header

                for obj in qs:
                    row = [str(getattr(obj, f)) for f in fields]
                    writer.writerow(row)

            csv_files.append(tmp_cvf_name)

        return csv_files

    def __get_csv_name(self, queryset, now, base_dir):
        tmp_cvf_name = os.path.join(
            base_dir,
            f"audit_{now}_{self.archive_model_postfix_map[queryset.model]}.csv",
        )
        if os.path.exists(tmp_cvf_name):
            os.remove(tmp_cvf_name)

        return tmp_cvf_name

    def __log(self, msg, method="info"):
        prefix = "Audit cleanup/archiving: "
        if method in ("exc", "exception"):
            log.warning("%sError in auditlog rotation", prefix)
            log.exception(msg)
        else:
            msg = "Audit cleanup/archiving: " + str(msg)
            self.stdout.write(msg)
            getattr(log, method)(msg)
