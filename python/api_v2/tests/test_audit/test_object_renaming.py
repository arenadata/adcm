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

from rbac.models import Role
from rbac.services.group import create as create_group
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from api_v2.tests.base import BaseAPITestCase


class TestAuditObjectNameChanged(BaseAPITestCase):
    def test_cluster_rename(self) -> None:
        first_new_name = "Best Cluster Name EVER"
        second_new_name = "Another Name"

        response = self.client.v2[self.cluster_1].patch(data={"name": first_new_name})
        self.assertEqual(response.status_code, HTTP_200_OK)

        log = self.get_most_recent_audit_log()

        self.assertEqual(log.audit_object.object_name, first_new_name)

        response = self.client.v2[self.cluster_1].patch(data={"name": second_new_name})
        self.assertEqual(response.status_code, HTTP_200_OK)

        log.refresh_from_db()

        self.assertEqual(log.audit_object.object_name, second_new_name)

    def test_host_rename(self) -> None:
        first_name = "best-cluster-fqdn-ever"
        second_name = "another-name"

        response = (self.client.v2 / "hosts").post(
            data={"name": first_name, "hostproviderId": self.provider.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        log = self.get_most_recent_audit_log()

        self.assertEqual(log.audit_object.object_name, first_name)

        response = (self.client.v2 / "hosts" / response.json()["id"]).patch(data={"name": second_name})
        self.assertEqual(response.status_code, HTTP_200_OK)

        log.refresh_from_db()

        self.assertEqual(log.audit_object.object_name, second_name)

    def test_policy_rename(self) -> None:
        first_name = "besT policy"
        second_name = "another Name"

        role = role_create(
            display_name="Custom role name",
            child=[Role.objects.get(name="View cluster configurations")],
        )

        policy = policy_create(
            name=first_name,
            role=role,
            group=[create_group(name_to_display="Other group")],
            object=[self.cluster_1],
        )

        response = self.client.v2[policy].patch(
            data={"displayName": "changed display name"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        log = self.get_most_recent_audit_log()

        self.assertEqual(log.audit_object.object_name, first_name)

        response = self.client.v2[policy].patch(data={"name": second_name})
        self.assertEqual(response.status_code, HTTP_200_OK)

        log.refresh_from_db()

        self.assertEqual(log.audit_object.object_name, second_name)
