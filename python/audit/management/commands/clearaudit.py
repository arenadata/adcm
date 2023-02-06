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
import logging
import os
from datetime import timedelta
from pathlib import Path
from shutil import rmtree
from tarfile import TarFile

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.utils import timezone

from audit.models import AuditLog, AuditLogOperationResult, AuditObject, AuditSession
from audit.utils import make_audit_log
from cm.adcm_config import get_adcm_config

logger = logging.getLogger("background_tasks")


# pylint: disable=protected-access
class Command(BaseCommand):
    config_key = "audit_data_retention"
    archive_base_dir = "/adcm/data/audit/"
    archive_tmp_dir = "/adcm/data/audit/tmp"
    archive_name = "audit_archive.tar.gz"
    tarfile_cfg = {
        "read": {
            "name": os.path.join(archive_base_dir, archive_name),
            "mode": "r:gz",
            "encoding": settings.ENCODING_UTF_8,
        },
        "write": {
            "name": os.path.join(archive_base_dir, archive_name),
            "mode": "w:gz",
            "encoding": settings.ENCODING_UTF_8,
            "compresslevel": 9,
        },
    }

    archive_model_postfix_map = {
        AuditLog: "operations",
        AuditSession: "logins",
        AuditObject: "objects",
    }

    def handle(self, *args, **options):
        try:
            self.__handle()
        except Exception as e:  # pylint: disable=broad-except
            make_audit_log("audit", AuditLogOperationResult.FAIL, "completed")
            self.__log(e, "exception")

    def __handle(self):
        _, config = get_adcm_config(self.config_key)
        if config["retention_period"] <= 0:
            self.__log("Disabled")
            return

        threshold_date = timezone.now() - timedelta(days=config["retention_period"])
        self.__log(f"Started. Threshold date: {threshold_date}")

        # get delete candidates
        target_operations = AuditLog.objects.filter(operation_time__lt=threshold_date)
        target_logins = AuditSession.objects.filter(login_time__lt=threshold_date)
        target_objects = (
            AuditObject.objects.filter(is_deleted=True)
            .annotate(not_deleted_auditlogs_count=Count("auditlog", filter=~Q(auditlog__in=target_operations)))
            .filter(not_deleted_auditlogs_count__lte=0)
        )

        cleared = False
        if any(qs.exists() for qs in (target_operations, target_logins, target_objects)):
            make_audit_log("audit", AuditLogOperationResult.SUCCESS, "launched")

        if config["data_archiving"]:
            archive_path = os.path.join(self.archive_base_dir, self.archive_name)
            self.__log(f"Target audit records will be archived to `{archive_path}`")
            self.__archive(target_operations, target_logins, target_objects)
        else:
            self.__log("Archiving is disabled")

        cleared = self.__delete(target_operations, target_logins, target_objects)

        self.__log("Finished.")
        if cleared:
            make_audit_log("audit", AuditLogOperationResult.SUCCESS, "completed")

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
            self.__log(f"Files {csv_filenames} will be added to archive `{self.archive_name}`")
        self.__archive_tmp_dir()

    def __delete(self, *querysets):
        was_deleted = False
        for queryset in querysets:
            self.__log(f"Deleting {queryset.count()} {queryset.model._meta.object_name}")
            if queryset.exists():
                queryset.delete()
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
        for queryset in querysets:
            if not queryset.exists():
                continue

            tmp_cvf_name = os.path.join(
                base_dir,
                f"audit_{now}_{self.archive_model_postfix_map[queryset.model]}.csv",
            )
            header = self.__get_csv_header(tmp_cvf_name)
            qs_fields = [f.column for f in queryset.model._meta.fields]
            if header:
                if set(header) != set(qs_fields):
                    self.__log(
                        f"Fields of {queryset.model._meta.object_name} was changed, "
                        f"can't append to existing file. No archiving will be made",
                        "warning",
                    )
                    continue
                qs_fields = header

            mode = "at" if header else "wt"
            with open(tmp_cvf_name, mode, newline="", encoding=settings.ENCODING_UTF_8) as csv_file:
                writer = csv.writer(csv_file)

                if header is None:
                    writer.writerow(qs_fields)  # header

                for obj in queryset:
                    row = [str(getattr(obj, f)) for f in qs_fields]
                    writer.writerow(row)

            csv_files.append(tmp_cvf_name)

        return csv_files

    def __get_csv_header(self, path):
        header = None
        if Path(path).is_file():
            with open(path, "rt", encoding=settings.ENCODING_UTF_8) as csv_file:
                header = csv_file.readline().strip().split(",")
        return header

    def __log(self, msg, method="info"):
        prefix = "Audit cleanup/archiving:"
        if method in ("exc", "exception"):
            logger.warning("%s Error in auditlog rotation", prefix)
            logger.exception(msg)
        else:
            msg = f"{prefix} {msg}"
            self.stdout.write(msg)
            getattr(logger, method)(msg)
