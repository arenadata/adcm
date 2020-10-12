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

from datetime import timedelta
from subprocess import Popen, PIPE

from background_task import background
from background_task.tasks import Task
from django.utils import timezone

from cm.logger import log
from cm.models import ADCM, ConfigLog

PERIODS = {
    'HOURLY': Task.HOURLY,
    'DAILY': Task.DAILY,
    'WEEKLY': Task.WEEKLY
}


@background(schedule=60)
def run_logrotate(path):
    cmd = ['logrotate', '-f', path]
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
    output, error = proc.communicate()
    log.info('RUN: logrotate -f %s, output: %s, error: %s', path,
             output.decode(errors='ignore'), error.decode(errors='ignore'))


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
