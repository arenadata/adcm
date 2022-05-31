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


import os
import shutil

from enum import Enum

from contextlib import suppress
from datetime import timedelta, datetime
from subprocess import Popen, PIPE

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from cm import config
from cm.logger import log_background_task as log
from cm.models import (
    ADCM,
    Cluster,
    ClusterObject,
    ConfigLog,
    DummyData,
    Host,
    HostProvider,
    JobLog,
    ObjectConfig,
    ServiceComponent,
    TaskLog,
)


class TargetType(Enum):
    ALL = 'all'
    JOB = 'job'
    CONFIG = 'config'
    NGINX = 'nginx'


class Command(BaseCommand):
    help = 'Delete / rotate log files, db records, `run` directories'
    __nginx_logrotate_conf = '/etc/logrotate.d/nginx'

    def add_arguments(self, parser):
        parser.add_argument(
            '--target',
            choices=[i.value for i in TargetType],
            default=TargetType.ALL.value,
            help=f'Rotation target. Must be one of: {[i.value for i in TargetType]}',
        )
        parser.add_argument('--disable_logs', action='store_true', help='Disable logging')

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
        self.verbose = not options['disable_logs']
        target = options['target']
        self.config = self.__get_logrotate_config()
        self.__log(f'Running logrotation for `{target}` target', 'info')
        for func in __target_method_map[target]:
            func()

    def __get_logrotate_config(self):
        adcm_object = ADCM.objects.get(id=1)
        adcm_conf = ConfigLog.objects.get(
            obj_ref=adcm_object.config, id=adcm_object.config.current
        ).config
        logrotate_config = {
            'nginx': adcm_conf['logrotate'],
            'job': adcm_conf['job_log'],
            'config': adcm_conf['config_rotation'],
        }
        self.__log(f'Got rotation config: {logrotate_config}')
        return logrotate_config

    def __run_nginx_log_rotation(self):
        if self.config['nginx']['nginx_server']:
            self.__log('Nginx log rotation started', 'info')
            # TODO: нужно ли плеваться в логи этим всем? (-v)
            cmd = ['logrotate', '-f', '-v', self.__nginx_logrotate_conf]
            proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
            output, error = proc.communicate()
            self.__log(
                f"RUN: logrotate -f {self.__nginx_logrotate_conf}, "
                f"output: {output.decode(errors='ignore')}, "
                f"error: {error.decode(errors='ignore')}",
                'info',
            )

    def __run_configlog_rotation(self):
        try:
            configlog_days_delta = self.config['config']['config_rotation_in_db']
            if configlog_days_delta <= 0:
                return

            threshold_date = timezone.now() - timedelta(days=configlog_days_delta)
            self.__log(f'ConfigLog rotation started. Threshold date: {threshold_date}', 'info')

            exclude_pks = set()
            target_configlogs = ConfigLog.objects.filter(date__lte=threshold_date)
            for cl in target_configlogs:
                for cl_pk in (cl.obj_ref.current, cl.obj_ref.previous):
                    exclude_pks.add(cl_pk)
            target_configlogs = target_configlogs.exclude(pk__in=exclude_pks)
            count = target_configlogs.count()

            with transaction.atomic():
                DummyData.objects.filter(id=1).update(date=timezone.now())
                for cl in target_configlogs:
                    if cl.obj_ref and not self.__has_related_records(cl.obj_ref):
                        cl.obj_ref.delete()
                    with suppress(
                        Exception
                    ):  # may be already deleted because of `obj_conf.delete() CASCADE`
                        cl.delete()

            self.__log(f'Deleted {count} ConfigLogs', 'info')

        except Exception as e:  # pylint: disable=broad-except
            self.__log('Error in ConfigLog rotation', 'warning')
            self.__log(e, 'exception')

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
                ]
            )
            > 0
        ):
            return True
        return False

    def __run_joblog_rotation(self):
        try:  # pylint: disable=too-many-nested-blocks
            days_delta_db = self.config['job']['log_rotation_in_db']
            days_delta_fs = self.config['job']['log_rotation_on_fs']
            if days_delta_db <= 0 and days_delta_fs <= 0:
                return

            threshold_date_db = timezone.now() - timedelta(days=days_delta_db)
            threshold_date_fs = timezone.now() - timedelta(days=days_delta_fs)
            self.__log(
                f'JobLog rotation started. Threshold dates: '
                f'db - {threshold_date_db}, fs - {threshold_date_fs}',
                'info',
            )
            if days_delta_db > 0:
                rotation_jobs_on_db = JobLog.objects.filter(finish_date__lt=threshold_date_db)
                if rotation_jobs_on_db:
                    task_ids = [job['task_id'] for job in rotation_jobs_on_db.values('task_id')]
                    with transaction.atomic():
                        rotation_jobs_on_db.delete()
                        TaskLog.objects.filter(id__in=task_ids).delete()

                self.__log('db JobLog rotated', 'info')

            if days_delta_fs > 0:  # pylint: disable=too-many-nested-blocks
                for name in os.listdir(config.RUN_DIR):
                    if not name.startswith('.'):  # a line of code is used for development
                        path = os.path.join(config.RUN_DIR, name)
                        try:
                            m_time = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
                            if timezone.now() - m_time > timedelta(days=days_delta_fs):
                                if os.path.isdir(path):
                                    shutil.rmtree(path)
                                else:
                                    os.remove(path)
                        except FileNotFoundError:
                            pass

                self.__log('fs JobLog rotated', 'info')
        except Exception as e:  # pylint: disable=broad-except
            self.__log('Error in JobLog rotation', 'warning')
            self.__log(e, 'exception')

    def __log(self, msg, method='debug'):
        if self.verbose:
            getattr(log, method)(msg)
