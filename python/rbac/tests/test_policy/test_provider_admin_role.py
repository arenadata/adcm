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

from adcm.tests.base import APPLICATION_JSON
from cm.models import ConfigLog, Host
from django.db.models import ObjectDoesNotExist
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from rbac.tests.test_policy.base import PolicyBaseTestCase


class PolicyWithProviderAdminRole(PolicyBaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.create_policy(role_name="Provider Administrator", obj=self.provider, group_pk=self.new_user_group.pk)

    def test_policy_with_provider_admin_role(self):
        required_perms = {perm.codename for perm in self.new_user_group.permissions.all()}
        required_perms.update(
            {perm.permission.codename for perm in self.new_user_group.groupobjectpermission_set.all()}
        )

        self.assertEqual(
            required_perms,
            {
                "add_configlog",
                "do_upgrade_of_provider",
                "change_config_of_provider",
                "change_bundle",
                "add_bundle",
                "delete_confighostgroup",
                "change_config_of_host",
                "add_prototype",
                "change_objectconfig",
                "view_provider",
                "add_host",
                "delete_bundle",
                "view_host",
                "change_configlog",
                "add_host_to_provider",
                "delete_host",
                "run_action_bd938c688f49b77c7fc537c6b9222e2c97ebddd63076b87f2feaec66fb9c05d0",
                "remove_host",
                "view_action",
                "add_confighostgroup",
                "change_confighostgroup",
                "view_upgrade_of_provider",
                "view_configlog",
                "view_objectconfig",
                "view_logstorage",
                "view_joblog",
                "view_tasklog",
            },
        )

        response: Response = self.client.get(
            path=reverse(viewname="v1:provider-details", kwargs={"provider_id": self.provider.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["name"], self.provider.name)

        response: Response = self.client.get(
            path=reverse(viewname="v1:object-config", kwargs={"provider_id": self.provider.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        new_string = "new_string"

        response: Response = self.client.post(
            path=reverse(viewname="v1:config-history", kwargs={"provider_id": self.provider.pk}),
            data={"config": {"string": new_string}},
            content_type=APPLICATION_JSON,
        )

        self.provider.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.provider.config.current)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(config_log.config["string"], new_string)

        response: Response = self.client.get(
            path=reverse(viewname="v1:object-action", kwargs={"provider_id": self.provider.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v1:run-task",
                    kwargs={"provider_id": self.provider.pk, "action_id": response.json()[0]["id"]},
                ),
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse(viewname="v1:host", kwargs={"provider_id": self.provider.pk}),
            data={"fqdn": "test-host"},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_pk = response.json()["id"]

        response: Response = self.client.get(path=reverse(viewname="v1:host-details", kwargs={"host_id": host_pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["id"], host_pk)

        response: Response = self.client.get(
            path=reverse(viewname="v1:object-config", kwargs={"host_id": host_pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        new_string = "new_string"

        response: Response = self.client.post(
            path=reverse(viewname="v1:config-history", kwargs={"host_id": host_pk}),
            data={"config": {"string": new_string}},
            content_type=APPLICATION_JSON,
        )

        host = Host.objects.get(pk=host_pk)
        config_log = ConfigLog.objects.get(pk=host.config.current)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(config_log.config["string"], new_string)

        response: Response = self.client.get(
            path=reverse(viewname="v1:object-action", kwargs={"host_id": host_pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v1:run-task",
                    kwargs={"host_id": host.pk, "action_id": response.json()[0]["id"]},
                ),
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.delete(path=reverse(viewname="v1:host-details", kwargs={"host_id": host.pk}))

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        with self.assertRaises(ObjectDoesNotExist):
            host.refresh_from_db()
