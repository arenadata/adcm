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

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from audit.models import AuditLogOperationResult
from audit.utils import make_audit_log
from cm.config import Job
from cm.job import start_task
from cm.logger import log_cron_task as log
from cm.models import ADCM, Action, ConfigLog, TaskLog


def get_settings(adcm_object):
    current_configlog = ConfigLog.objects.get(
        obj_ref=adcm_object.config, id=adcm_object.config.current
    )
    if current_configlog.attr["ldap_integration"]["active"]:
        ldap_config = current_configlog.config["ldap_integration"]
        return ldap_config["sync_interval"]
    return 0


class Command(BaseCommand):
    help = "Run synchronization with ldap if sync_interval is specified in ADCM settings"

    def handle(self, *args, **options):
        adcm_object = ADCM.objects.get(id=1)
        action = Action.objects.get(name="run_ldap_sync", prototype=adcm_object.prototype)
        period = get_settings(adcm_object)
        if period <= 0:
            return
        if TaskLog.objects.filter(action__name="run_ldap_sync", status=Job.RUNNING).exists():
            log.debug("Sync has already launched, we need to wait for the task end")
            return
        last_sync = TaskLog.objects.filter(
            action__name="run_ldap_sync", status__in=[Job.SUCCESS, Job.FAILED]
        ).last()
        if last_sync is None:
            log.debug("First ldap sync launched in %s", timezone.now())
            make_audit_log("sync", AuditLogOperationResult.Success, "launched")
            task = start_task(action, adcm_object, {}, {}, [], [], False)
            if task:
                make_audit_log("sync", AuditLogOperationResult.Success, "completed")
            else:
                make_audit_log("sync", AuditLogOperationResult.Fail, "completed")
            return
        new_rotate_time = last_sync.finish_date + timedelta(minutes=period - 1)
        if new_rotate_time <= timezone.now():
            log.debug("Ldap sync launched in %s", timezone.now())
            make_audit_log("sync", AuditLogOperationResult.Success, "launched")
            task = start_task(action, adcm_object, {}, {}, [], [], False)
            if task:
                make_audit_log("sync", AuditLogOperationResult.Success, "completed")
            else:
                make_audit_log("sync", AuditLogOperationResult.Fail, "completed")
