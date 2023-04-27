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

from cm.models import Action, Host, MaintenanceMode
from django.urls import reverse
from rbac.tests.test_policy.base import PolicyBaseTestCase
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from adcm.tests.base import APPLICATION_JSON


class PolicyWithClusterAdminRoleTestCase(PolicyBaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.create_policy(role_name="Cluster Administrator", user_pk=self.new_user.pk)

        self.another_user_log_in(username=self.new_user.username, password=self.new_user_password)

    def test_policy_with_cluster_admin_role(self):  # pylint: disable=too-many-statements
        required_perms = {perm.codename for perm in self.new_user.user_permissions.all()}
        required_perms.update({perm.permission.codename for perm in self.new_user.userobjectpermission_set.all()})

        self.assertEqual(
            required_perms,
            {
                "add_bundle",
                "add_clusterobject",
                "add_configlog",
                "add_groupconfig",
                "add_host",
                "add_prototype",
                "add_service_to_cluster",
                "change_bundle",
                "change_cluster",
                "change_config_of_cluster",
                "change_config_of_clusterobject",
                "change_config_of_host",
                "change_config_of_servicecomponent",
                "change_configlog",
                "change_groupconfig",
                "change_import_of_cluster",
                "change_import_of_clusterobject",
                "change_maintenance_mode_clusterobject",
                "change_maintenance_mode_host",
                "change_maintenance_mode_servicecomponent",
                "change_objectconfig",
                "delete_bundle",
                "delete_clusterobject",
                "delete_groupconfig",
                "delete_host",
                "do_upgrade_of_cluster",
                "edit_host_components_of_cluster",
                "map_host_to_cluster",
                "remove_host",
                "run_action_0673a0096dff0ec7006ee273e441fff030b0d9f895b8ee57c9a1d02bdc338f67",
                "run_action_633e1c7d3008add9f296b760ef59217bdf23ecda0d58cad0108aff4d59f3dec1",
                "run_action_bd938c688f49b77c7fc537c6b9222e2c97ebddd63076b87f2feaec66fb9c05d0",
                "run_action_d96211279e42aa024d783a3c107df602883f0d569bf4d30f376a19d46a7106c3",
                "run_action_e4c717c28210c2a5937ca61c3da64cb4207842ef849eb4c0722ac9de41929348",
                "run_action_eed3575d5dd631c3528cb110d024d73a00f628b124dbcb7d78c82ee33a358410",
                "unmap_host_from_cluster",
                "view_action",
                "view_cluster",
                "view_clusterobject",
                "view_configlog",
                "view_host",
                "view_host_components_of_cluster",
                "view_import_of_cluster",
                "view_import_of_clusterobject",
                "view_objectconfig",
                "view_servicecomponent",
                "view_upgrade_of_cluster",
            },
        )

        response: Response = self.client.get(
            path=reverse(viewname="cluster-details", kwargs={"cluster_id": self.cluster.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.patch(
            path=reverse(viewname="cluster-details", kwargs={"cluster_id": self.cluster.pk}),
            data={"name": "Test Cluster"},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.get(
            path=reverse(viewname="service-details", kwargs={"service_id": self.last_service_pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.get(
            path=reverse(viewname="component-details", kwargs={"component_id": self.last_component_pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.get(
            path=reverse(viewname="host-details", kwargs={"host_id": self.last_host_pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.get(
            path=reverse(viewname="host", kwargs={"cluster_id": self.cluster.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.get(
            path=reverse(
                viewname="config-current",
                kwargs={"cluster_id": self.cluster.pk, "object_type": "cluster", "version": "current"},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.get(
            path=reverse(
                viewname="config-current",
                kwargs={
                    "cluster_id": self.cluster.pk,
                    "service_id": self.last_service_pk,
                    "object_type": "service",
                    "version": "current",
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.get(
            path=reverse(
                viewname="config-current",
                kwargs={"component_id": self.last_component_pk, "object_type": "component", "version": "current"},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.get(
            path=reverse(
                viewname="config-current",
                kwargs={"host_id": self.last_host_pk, "object_type": "host", "version": "current"},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.get(
            path=reverse(viewname="object-action", kwargs={"cluster_id": self.cluster.pk, "object_type": "cluster"}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

        response: Response = self.client.get(
            path=reverse(
                viewname="object-action", kwargs={"service_id": self.last_service_pk, "object_type": "service"}
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

        response: Response = self.client.get(
            path=reverse(
                viewname="object-action", kwargs={"component_id": self.last_component_pk, "object_type": "component"}
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

        response: Response = self.client.post(
            path=reverse(viewname="host-component", kwargs={"cluster_id": self.cluster.pk}),
            data={
                "cluster_id": self.cluster.pk,
                "hc": [
                    {
                        "component_id": self.last_component_pk,
                        "host_id": self.last_host_pk,
                        "service_id": self.last_service_pk,
                    }
                ],
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse(viewname="config-history", kwargs={"cluster_id": self.cluster.pk, "object_type": "cluster"}),
            data={"config": {"float": 3.3}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse(
                viewname="config-history",
                kwargs={"cluster_id": self.cluster.pk, "service_id": self.last_service_pk, "object_type": "service"},
            ),
            data={"config": {"float": 3.3}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse(
                viewname="config-history",
                kwargs={"component_id": self.last_component_pk, "object_type": "component"},
            ),
            data={"config": {"float": 3.3}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse(
                viewname="config-history",
                kwargs={"host_id": self.last_host_pk, "object_type": "host"},
            ),
            data={"config": {"string": "new_string"}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse(
                viewname="config-history",
                kwargs={"cluster_id": self.cluster.pk, "host_id": self.last_host_pk, "object_type": "host"},
            ),
            data={"config": {"string": "new_string"}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = self.client.post(
            path=reverse(viewname="service", kwargs={"cluster_id": self.cluster.pk}),
            data={
                "prototype_id": self.service_6_proto.pk,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = self.client.delete(
            path=reverse(
                viewname="service-details",
                kwargs={"cluster_id": self.cluster.pk, "service_id": response.json()["id"]},
            ),
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        response = self.client.post(
            path=reverse(viewname="service-maintenance-mode", kwargs={"service_id": self.last_service_pk}),
            data={
                "maintenance_mode": MaintenanceMode.ON,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response = self.client.post(
            path=reverse(viewname="component-maintenance-mode", kwargs={"component_id": self.last_component_pk}),
            data={
                "maintenance_mode": MaintenanceMode.ON,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response = self.client.post(
            path=reverse(viewname="host-maintenance-mode", kwargs={"host_id": self.last_host_pk}),
            data={
                "maintenance_mode": MaintenanceMode.ON,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response = self.client.post(
            path=reverse(viewname="host-maintenance-mode", kwargs={"host_id": self.last_host_pk}),
            data={
                "maintenance_mode": MaintenanceMode.OFF,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.get(
            path=reverse(viewname="object-action", kwargs={"host_id": self.last_host_pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            response: Response = self.client.post(
                path=reverse(
                    viewname="run-task",
                    kwargs={"host_id": self.last_host_pk, "action_id": response.json()[0]["id"]},
                ),
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.delete(
            path=reverse(
                viewname="host-details",
                kwargs={"host_id": self.first_host_pk, "cluster_id": self.cluster.pk},
            ),
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        response: Response = self.client.get(
            path=reverse(
                viewname="config-current",
                kwargs={"host_id": self.first_host_pk, "object_type": "host", "version": "current"},
            ),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        response: Response = self.client.post(
            path=reverse(
                viewname="config-history",
                kwargs={"cluster_id": self.cluster.pk, "host_id": self.first_host_pk, "object_type": "host"},
            ),
            data={"config": {"string": "new_string"}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        response: Response = self.client.get(
            path=reverse(viewname="object-action", kwargs={"host_id": self.first_host_pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertFalse(response.json())

        first_host = Host.objects.get(id=self.first_host_pk)
        first_host_action = Action.objects.filter(prototype=first_host.prototype).first()

        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            response: Response = self.client.post(
                path=reverse(
                    viewname="run-task",
                    kwargs={"host_id": self.first_host_pk, "action_id": first_host_action.pk},
                ),
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
