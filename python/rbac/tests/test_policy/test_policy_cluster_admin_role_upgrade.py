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

from unittest.mock import patch

from cm.models import ServiceComponent, Upgrade
from django.conf import settings
from django.urls import reverse
from rbac.tests.test_policy.base import PolicyBaseTestCase
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from adcm.tests.base import APPLICATION_JSON


class PolicyWithClusterAdminRoleUpgradeTestCase(PolicyBaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.create_policy(role_name="Cluster Administrator", obj=self.cluster, user_pk=self.new_user.pk)
        self.another_user_log_in(username=self.new_user.username, password=self.new_user_password)
        self.upgrade_cluster()
        self.component_upgrade = ServiceComponent.objects.get(prototype__name="component_upgrade")

    def upgrade_cluster(self):
        self.upload_and_load_bundle(
            path=(
                settings.BASE_DIR
                / "python"
                / "rbac"
                / "tests"
                / "files"
                / "test_cluster_for_cluster_admin_role_upgrade.tar"
            )
        )
        response: Response = self.client.post(
            path=reverse(
                "do-cluster-upgrade",
                kwargs={"cluster_id": self.cluster.pk, "upgrade_id": Upgrade.objects.first().pk},
            ),
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_policy_with_cluster_admin_role_upgrade(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="object-action",
                kwargs={"service_id": self.last_service_pk, "object_type": "service"},
            ),
        )
        response_json = response.json()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response_json), 3)

        action_upgrade_pk = next(action["id"] for action in response_json if action["name"] == "action_upgrade")
        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            response: Response = self.client.post(
                path=reverse(
                    viewname="run-task",
                    kwargs={"service_id": self.last_service_pk, "action_id": action_upgrade_pk},
                ),
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.get(
            path=reverse(viewname="component-details", kwargs={"component_id": self.component_upgrade.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.get(
            path=reverse(
                viewname="config-current",
                kwargs={"component_id": self.component_upgrade.pk, "object_type": "component", "version": "current"},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.post(
            path=reverse(
                viewname="config-history",
                kwargs={"component_id": self.component_upgrade.pk, "object_type": "component"},
            ),
            data={"config": {"float": 3.3}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.get(
            path=reverse(
                viewname="object-action",
                kwargs={"component_id": self.component_upgrade.pk, "object_type": "component"},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            response: Response = self.client.post(
                path=reverse(
                    viewname="run-task",
                    kwargs={"component_id": self.component_upgrade.pk, "action_id": response.json()[0]["id"]},
                ),
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
