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

from datetime import datetime, timedelta
from enum import Enum
import os
import shutil
import logging

from audit.models import AuditLogOperationResult
from audit.utils import make_audit_log
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from cm.models import (
    ADCM,
    Cluster,
    ClusterObject,
    ConfigLog,
    GroupConfig,
    Host,
    HostProvider,
    JobLog,
    ObjectConfig,
    ServiceComponent,
    TaskLog,
)

logger = logging.getLogger("background_tasks")


class TargetType(Enum):
    ALL = "all"
    JOB = "job"
    CONFIG = "config"


class Command(BaseCommand):
    help = "Delete / rotate log files, db records, `run` directories"

    def add_arguments(self, parser):
        parser.add_argument(
            "--target",
            choices=[i.value for i in TargetType],
            default=TargetType.ALL.value,
            help=f"Rotation target. Must be one of: {[i.value for i in TargetType]}",
        )
        parser.add_argument("--disable_logs", action="store_true", help="Disable logging")

    def handle(self, *args, **options):  # noqa: ARG002
        __target_method_map = {
            TargetType.ALL.value: [
                self.__run_joblog_rotation,
                self.__run_configlog_rotation,
            ],
            TargetType.JOB.value: [self.__run_joblog_rotation],
            TargetType.CONFIG.value: [self.__run_configlog_rotation],
        }

        self.verbose = not options["disable_logs"]
        target = options["target"]
        self.config = self.__get_logrotate_config()
        self.__log(f"Running logrotation for `{target}` target", "info")
        for func in __target_method_map[target]:
            func()

    def __get_logrotate_config(self):
        adcm_object = ADCM.objects.first()
        current_config = ConfigLog.objects.get(obj_ref=adcm_object.config, id=adcm_object.config.current).config
        logrotate_config = {
            "config": current_config["audit_data_retention"],
        }
        self.__log(f"Got rotation config: {logrotate_config}")
        return logrotate_config

    def __run_configlog_rotation(self):
        try:
            configlog_days_delta = self.config["config"]["config_rotation_in_db"]
            if configlog_days_delta <= 0:
                return

            threshold_date = timezone.now() - timedelta(days=configlog_days_delta)
            self.__log(f"ConfigLog rotation started. Threshold date: {threshold_date}", "info")

            exclude_pks = set()
            target_configlogs = ConfigLog.objects.filter(date__lte=threshold_date)
            for config_log in target_configlogs:
                for cl_pk in (config_log.obj_ref.current, config_log.obj_ref.previous):
                    exclude_pks.add(cl_pk)

            for group_config in GroupConfig.objects.order_by("id"):
                if group_config.config:
                    exclude_pks.add(group_config.config.previous)
                    exclude_pks.add(group_config.config.current)

            target_configlogs = target_configlogs.exclude(pk__in=exclude_pks)
            target_configlog_ids = {i[0] for i in target_configlogs.values_list("id")}
            target_objectconfig_ids = {
                cl.obj_ref.id for cl in target_configlogs if not self.__has_related_records(cl.obj_ref)
            }
            if target_configlog_ids or target_objectconfig_ids:
                make_audit_log("config", AuditLogOperationResult.SUCCESS, "launched")

            with transaction.atomic():
                ConfigLog.objects.filter(id__in=target_configlog_ids).delete()
                ObjectConfig.objects.filter(id__in=target_objectconfig_ids).delete()
                if target_configlog_ids or target_objectconfig_ids:
                    make_audit_log("config", AuditLogOperationResult.SUCCESS, "completed")

            self.__log(
                f"Deleted {len(target_configlog_ids)} ConfigLogs and " f"{len(target_objectconfig_ids)} ObjectConfigs",
                "info",
            )

        except Exception as e:  # noqa: BLE001
            make_audit_log("config", AuditLogOperationResult.FAIL, "completed")
            self.__log("Error in ConfigLog rotation", "warning")
            self.__log(e, "exception")

    @staticmethod
    def __has_related_records(obj_conf: ObjectConfig) -> bool:
        if (
            sum(
                [
                    ADCM.objects.filter(config=obj_conf).count(),
                    Cluster.objects.filter(config=obj_conf).count(),
                    ClusterObject.objects.filter(config=obj_conf).count(),
                    Host.objects.filter(config=obj_conf).count(),
                    HostProvider.objects.filter(config=obj_conf).count(),
                    ServiceComponent.objects.filter(config=obj_conf).count(),
                    GroupConfig.objects.filter(config=obj_conf).count(),
                ],
            )
            > 0
        ):
            return True
        return False

    def __run_joblog_rotation(self):
        try:
            days_delta_db = self.config["config"]["log_rotation_in_db"]
            days_delta_fs = self.config["config"]["log_rotation_on_fs"]
            if days_delta_db <= 0 and days_delta_fs <= 0:
                return

            threshold_date_db = timezone.now() - timedelta(days=days_delta_db)
            threshold_date_fs = timezone.now() - timedelta(days=days_delta_fs)
            self.__log(
                f"JobLog rotation started. Threshold dates: " f"db - {threshold_date_db}, fs - {threshold_date_fs}",
                "info",
            )
            is_deleted = False
            if days_delta_db > 0:
                target_tasklogs = TaskLog.objects.filter(
                    finish_date__lte=threshold_date_db,
                    status__in=["success", "failed"],
                )
                if target_tasklogs:
                    is_deleted = True
                    with transaction.atomic():
                        target_tasklogs.delete()

                        # valid as long as `on_delete=models.SET_NULL` in JobLog.task field
                        JobLog.objects.filter(task__isnull=True).delete()

                self.__log("db JobLog rotated", "info")
            if days_delta_fs > 0:
                for name in os.listdir(settings.RUN_DIR):
                    if not name.startswith("."):  # a line of code is used for development
                        path = settings.RUN_DIR / name
                        try:
                            m_time = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.get_current_timezone())  # noqa: PTH204
                            if timezone.now() - m_time > timedelta(days=days_delta_fs):
                                is_deleted = True
                                if os.path.isdir(path):  # noqa: PTH112
                                    shutil.rmtree(path)
                                else:
                                    os.remove(path)  # noqa: PTH107
                        except FileNotFoundError:
                            pass
                if is_deleted:
                    make_audit_log("task", AuditLogOperationResult.SUCCESS, "launched")
                    make_audit_log("task", AuditLogOperationResult.SUCCESS, "completed")
                self.__log("fs JobLog rotated", "info")
        except Exception as e:  # noqa: BLE001
            make_audit_log("task", AuditLogOperationResult.FAIL, "completed")
            self.__log("Error in JobLog rotation", "warning")
            self.__log(e, "exception")

    def __log(self, msg, method="debug"):
        self.stdout.write(msg)
        if self.verbose:
            getattr(logger, method)(msg)
