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
# pylint: disable = unexpected-keyword-arg

from contextlib import suppress
from datetime import timedelta
from subprocess import Popen, PIPE

from background_task import background
from background_task.tasks import Task
from django.utils import timezone

from cm.logger import log
from cm.models import (
    ADCM,
    Cluster,
    ClusterObject,
    ConfigLog,
    Host,
    HostProvider,
    ObjectConfig,
    ServiceComponent,
)

BACKGROUND_TASKS_DEFAULT_DELAY = 60  # seconds
PERIODS = {'HOURLY': Task.HOURLY, 'DAILY': Task.DAILY, 'WEEKLY': Task.WEEKLY}
CONFIGLOG_ROTATION = {'repeat': PERIODS['DAILY'], 'verbose_name': 'configlog_db_rotation'}


@background(schedule=BACKGROUND_TASKS_DEFAULT_DELAY)
def run_logrotate(path):
    cmd = ['logrotate', '-f', path]
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
    output, error = proc.communicate()
    log.info(
        'RUN: logrotate -f %s, output: %s, error: %s',
        path,
        output.decode(errors='ignore'),
        error.decode(errors='ignore'),
    )


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


@background(schedule=BACKGROUND_TASKS_DEFAULT_DELAY)
def run_configlog_rotation(configlog_days_delta: int) -> None:
    try:
        threshold_date = timezone.now() - timedelta(days=configlog_days_delta)
        log.debug('ConfigLog rotation started. Threshold date: %s', threshold_date)

        exclude_pks = set()
        target_configlogs = ConfigLog.objects.filter(date__lte=threshold_date)
        for cl in target_configlogs:
            for cl_pk in (cl.obj_ref.current, cl.obj_ref.previous):
                exclude_pks.add(cl_pk)
        target_configlogs = target_configlogs.exclude(pk__in=exclude_pks)
        count = target_configlogs.count()

        for cl in target_configlogs:
            if cl.obj_ref and not __has_related_records(cl.obj_ref):
                cl.obj_ref.delete()
            with suppress(
                Exception
            ):  # may be already deleted because of `obj_conf.delete() CASCADE`
                cl.delete()

        log.debug('Deleted %s ConfigLogs', count)

    except Exception as e:  # pylint: disable=broad-except
        log.warning('Error in ConfigLog rotation')
        log.exception(e)


def create_task(path, name, period, turn):
    try:
        task = Task.objects.get(verbose_name=name)
        if not turn:
            task.delete()
            return
        if not period == task.repeat:
            task.repeat = period
            task.run_at = timezone.now() + timedelta(seconds=60)
            task.save()
    except Task.DoesNotExist:
        if turn:
            run_logrotate(path, verbose_name=name, repeat=period)


def run():
    adcm_object = ADCM.objects.get(id=1)
    cl = ConfigLog.objects.get(obj_ref=adcm_object.config, id=adcm_object.config.current)
    adcm_conf = cl.config
    period = PERIODS[adcm_conf['logrotate']['rotation_period']]

    use_rotation_nginx_server = adcm_conf['logrotate']['nginx_server']
    create_task('/etc/logrotate.d/nginx', 'nginx', period, use_rotation_nginx_server)

    configlog_days_delta = adcm_conf['config_rotation']['config_rotation_in_db']
    if configlog_days_delta > 0:
        Task.objects.filter(verbose_name=CONFIGLOG_ROTATION['verbose_name']).delete()
        run_configlog_rotation(
            configlog_days_delta,
            verbose_name=CONFIGLOG_ROTATION['verbose_name'],
            repeat=CONFIGLOG_ROTATION['repeat'],
        )
        log.debug('Rotation of ConfigLog initialized [days=%s]', configlog_days_delta)
