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
        super().setUp()

        adcm = ADCM.objects.first()
        current_config_log = ConfigLog.objects.get(id=adcm.config.current)
        config = current_config_log.config
        attr = current_config_log.attr
        config.update(
            {
                "audit_data_retention": {"log_rotation_on_fs": 1, "log_rotation_in_db": 1, "config_rotation_in_db": 1},
                "logrotate": {"size": "10M", "max_history": 10, "compress": False},
            }
        )
        attr.update({"logrotate": {"active": False}})
        new_config_log = ConfigLog.objects.create(config=config, attr=attr, obj_ref=adcm.config)
        adcm.config.previous = current_config_log.pk
        adcm.config.current = new_config_log.pk
        adcm.config.save()

        self.user = User.objects.get(username="system")
        bundle = Bundle.objects.create()
        cluster_prototype = Prototype.objects.create(bundle=bundle, type="cluster")
        cluster_config = ObjectConfig.objects.create(current=0, previous=0)
        date = timezone.now() - timedelta(days=3)
        cluster = Cluster.objects.create(name="test_cluster", prototype=cluster_prototype, config=cluster_config)

        ConfigLog.objects.create(obj_ref=cluster_config)
        current_cluster_config_log = ConfigLog.objects.create(obj_ref=cluster_config)
        previous_cluster_config_log = ConfigLog.objects.create(obj_ref=cluster_config)
        cluster_config.current = current_cluster_config_log.pk
        cluster_config.previous = previous_cluster_config_log.pk
        cluster_config.save(update_fields=["current", "previous"])
        ConfigLog.objects.filter().update(date=date)

        TaskLog.objects.create(object_id=cluster.id, start_date=date, finish_date=date, status="success")
        JobLog.objects.create(start_date=date, finish_date=date)

    def check_auditlog(self, log: AuditLog, name):
        self.assertIsNone(log.audit_object)
        self.assertEqual(log.operation_name, name)
        self.assertEqual(log.operation_type, AuditLogOperationType.DELETE)
        self.assertEqual(log.operation_result, AuditLogOperationResult.SUCCESS)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, self.user.username)

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
