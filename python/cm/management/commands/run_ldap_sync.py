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
from datetime import timedelta

from audit.models import AuditLogOperationResult
from audit.utils import make_audit_log
from cm.job import ActionRunPayload, run_action
from cm.models import ADCM, Action, ConfigLog, JobStatus, TaskLog
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger("background_tasks")


def get_settings(adcm_object):
    current_configlog = ConfigLog.objects.get(obj_ref=adcm_object.config, id=adcm_object.config.current)
    if current_configlog.attr["ldap_integration"]["active"]:
        ldap_config = current_configlog.config["ldap_integration"]
        return ldap_config["sync_interval"]
    return 0


class Command(BaseCommand):
    help = "Run synchronization with ldap if sync_interval is specified in ADCM settings"

    def handle(self, *args, **options):
        adcm_object = ADCM.objects.first()
        action = Action.objects.get(name="run_ldap_sync", prototype=adcm_object.prototype)
        period = get_settings(adcm_object)
        if period <= 0:
            return
        if TaskLog.objects.filter(action__name="run_ldap_sync", status=JobStatus.RUNNING).exists():
            logger.debug("Sync has already launched, we need to wait for the task end")
            return
        last_sync = TaskLog.objects.filter(
            action__name="run_ldap_sync",
            status__in=[JobStatus.SUCCESS, JobStatus.FAILED],
        ).last()
        if last_sync is None:
            logger.debug("First ldap sync launched in %s", timezone.now())
            make_audit_log("sync", AuditLogOperationResult.SUCCESS, "launched")
            task = run_action(action=action, obj=adcm_object, payload=ActionRunPayload(), hosts=[])
            if task:
                make_audit_log("sync", AuditLogOperationResult.SUCCESS, "completed")
            else:
                make_audit_log("sync", AuditLogOperationResult.FAIL, "completed")
            return
        new_rotate_time = last_sync.finish_date + timedelta(minutes=period - 1)
        if new_rotate_time <= timezone.now():
            logger.debug("Ldap sync launched in %s", timezone.now())
            make_audit_log("sync", AuditLogOperationResult.SUCCESS, "launched")
            task = run_action(action=action, obj=adcm_object, payload=ActionRunPayload(), hosts=[])
            if task:
                make_audit_log("sync", AuditLogOperationResult.SUCCESS, "completed")
            else:
                make_audit_log("sync", AuditLogOperationResult.FAIL, "completed")
