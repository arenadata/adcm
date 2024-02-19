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

from audit.models import AuditObject
from cm.models import (
    Action,
    Cluster,
    ClusterObject,
    Host,
    ObjectType,
    Prototype,
    ServiceComponent,
    Upgrade,
)
from rest_framework.reverse import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase


class TestClusterAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

        self.prototype = Prototype.objects.get(bundle=self.bundle_1, type=ObjectType.CLUSTER)

        self.host_1 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_1)

        self.host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host2")
        self.host_3 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host3")

        self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1)
        self.service_1 = ClusterObject.objects.get(cluster=self.cluster_1, prototype__name="service_1")
        self.component_1 = ServiceComponent.objects.get(
            cluster=self.cluster_1, prototype__bundle=self.bundle_1, prototype__name="component_1"
        )

        required_import_bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_with_required_import")
        self.import_cluster = self.add_cluster(bundle=required_import_bundle, name="required_import_cluster")

        self.cluster_1_config_post_data = {
            "config": {
                "activatable_group": {"integer": 111},
                "boolean": False,
                "group": {"float": 2.2},
                "list": ["value1", "value2", "value3", "value4"],
                "variant_not_strict": "value5",
            },
            "adcmMeta": {"/activatable_group": {"isActive": False}},
            "description": "new config",
        }

        self.service_add_prototypes = Prototype.objects.filter(
            bundle=self.cluster_1.prototype.bundle,
            type=ObjectType.SERVICE,
            name__in=["service_3_manual_add", "service_2"],
        ).order_by("pk")

        self.cluster_action = Action.objects.get(name="action", prototype=self.cluster_1.prototype)
        self.service_action = Action.objects.get(name="action", prototype=self.service_1.prototype)
        self.component_action = Action.objects.get(name="action_1_comp_1", prototype=self.component_1.prototype)
        self.host_action = Action.objects.get(name="cluster_on_host", prototype=self.cluster_1.prototype)

        self.upgrade_bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_one_upgrade")
        self.cluster_upgrade = Upgrade.objects.get(bundle=self.upgrade_bundle, name="upgrade_via_action_simple")

    def test_create_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototypeId": self.prototype.pk, "name": "audit_test_cluster"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        cluster = Cluster.objects.get(pk=response.json()["id"])

        self.check_last_audit_record(
            operation_name="Cluster created",
            operation_type="create",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=cluster),
            user__username="admin",
        )

    def test_create_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototypeId": self.prototype.pk, "name": "audit_test_cluster"},
        )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="Cluster created",
            operation_type="create",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username=self.test_user.username,
        )

    def test_create_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototypeId": self.prototype.pk, "name": self.cluster_1.name},
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        self.check_last_audit_record(
            operation_name="Cluster created",
            operation_type="create",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_edit_success(self):
        old_name = self.cluster_1.name
        response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
            data={"name": "new_cluster_name"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.cluster_1.refresh_from_db()

        self.check_last_audit_record(
            operation_name="Cluster updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            object_changes={"current": {"name": "new_cluster_name"}, "previous": {"name": old_name}},
            user__username="admin",
        )

    def test_edit_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
            data={"name": "new_cluster_name"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Cluster updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_edit_incorrect_body_fail(self):
        response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
            data={"name": "new , cluster_name"},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="Cluster updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_edit_not_found_fail(self):
        response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.get_non_existent_pk(model=Cluster)}),
            data={"name": "new_cluster_name"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Cluster updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_delete_success(self):
        # audit object should exist before successful DELETE request
        # to have `is_deleted` updated
        # for now we've agreed that's ok tradeoff
        AuditObject.objects.get_or_create(
            object_id=self.cluster_1.pk,
            object_name=self.cluster_1.name,
            object_type="cluster",
            is_deleted=False,
        )

        response = self.client.delete(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_record(
            operation_name="Cluster deleted",
            operation_type="delete",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1, is_deleted=True),
            user__username="admin",
        )

    def test_delete_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.delete(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Cluster deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_delete_fail(self):
        response = self.client.delete(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.get_non_existent_pk(model=Cluster)}),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Cluster deleted",
            operation_type="delete",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_create_mapping_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-mapping", kwargs={"pk": self.cluster_1.pk}),
            data=[{"hostId": self.host_1.pk, "componentId": self.component_1.pk}],
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name="Host-Component map updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_create_mapping_only_view_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View host-components"):
            response = self.client.post(
                path=reverse(viewname="v2:cluster-mapping", kwargs={"pk": self.cluster_1.pk}),
                data=[{"hostId": self.host_1.pk, "componentId": self.component_1.pk}],
            )
            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="Host-Component map updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_create_mapping_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(
            path=reverse(viewname="v2:cluster-mapping", kwargs={"pk": self.cluster_1.pk}),
            data=[{"hostId": self.host_1.pk, "componentId": self.component_1.pk}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Host-Component map updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_create_mapping_incorrect_body_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-mapping", kwargs={"pk": self.cluster_1.pk}),
            data=[{"host_id": 4}],
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="Host-Component map updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_create_mapping_not_found_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-mapping", kwargs={"pk": self.get_non_existent_pk(model=Cluster)}),
            data=[{"hostId": self.host_1.pk, "componentId": self.component_1.pk}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Host-Component map updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_create_import_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.import_cluster.pk}),
            data=[{"source": {"id": self.cluster_1.pk, "type": ObjectType.CLUSTER}}],
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name="Cluster import updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.import_cluster),
            user__username="admin",
        )

    def test_create_import_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(
            path=reverse(viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.import_cluster.pk}),
            data=[{"source": {"id": self.cluster_1.pk, "type": ObjectType.CLUSTER}}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Cluster import updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.import_cluster),
            user__username=self.test_user.username,
        )

    def test_create_import_incorrect_body_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.import_cluster.pk}),
            data=[{}],
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="Cluster import updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.import_cluster),
            user__username="admin",
        )

    def test_create_import_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster)}
            ),
            data=[{"source": {"id": self.cluster_1.pk, "type": ObjectType.CLUSTER}}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Cluster import updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_update_config_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=self.cluster_1_config_post_data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name="Cluster configuration updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_update_config_view_only_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
            response = self.client.post(
                path=reverse(viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.cluster_1.pk}),
                data=self.cluster_1_config_post_data,
            )
            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="Cluster configuration updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_update_config_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(
            path=reverse(viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=self.cluster_1_config_post_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Cluster configuration updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_update_config_incorrect_body_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="Cluster configuration updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_update_config_not_found_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster)}
            ),
            data=self.cluster_1_config_post_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Cluster configuration updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_delete_host_success(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:host-cluster-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk}
            ),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_record(
            operation_name=f"{self.host_1.name} host removed",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            object_changes={},
            user__username="admin",
        )

    def test_delete_host_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.delete(
            path=reverse(
                viewname="v2:host-cluster-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk}
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.host_1.name} host removed",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_delete_host_fail(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:host-cluster-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.get_non_existent_pk(model=Host)},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="host removed",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    # add single host

    def test_add_host_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"hostId": self.host_2.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name=f"[{self.host_2.name}] host(s) added",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_add_host_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"hostId": self.host_2.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"[{self.host_2.name}] host(s) added",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_add_host_incorrect_body_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="[] host(s) added",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_add_non_existing_host_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"hostId": self.get_non_existent_pk(Host)},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="[] host(s) added",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_add_host_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster)}
            ),
            data={"hostId": self.host_2.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"[{self.host_2.name}] host(s) added",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_add_host_wrong_data_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[{"totally": "wrong"}, "request data"],
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="[] host(s) added",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    # add multiple hosts

    def test_add_many_hosts_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[{"hostId": self.host_2.pk}, {"hostId": self.host_3.pk}],
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name=f"[{self.host_2.name}, {self.host_3.name}] host(s) added",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_add_many_hosts_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[{"hostId": self.host_2.pk}, {"hostId": self.host_3.pk}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"[{self.host_2.name}, {self.host_3.name}] host(s) added",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_add_many_hosts_incorrect_body_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[{"hey": "you"}, {"hostId": self.host_2.pk}],
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name=f"[{self.host_2.name}] host(s) added",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_add_many_non_existing_host_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[{"hostId": self.get_non_existent_pk(Host)}],
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="[] host(s) added",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_change_host_mm_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
            object_changes={"current": {"maintenance_mode": "on"}, "previous": {"maintenance_mode": "off"}},
            user__username="admin",
        )

    def test_change_host_mm_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
            user__username=self.test_user.username,
        )

    def test_change_host_mm_fail(self):
        cluster_proto = self.cluster_1.prototype
        cluster_proto.allow_maintenance_mode = False
        cluster_proto.save(update_fields=["allow_maintenance_mode"])

        response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        self.check_last_audit_record(
            operation_name="Host updated",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
            user__username="admin",
        )

    # add multiple services

    def test_add_service_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[
                {"prototypeId": self.service_add_prototypes[0].pk},
                {"prototypeId": self.service_add_prototypes[1].pk},
            ],
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name=(
                f"[{', '.join(proto.display_name for proto in self.service_add_prototypes)}] service(s) added"
            ),
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_add_service_wrong_data_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[
                {"id_of_prototype": self.service_add_prototypes[0].pk},
                {"prototypeId": self.service_add_prototypes[1].pk},
            ],
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name=f"[{self.service_add_prototypes[1].display_name}] service(s) added",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_add_service_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[
                {"prototypeId": self.service_add_prototypes[0].pk},
                {"prototypeId": self.service_add_prototypes[1].pk},
            ],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=(
                f"[{', '.join(proto.display_name for proto in self.service_add_prototypes)}] service(s) added"
            ),
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_add_service_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster)}),
            data=[
                {"prototypeId": self.service_add_prototypes[0].pk},
                {"prototypeId": self.service_add_prototypes[1].pk},
            ],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=(
                f"[{', '.join(proto.display_name for proto in self.service_add_prototypes)}] service(s) added"
            ),
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    # add single service

    def test_add_one_service_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"prototypeId": self.service_add_prototypes[0].pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_record(
            operation_name=(f"[{self.service_add_prototypes[0].display_name}] service(s) added"),
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_add_one_service_wrong_data_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"id_of_prototype": self.service_add_prototypes[0].pk},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_record(
            operation_name="[] service(s) added",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_add_one_service_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"prototypeId": self.service_add_prototypes[1].pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"[{self.service_add_prototypes[1].display_name}] service(s) added",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_add_one_service_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster)}),
            data={"prototypeId": self.service_add_prototypes[0].pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"[{self.service_add_prototypes[0].display_name}] service(s) added",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_delete_service_success(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:service-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_1.pk}
            ),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_record(
            operation_name=f"{self.service_1.display_name} service removed",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_delete_service_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.delete(
            path=reverse(
                viewname="v2:service-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_1.pk}
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.service_1.display_name} service removed",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_delete_non_existent_service_fail(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:service-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.get_non_existent_pk(model=ClusterObject)},
            ),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_record(
            operation_name="service removed",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_delete_service_from_non_existent_cluster_fail(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:service-detail",
                kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster), "pk": self.service_1.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.service_1.display_name} service removed",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_run_cluster_action_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-action-run", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_action.pk}
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_action.display_name} action launched",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_run_cluster_action_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
            response = self.client.post(
                path=reverse(
                    viewname="v2:cluster-action-run",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_action.pk},
                ),
            )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_action.display_name} action launched",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_run_cluster_action_incorrect_body_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-action-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "pk": Action.objects.get(name="with_config", prototype=self.cluster_1.prototype).pk,
                },
            ),
            data={},
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        self.check_last_audit_record(
            operation_name="with_config action launched",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_run_non_existent_cluster_action_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-action-run",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.get_non_existent_pk(model=Action)},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="action launched",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_run_host_action_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-action-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "host_pk": self.host_1.pk,
                    "pk": self.host_action.pk,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_record(
            operation_name=f"{self.host_action.display_name} action launched",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
            user__username="admin",
        )

    def test_run_host_action_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(
            to=self.test_user, on=self.host_1, role_name="View host configurations"
        ), self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
            response = self.client.post(
                path=reverse(
                    viewname="v2:host-cluster-action-run",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "host_pk": self.host_1.pk,
                        "pk": self.host_action.pk,
                    },
                ),
            )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name=f"{self.host_action.display_name} action launched",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
            user__username=self.test_user.username,
        )

    def test_run_host_action_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-action-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "host_pk": self.host_1.pk,
                    "pk": self.get_non_existent_pk(model=Action),
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="action launched",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.host_1),
            user__username="admin",
        )

    def test_upgrade_cluster_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "pk": self.cluster_upgrade.pk,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_upgrade.action.display_name} upgrade launched",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_upgrade_cluster_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
            response = self.client.post(
                path=reverse(
                    viewname="v2:upgrade-run",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "pk": self.cluster_upgrade.pk,
                    },
                ),
            )
            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name=f"{self.cluster_upgrade.action.display_name} upgrade launched",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username=self.test_user.username,
        )

    def test_upgrade_cluster_incorrect_data_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "pk": Upgrade.objects.get(bundle=self.upgrade_bundle, name="upgrade_via_action_complex").pk,
                },
            ),
            data={},
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        self.check_last_audit_record(
            operation_name="Upgrade: upgrade_via_action_complex upgrade launched",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_upgrade_cluster_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "pk": self.get_non_existent_pk(model=Upgrade),
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Upgraded to",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=self.cluster_1),
            user__username="admin",
        )

    def test_cluster_object_changes_one_field_success(self):
        response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
            data={"name": "new_cluster_name"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_record(
            operation_name="Cluster updated",
            operation_type="update",
            operation_result="success",
            user__username="admin",
            expect_object_changes_=True,
            object_changes={"current": {"name": "new_cluster_name"}, "previous": {"name": self.cluster_1.name}},
        )

    def test_cluster_object_changes_name_on_installed_fail(self):
        self.cluster_1.set_state("installed")
        response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
            data={"name": "new_cluster_name"},
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        self.check_last_audit_record(
            operation_name="Cluster updated",
            operation_type="update",
            operation_result="fail",
            user__username="admin",
            expect_object_changes_=False,
        )

    def test_cluster_object_changes_all_fields_success(self):
        response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
            data={"name": "new_cluster_name", "description": "new description"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        expected_object_changes = {
            "current": {"name": "new_cluster_name", "description": "new description"},
            "previous": {"name": self.cluster_1.name, "description": self.cluster_1.description},
        }
        self.check_last_audit_record(
            operation_name="Cluster updated",
            operation_type="update",
            operation_result="success",
            user__username="admin",
            expect_object_changes_=True,
            object_changes=expected_object_changes,
        )
