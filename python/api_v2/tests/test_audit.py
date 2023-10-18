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

from api_v2.tests.base import BaseAPITestCase
from audit.models import AuditLog, AuditObject, AuditSession
from cm.models import (
    Cluster,
    ClusterObject,
    Host,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from rbac.models import User
from rbac.services.user import create_user
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)


class TestAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.username = self.password = "user"
        self.user = User.objects.create_superuser(self.username, "user@example.com", self.password)
        self.login_for_audit(username=self.username, password=self.password)
        last_login = AuditSession.objects.last()
        self.last_login_id = last_login.id
        current_datetime = last_login.login_time
        self.time_from = (current_datetime - timedelta(minutes=1)).isoformat()
        self.time_to = (current_datetime + timedelta(minutes=1)).isoformat()

    def login_for_audit(self, username="admin", password="admin"):
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={"username": username, "password": password},
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

    def test_logins_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:audit:auditsession-list"),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["user"], {"name": self.username})

    def test_logins_time_filtering_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:audit:auditsession-list"),
            data={"time_to": self.time_to, "time_from": self.time_from},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["user"], {"name": self.username})

    def test_logins_time_filtering_empty_list_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:audit:auditsession-list"),
            data={"timeTo": self.time_from, "timeFrom": self.time_to},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 0)

    def test_logins_retrieve_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:audit:auditsession-detail", kwargs={"pk": self.last_login_id})
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["user"]["name"], self.username)

    def test_logins_retrieve_not_found_fail(self):
        response = self.client.get(
            path=reverse(viewname="v2:audit:auditsession-detail", kwargs={"pk": self.last_login_id + 1})
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_logins_not_authorized_fail(self):
        self.client.logout()
        response = self.client.get(path=reverse(viewname="v2:audit:auditsession-list"))
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)

    def test_operations_not_authorized_fail(self):
        self.client.logout()
        response = self.client.get(path=reverse(viewname="v2:audit:auditlog-list"))
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)

    def test_operations_list_success(self):
        response = self.client.get(path=reverse(viewname="v2:audit:auditlog-list"))
        self.assertEqual(response.status_code, HTTP_200_OK)


class TestClusterAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        create_user(**self.test_user_credentials)

        self.prototype = Prototype.objects.get(bundle=self.bundle_1, type=ObjectType.CLUSTER)

        self.host_1 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_1)

        self.host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host2")
        self.host_3 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host3")

        self.add_service_to_cluster(service_name="service_1", cluster=self.cluster_1)
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

    def _check_last_audit_log(self, **kwargs) -> None:
        audit_log = AuditLog.objects.order_by("-pk").first()
        self.assertIsNotNone(audit_log)

        expected_log = AuditLog.objects.filter(**kwargs)
        self.assertEqual(expected_log.count(), 1)
        self.assertEqual(audit_log.pk, expected_log.get().pk)

    def test_create_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototypeId": self.prototype.pk, "name": "audit_test_cluster"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self._check_last_audit_log(
            operation_name="Cluster created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=response.json()["id"],
            audit_object__object_name="audit_test_cluster",
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            user__username="admin",
        )

    def test_create_denied(self):
        self.client.login(**self.test_user_credentials)

        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototypeId": self.prototype.pk, "name": "audit_test_cluster"},
        )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self._check_last_audit_log(
            operation_name="Cluster created",
            operation_type="create",
            operation_result="denied",
            audit_object__isnull=True,
            user__username=self.test_user_credentials["username"],
        )

    def test_create_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototypeId": self.prototype.pk, "name": self.cluster_1.name},
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        self._check_last_audit_log(
            operation_name="Cluster created",
            operation_type="create",
            operation_result="fail",
            audit_object__isnull=True,
            user__username="admin",
        )

    def test_edit_success(self):
        old_name = self.cluster_1.name
        response: Response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
            data={"name": "new_cluster_name"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self._check_last_audit_log(
            operation_name="Cluster updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name="new_cluster_name",
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={"current": {"name": "new_cluster_name"}, "previous": {"name": old_name}},
            user__username="admin",
        )

    def test_edit_denied(self):
        self.client.login(**self.test_user_credentials)

        response: Response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
            data={"name": "new_cluster_name"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name="Cluster updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user_credentials["username"],
        )

    def test_edit_fail(self):
        response: Response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.get_non_existent_pk(model=Cluster)}),
            data={"name": "new_cluster_name"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name="Cluster updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_delete_success(self):
        AuditObject.objects.get_or_create(
            object_id=self.cluster_1.pk,
            object_name=self.cluster_1.name,
            object_type="cluster",
            is_deleted=False,
        )

        response: Response = self.client.delete(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self._check_last_audit_log(
            operation_name="Cluster deleted",
            operation_type="delete",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=True,
            object_changes={},
            user__username="admin",
        )

    def test_delete_denied(self):
        self.client.login(**self.test_user_credentials)

        response: Response = self.client.delete(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name="Cluster deleted",
            operation_type="delete",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user_credentials["username"],
        )

    def test_delete_fail(self):
        response: Response = self.client.delete(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.get_non_existent_pk(model=Cluster)}),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name="Cluster deleted",
            operation_type="delete",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_create_mapping_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:mapping-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[{"hostId": self.host_1.pk, "componentId": self.component_1.pk}],
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self._check_last_audit_log(
            operation_name="Host-Component map updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_create_mapping_denied(self):
        self.client.login(**self.test_user_credentials)

        response: Response = self.client.post(
            path=reverse(viewname="v2:mapping-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[{"hostId": self.host_1.pk, "componentId": self.component_1.pk}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name="Host-Component map updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user_credentials["username"],
        )

    def test_create_mapping_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:mapping-list", kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster)}),
            data=[{"hostId": self.host_1.pk, "componentId": self.component_1.pk}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name="Host-Component map updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_create_import_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.import_cluster.pk}),
            data=[{"source": {"id": self.cluster_1.pk, "type": ObjectType.CLUSTER}}],
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self._check_last_audit_log(
            operation_name="Cluster import updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.import_cluster.pk,
            audit_object__object_name=self.import_cluster.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_create_import_denied(self):
        self.client.login(**self.test_user_credentials)

        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.import_cluster.pk}),
            data=[{"source": {"id": self.cluster_1.pk, "type": ObjectType.CLUSTER}}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name="Cluster import updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.import_cluster.pk,
            audit_object__object_name=self.import_cluster.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user_credentials["username"],
        )

    def test_create_import_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster)}
            ),
            data=[{"source": {"id": self.cluster_1.pk, "type": ObjectType.CLUSTER}}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name="Cluster import updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_update_config_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=self.cluster_1_config_post_data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self._check_last_audit_log(
            operation_name="Cluster configuration updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_update_config_denied(self):
        self.client.login(**self.test_user_credentials)

        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=self.cluster_1_config_post_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name="Cluster configuration updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user_credentials["username"],
        )

    def test_update_config_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster)}
            ),
            data=self.cluster_1_config_post_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name="Cluster configuration updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_delete_host_success(self):
        response: Response = self.client.delete(
            path=reverse(
                viewname="v2:host-cluster-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk}
            ),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self._check_last_audit_log(
            operation_name=f"{self.host_1.name} host removed",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_delete_host_denied(self):
        self.client.login(**self.test_user_credentials)

        response: Response = self.client.delete(
            path=reverse(
                viewname="v2:host-cluster-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk}
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name=f"{self.host_1.name} host removed",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user_credentials["username"],
        )

    def test_delete_host_fail(self):
        response: Response = self.client.delete(
            path=reverse(
                viewname="v2:host-cluster-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.get_non_existent_pk(model=Host)},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name="host removed",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_add_host_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[{"hostId": self.host_2.pk}, {"hostId": self.host_3.pk}],
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self._check_last_audit_log(
            operation_name=f"[{self.host_2.name}, {self.host_3.name}] host(s) added",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_add_host_denied(self):
        self.client.login(**self.test_user_credentials)

        response: Response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[{"hostId": self.host_2.pk}, {"hostId": self.host_3.pk}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name=f"[{self.host_2.name}, {self.host_3.name}] host(s) added",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user_credentials["username"],
        )

    def test_add_host_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster)}
            ),
            data=[{"hostId": self.host_2.pk}, {"hostId": self.host_3.pk}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name=f"[{self.host_2.name}, {self.host_3.name}] host(s) added",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_add_host_wrong_data_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[{"totally": "wrong"}, "request data"],
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self._check_last_audit_log(
            operation_name=f"[] host(s) added",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_change_host_mm_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self._check_last_audit_log(
            operation_name="Host updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.host_1.pk,
            audit_object__object_name=self.host_1.name,
            audit_object__object_type="host",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_change_host_mm_denied(self):
        self.client.login(**self.test_user_credentials)

        response: Response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name=f"Host updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.host_1.pk,
            audit_object__object_name=self.host_1.name,
            audit_object__object_type="host",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user_credentials["username"],
        )

    def test_change_host_mm_fail(self):
        cluster_proto = self.cluster_1.prototype
        cluster_proto.allow_maintenance_mode = False
        cluster_proto.save(update_fields=["allow_maintenance_mode"])

        response: Response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        self._check_last_audit_log(
            operation_name="Host updated",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.host_1.pk,
            audit_object__object_name=self.host_1.name,
            audit_object__object_type="host",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_add_service_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[
                {"prototypeId": self.service_add_prototypes[0].pk},
                {"prototypeId": self.service_add_prototypes[1].pk},
            ],
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self._check_last_audit_log(
            operation_name=f"[{', '.join(proto.display_name for proto in self.service_add_prototypes)}] service(s) added",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_add_service_wrong_data_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[
                {"id_of_prototype": self.service_add_prototypes[0].pk},
                {"id_of_prototype": self.service_add_prototypes[1].pk},
            ],
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self._check_last_audit_log(
            operation_name=f"[] service(s) added",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_add_service_denied(self):
        self.client.login(**self.test_user_credentials)

        response: Response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[
                {"prototypeId": self.service_add_prototypes[0].pk},
                {"prototypeId": self.service_add_prototypes[1].pk},
            ],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name=f"[{', '.join(proto.display_name for proto in self.service_add_prototypes)}] service(s) added",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user_credentials["username"],
        )

    def test_add_service_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster)}),
            data=[
                {"prototypeId": self.service_add_prototypes[0].pk},
                {"prototypeId": self.service_add_prototypes[1].pk},
            ],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name=f"[{', '.join(proto.display_name for proto in self.service_add_prototypes)}] service(s) added",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_delete_service_success(self):
        response: Response = self.client.delete(
            path=reverse(
                viewname="v2:service-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_1.pk}
            ),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self._check_last_audit_log(
            operation_name=f"{self.service_1.display_name} service removed",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_delete_service_denied(self):
        self.client.login(**self.test_user_credentials)

        response: Response = self.client.delete(
            path=reverse(
                viewname="v2:service-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_1.pk}
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name=f"{self.service_1.display_name} service removed",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user_credentials["username"],
        )

    def test_delete_non_existent_service_fail(self):
        response: Response = self.client.delete(
            path=reverse(
                viewname="v2:service-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.get_non_existent_pk(model=ClusterObject)},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name="service removed",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_delete_service_from_non_existent_cluster_denied(self):
        response: Response = self.client.delete(
            path=reverse(
                viewname="v2:service-detail",
                kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster), "pk": self.service_1.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self._check_last_audit_log(
            operation_name=f"{self.service_1.display_name} service removed",
            operation_type="update",
            operation_result="denied",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )
