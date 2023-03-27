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

from audit.models import AuditLog, AuditSession
from cm.models import ADCM, Bundle, Prototype
from django.urls import reverse
from rest_framework.response import Response

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestAuditAPI(BaseTestCase):
    def test_filter_session_login_time(self):
        login_time = AuditSession.objects.first().login_time
        login_time_before = login_time - timedelta(minutes=1)
        response: Response = self.client.get(
            reverse("audit:auditsession-list"),
            {"login_time_before": login_time_before.isoformat()},
        )

        self.assertEqual(response.data["count"], 0)

        login_time_after = login_time + timedelta(minutes=1)
        response: Response = self.client.get(
            reverse("audit:auditsession-list"),
            {"login_time_after": login_time_after.isoformat()},
        )

        self.assertEqual(response.data["count"], 0)

        response: Response = self.client.get(
            reverse("audit:auditsession-list"),
            {"login_time_after": login_time_before.isoformat(), "login_time_before": login_time_after.isoformat()},
        )

        self.assertEqual(response.data["count"], 1)

    def test_filter_operations_operation_time(self):
        adcm = ADCM.objects.create(
            prototype=Prototype.objects.create(bundle=Bundle.objects.create(), type="adcm"),
            name="ADCM",
        )
        self.client.post(
            path=reverse("config-history", kwargs={"adcm_pk": adcm.pk}),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )
        operation_time = AuditLog.objects.first().operation_time
        operation_time_before = operation_time - timedelta(minutes=1)

        response: Response = self.client.get(
            reverse("audit:auditlog-list"),
            {"operation_time_before": operation_time_before.isoformat()},
        )

        self.assertEqual(response.data["count"], 0)

        operation_time_after = operation_time + timedelta(minutes=1)

        response: Response = self.client.get(
            reverse("audit:auditlog-list"),
            {"operation_time_after": operation_time_after.isoformat()},
        )

        self.assertEqual(response.data["count"], 0)

        response: Response = self.client.get(
            reverse("audit:auditlog-list"),
            {
                "operation_time_after": operation_time_before.isoformat(),
                "operation_time_before": operation_time_after.isoformat(),
            },
        )

        self.assertEqual(response.data["count"], 1)
