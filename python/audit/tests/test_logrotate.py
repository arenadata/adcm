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

from audit.models import AuditLog, AuditLogOperationResult, AuditLogOperationType
from cm.models import (
    ADCM,
    Bundle,
    Cluster,
    ConfigLog,
    JobLog,
    ObjectConfig,
    Prototype,
    TaskLog,
)
from django.core.management import call_command
from django.utils import timezone
from rbac.models import User

from adcm.tests.base import BaseTestCase


class TestLogrotate(BaseTestCase):
    def setUp(self) -> None:
        bundle = Bundle.objects.create()
        date = timezone.now() - timedelta(days=3)
        prototype = Prototype.objects.create(bundle=bundle, type="adcm")
        config = ObjectConfig.objects.create(current=0, previous=0)
        config_log = ConfigLog.objects.create(
            obj_ref=config,
            config={
                "job_log": {"log_rotation_on_fs": 1, "log_rotation_in_db": 1},
                "config_rotation": {"config_rotation_in_db": 1},
                "logrotate": {"size": "10M", "max_history": 10, "compress": False},
            },
            attr={"logrotate": {"active": False}},
        )
        config.current = config_log.pk
        config.save(update_fields=["current"])

        ADCM.objects.create(prototype=prototype, name="ADCM_2", config=config)
        self.user = User.objects.create_superuser("system", "", None, built_in=True)
        prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        config_2 = ObjectConfig.objects.create(current=4, previous=3)
        cluster = Cluster.objects.create(name="test_cluster", prototype=prototype, config=config_2)
        TaskLog.objects.create(object_id=cluster.id, start_date=date, finish_date=date, status="success")
        JobLog.objects.create(start_date=date, finish_date=date)
        ConfigLog.objects.create(obj_ref=config_2)
        ConfigLog.objects.all().update(date=date)

    def check_auditlog(self, log: AuditLog, name):
        self.assertIsNone(log.audit_object)
        self.assertEqual(log.operation_name, name)
        self.assertEqual(log.operation_type, AuditLogOperationType.DELETE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.SUCCESS)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, self.user.pk)

    def test_logrotate(
        self,
    ):
        call_command("logrotate", "--target=all")
        logs = AuditLog.objects.order_by("operation_time")

        self.assertEqual(logs.count(), 4)
        self.check_auditlog(logs[0], '"Task log cleanup on schedule" job launched')
        self.check_auditlog(logs[1], '"Task log cleanup on schedule" job completed')
        self.check_auditlog(logs[2], '"Objects configurations cleanup on schedule" job launched')
        self.check_auditlog(logs[3], '"Objects configurations cleanup on schedule" job completed')

        call_command("logrotate", "--target=all")
        new_logs = AuditLog.objects.order_by("operation_time")
        self.assertEqual(new_logs.count(), 4)
