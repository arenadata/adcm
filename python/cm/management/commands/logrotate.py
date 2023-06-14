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
import logging
import os
import shutil
from datetime import datetime, timedelta
from enum import Enum
from subprocess import STDOUT, CalledProcessError, check_output

from audit.models import AuditLogOperationResult
from audit.utils import make_audit_log
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
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("background_tasks")


LOGROTATE_CONF_FILE_TEMPLATE = """
/adcm/data/log/nginx/*.log {{
        su root root
        size {size}
        missingok
        nomail
        {no_compress}compress
        {no_compress}delaycompress
        rotate {num_rotations}
        sharedscripts
        postrotate
                kill -USR1 `cat /run/nginx/nginx.pid`
        endscript
}}
"""


class TargetType(Enum):
    ALL = "all"
    JOB = "job"
    CONFIG = "config"
    NGINX = "nginx"


class Command(BaseCommand):
    help = "Delete / rotate log files, db records, `run` directories"

    __nginx_logrotate_conf = "/etc/logrotate.d/nginx"
    __logrotate_cmd = f"logrotate {__nginx_logrotate_conf}"
    __logrotate_cmd_debug = f"{__logrotate_cmd} -v"

    def add_arguments(self, parser):
        parser.add_argument(
            "--target",
            choices=[i.value for i in TargetType],
            default=TargetType.ALL.value,
            help=f"Rotation target. Must be one of: {[i.value for i in TargetType]}",
        )
        parser.add_argument("--disable_logs", action="store_true", help="Disable logging")

    def handle(self, *args, **options):
        __target_method_map = {
            TargetType.ALL.value: [
                self.__run_nginx_log_rotation,
                self.__run_joblog_rotation,
                self.__run_configlog_rotation,
            ],
            TargetType.JOB.value: [self.__run_joblog_rotation],
            TargetType.CONFIG.value: [self.__run_configlog_rotation],
            TargetType.NGINX.value: [self.__run_nginx_log_rotation],
        }

        # pylint: disable=attribute-defined-outside-init
        self.verbose = not options["disable_logs"]
        target = options["target"]
        self.config = self.__get_logrotate_config()
        self.__log(f"Running logrotation for `{target}` target", "info")
        for func in __target_method_map[target]:
            func()

    def __execute_cmd(self, cmd):
        self.__log(f"executing cmd: `{cmd}`", "info")
        try:
            out = check_output(cmd, shell=True, stderr=STDOUT)
            out = out.decode(settings.ENCODING_UTF_8).strip("\n")
            if out:
                self.__log(out, "debug")
        except CalledProcessError as e:
            err_msg = e.stdout.decode(settings.ENCODING_UTF_8).strip("\n")
            msg = f"Error! cmd: `{cmd}` return code: `{e.returncode}` msg: `{err_msg}`"
            self.__log(msg, "exception")

    def __get_logrotate_config(self):
        adcm_object = ADCM.objects.first()
        current_configlog = ConfigLog.objects.get(obj_ref=adcm_object.config, id=adcm_object.config.current)
        adcm_conf = current_configlog.config
        logrotate_config = {
            "logrotate": {
                "active": current_configlog.attr["logrotate"]["active"],
                "nginx": adcm_conf["logrotate"],
            },
            "job": adcm_conf["job_log"],
            "config": adcm_conf["config_rotation"],
        }
        self.__log(f"Got rotation config: {logrotate_config}")
        return logrotate_config

    def __generate_logrotate_conf_file(self):
        conf_file_args = {
            "size": f"{self.config['logrotate']['nginx']['size']}",
            "no_compress": "" if self.config["logrotate"]["nginx"]["compress"] else "#",
            "num_rotations": self.config["logrotate"]["nginx"]["max_history"],
        }
        with open(self.__nginx_logrotate_conf, "w", encoding=settings.ENCODING_UTF_8) as conf_file:
            conf_file.write(LOGROTATE_CONF_FILE_TEMPLATE.format(**conf_file_args))
        self.__log(f"conf file `{self.__nginx_logrotate_conf}` generated", "debug")

    def __run_nginx_log_rotation(self):
        if self.config["logrotate"]["active"]:
            self.__log("Nginx log rotation started", "info")
            self.__generate_logrotate_conf_file()
            self.__log(
                f"Using config file `{self.__nginx_logrotate_conf}`",
                "debug",
            )
            if self.verbose:
                self.__execute_cmd(self.__logrotate_cmd_debug)
            self.__execute_cmd(self.__logrotate_cmd)

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

        except Exception as e:  # pylint: disable=broad-except
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
        try:  # pylint: disable=too-many-nested-blocks
            days_delta_db = self.config["job"]["log_rotation_in_db"]
            days_delta_fs = self.config["job"]["log_rotation_on_fs"]
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
            if days_delta_fs > 0:  # pylint: disable=too-many-nested-blocks
                for name in os.listdir(settings.RUN_DIR):
                    if not name.startswith("."):  # a line of code is used for development
                        path = settings.RUN_DIR / name
                        try:
                            m_time = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.get_current_timezone())
                            if timezone.now() - m_time > timedelta(days=days_delta_fs):
                                is_deleted = True
                                if os.path.isdir(path):
                                    shutil.rmtree(path)
                                else:
                                    os.remove(path)
                        except FileNotFoundError:
                            pass
                if is_deleted:
                    make_audit_log("task", AuditLogOperationResult.SUCCESS, "launched")
                    make_audit_log("task", AuditLogOperationResult.SUCCESS, "completed")
                self.__log("fs JobLog rotated", "info")
        except Exception as e:  # pylint: disable=broad-except
            make_audit_log("task", AuditLogOperationResult.FAIL, "completed")
            self.__log("Error in JobLog rotation", "warning")
            self.__log(e, "exception")

    def __log(self, msg, method="debug"):
        self.stdout.write(msg)
        if self.verbose:
            getattr(logger, method)(msg)
