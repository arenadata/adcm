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
import logging

from audit.alt.background import audit_background_operation
from audit.models import AuditLogOperationType
from django.core.management.base import BaseCommand
from django.utils import timezone

from cm.models import ADCM, Action, ConfigLog, JobStatus, TaskLog
from cm.services.job.action import ActionRunPayload, run_action

logger = logging.getLogger("background_tasks")


def get_settings(adcm_object):
    current_configlog = ConfigLog.objects.get(obj_ref=adcm_object.config, id=adcm_object.config.current)
    if current_configlog.attr["ldap_integration"]["active"]:
        ldap_config = current_configlog.config["ldap_integration"]
        return ldap_config["sync_interval"]
    return 0


class Command(BaseCommand):
    help = "Run synchronization with ldap if sync_interval is specified in ADCM settings"

    def handle(self, *args, **options):  # noqa: ARG002
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

        if not last_sync:
            logger.debug("First ldap sync launched in %s", timezone.now())
        else:
            next_rotation_time = last_sync.finish_date + timedelta(minutes=period - 1)
            if next_rotation_time > timezone.now():
                return

            logger.debug("Ldap sync launched in %s", timezone.now())

        with audit_background_operation(name='"User sync on schedule" job', type_=AuditLogOperationType.UPDATE):
            run_action(action=action, obj=adcm_object, payload=ActionRunPayload())
