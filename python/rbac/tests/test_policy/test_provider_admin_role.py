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

from cm.models import ConfigLog, Host
from django.db.models import ObjectDoesNotExist
from django.urls import reverse
from rbac.tests.test_policy.base import PolicyBaseTestCase
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from adcm.tests.base import APPLICATION_JSON


class PolicyWithProviderAdminRole(PolicyBaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.create_policy(role_name="Provider Administrator", obj=self.provider, user_pk=self.new_user.pk)

    def test_policy_with_provider_admin_role(self):
        required_perms = {perm.codename for perm in self.new_user.user_permissions.all()}
        required_perms.update({perm.permission.codename for perm in self.new_user.userobjectpermission_set.all()})

        self.assertEqual(
            required_perms,
            {
                "add_configlog",
                "do_upgrade_of_hostprovider",
                "change_config_of_hostprovider",
                "change_bundle",
                "add_bundle",
                "delete_groupconfig",
                "change_config_of_host",
                "add_prototype",
                "change_objectconfig",
                "view_hostprovider",
                "add_host",
                "delete_bundle",
                "view_host",
                "change_configlog",
                "add_host_to_hostprovider",
                "delete_host",
                "run_action_bd938c688f49b77c7fc537c6b9222e2c97ebddd63076b87f2feaec66fb9c05d0",
                "remove_host",
                "view_action",
                "add_groupconfig",
                "change_groupconfig",
                "view_upgrade_of_hostprovider",
                "view_configlog",
                "view_objectconfig",
            },
        )

        response: Response = self.client.get(
            path=reverse(viewname="provider-details", kwargs={"provider_id": self.provider.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["name"], self.provider.name)

        response: Response = self.client.get(
            path=reverse(viewname="object-config", kwargs={"provider_id": self.provider.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        new_string = "new_string"

        response: Response = self.client.post(
            path=reverse(viewname="config-history", kwargs={"provider_id": self.provider.pk}),
            data={"config": {"string": new_string}},
            content_type=APPLICATION_JSON,
        )

        self.provider.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.provider.config.current)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(config_log.config["string"], new_string)

        response: Response = self.client.get(
            path=reverse(viewname="object-action", kwargs={"provider_id": self.provider.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            response: Response = self.client.post(
                path=reverse(
                    viewname="run-task",
                    kwargs={"provider_id": self.provider.pk, "action_id": response.json()[0]["id"]},
                ),
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse("host", kwargs={"provider_id": self.provider.pk}),
            data={"fqdn": "test-host"},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_pk = response.json()["id"]

        response: Response = self.client.get(path=reverse("host-details", kwargs={"host_id": host_pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["id"], host_pk)

        response: Response = self.client.get(
            path=reverse(viewname="object-config", kwargs={"host_id": host_pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        new_string = "new_string"

        response: Response = self.client.post(
            path=reverse(viewname="config-history", kwargs={"host_id": host_pk}),
            data={"config": {"string": new_string}},
            content_type=APPLICATION_JSON,
        )

        host = Host.objects.get(pk=host_pk)
        config_log = ConfigLog.objects.get(pk=host.config.current)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(config_log.config["string"], new_string)

        response: Response = self.client.get(
            path=reverse(viewname="object-action", kwargs={"host_id": host_pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            response: Response = self.client.post(
                path=reverse(
                    viewname="run-task",
                    kwargs={"host_id": host.pk, "action_id": response.json()[0]["id"]},
                ),
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.delete(path=reverse("host-details", kwargs={"host_id": host.pk}))

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        with self.assertRaises(ObjectDoesNotExist):
            host.refresh_from_db()
