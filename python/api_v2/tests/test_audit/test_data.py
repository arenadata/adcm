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

from audit.models import AuditLog, AuditSession
from cm.models import ObjectType, Prototype
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from api_v2.tests.base import BaseAPITestCase


class TestAgentFieldAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client.logout()

        self.admin_creds = {"username": "admin", "password": "admin"}
        self.user_agent = "Test-User-Agent"
        self.long_user_agent = self.user_agent * 256

    def test_session_agent(self):
        response = (self.client.v2 / "login").post(data=self.admin_creds, headers={"HTTP_USER_AGENT": self.user_agent})
        session = AuditSession.objects.order_by("pk").last()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIsNotNone(session)
        self.assertEqual(session.agent, self.user_agent)

        self.client.logout()

        response = (self.client.v2 / "login").post(data=self.admin_creds)
        session = AuditSession.objects.order_by("pk").last()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIsNotNone(session)
        self.assertEqual(session.agent, "")

    def test_log_agent(self):
        self.client.login(**self.admin_creds)

        response = (self.client.v2 / "clusters" / str(self.cluster_1.pk) / "services").post(
            data=[
                {
                    "prototypeId": Prototype.objects.get(
                        type=ObjectType.SERVICE, name="service_3_manual_add", bundle_id=self.cluster_1.bundle_id
                    ).pk
                }
            ],
        )
        log = AuditLog.objects.order_by("pk").last()

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertIsNotNone(log)
        self.assertEqual(log.agent, "")

        response = (self.client.v2 / "clusters" / str(self.cluster_1.pk) / "services").post(
            data=[
                {
                    "prototypeId": Prototype.objects.get(
                        type=ObjectType.SERVICE, name="service_1", bundle_id=self.cluster_1.bundle_id
                    ).pk
                }
            ],
            headers={"HTTP_USER_AGENT": self.long_user_agent},
        )
        log = AuditLog.objects.order_by("pk").last()

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertIsNotNone(log)
        self.assertEqual(log.agent, self.long_user_agent[:255])
