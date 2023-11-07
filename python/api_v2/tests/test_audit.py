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

# pylint: disable=too-many-lines

from datetime import timedelta
from unittest.mock import patch

from api_v2.tests.base import BaseAPITestCase
from audit.models import (
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditSession,
)
from cm.models import (
    ADCM,
    Action,
    ActionType,
    Bundle,
    Cluster,
    ClusterObject,
    GroupConfig,
    Host,
    HostProvider,
    JobLog,
    JobStatus,
    ObjectType,
    Prototype,
    ServiceComponent,
    SubAction,
    TaskLog,
    Upgrade,
)
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rbac.models import Group, Policy, Role, User
from rbac.services.group import create as create_group
from rbac.services.policy import policy_create
from rbac.services.role import role_create
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


class AuditBaseTestCase(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = create_user(**self.test_user_credentials)


class TestClusterAudit(
    AuditBaseTestCase
):  # pylint: disable=too-many-instance-attributes, too-many-public-methods, too-many-ancestors
    def setUp(self) -> None:
        super().setUp()

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

        self.cluster_action = Action.objects.get(name="action", prototype=self.cluster_1.prototype)
        self.service_action = Action.objects.get(name="action", prototype=self.service_1.prototype)
        self.component_action = Action.objects.get(name="action_1_comp_1", prototype=self.component_1.prototype)
        self.host_action = Action.objects.get(name="cluster_on_host", prototype=self.cluster_1.prototype)

        upgrade_bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_one_upgrade")
        self.cluster_upgrade = Upgrade.objects.get(bundle=upgrade_bundle, name="upgrade_via_action_simple")

    def test_create_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototypeId": self.prototype.pk, "name": "audit_test_cluster"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
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

        self.check_last_audit_log(
            operation_name="Cluster created",
            operation_type="create",
            operation_result="denied",
            audit_object__isnull=True,
            user__username=self.test_user.username,
        )

    def test_create_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototypeId": self.prototype.pk, "name": self.cluster_1.name},
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        self.check_last_audit_log(
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

        self.check_last_audit_log(
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

        self.check_last_audit_log(
            operation_name="Cluster updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_edit_fail(self):
        response: Response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.get_non_existent_pk(model=Cluster)}),
            data={"name": "new_cluster_name"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
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

        self.check_last_audit_log(
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

        self.check_last_audit_log(
            operation_name="Cluster deleted",
            operation_type="delete",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_delete_fail(self):
        response: Response = self.client.delete(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.get_non_existent_pk(model=Cluster)}),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Cluster deleted",
            operation_type="delete",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_create_mapping_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-mapping", kwargs={"pk": self.cluster_1.pk}),
            data=[{"hostId": self.host_1.pk, "componentId": self.component_1.pk}],
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
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
            path=reverse(viewname="v2:cluster-mapping", kwargs={"pk": self.cluster_1.pk}),
            data=[{"hostId": self.host_1.pk, "componentId": self.component_1.pk}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Host-Component map updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_create_mapping_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-mapping", kwargs={"pk": self.get_non_existent_pk(model=Cluster)}),
            data=[{"hostId": self.host_1.pk, "componentId": self.component_1.pk}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
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
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
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

        self.check_last_audit_log(
            operation_name="Cluster import updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.import_cluster.pk,
            audit_object__object_name=self.import_cluster.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_create_import_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster)}
            ),
            data=[{"source": {"id": self.cluster_1.pk, "type": ObjectType.CLUSTER}}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
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

        self.check_last_audit_log(
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

        self.check_last_audit_log(
            operation_name="Cluster configuration updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_update_config_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:cluster-config-list", kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster)}
            ),
            data=self.cluster_1_config_post_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
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

        self.check_last_audit_log(
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

        self.check_last_audit_log(
            operation_name=f"{self.host_1.name} host removed",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_delete_host_fail(self):
        response: Response = self.client.delete(
            path=reverse(
                viewname="v2:host-cluster-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.get_non_existent_pk(model=Host)},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Host removed",
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
            data={"hostId": self.host_2.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.host_2.name} host added",
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
            data={"hostId": self.host_2.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.host_2.name} host added",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_add_host_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.get_non_existent_pk(model=Cluster)}
            ),
            data={"hostId": self.host_2.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.host_2.name} host added",
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

        self.check_last_audit_log(
            operation_name="host added",
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

        self.check_last_audit_log(
            operation_name="Host updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.host_1.pk,
            audit_object__object_name=self.host_1.name,
            audit_object__object_type="host",
            audit_object__is_deleted=False,
            object_changes={"current": {"maintenance_mode": "on"}, "previous": {"maintenance_mode": "off"}},
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

        self.check_last_audit_log(
            operation_name="Host updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.host_1.pk,
            audit_object__object_name=self.host_1.name,
            audit_object__object_type="host",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
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

        self.check_last_audit_log(
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

        self.check_last_audit_log(
            operation_name=(
                f"[{', '.join(proto.display_name for proto in self.service_add_prototypes)}] service(s) added"
            ),
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

        self.check_last_audit_log(
            operation_name="[] service(s) added",
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

        self.check_last_audit_log(
            operation_name=(
                f"[{', '.join(proto.display_name for proto in self.service_add_prototypes)}] service(s) added"
            ),
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
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

        self.check_last_audit_log(
            operation_name=(
                f"[{', '.join(proto.display_name for proto in self.service_add_prototypes)}] service(s) added"
            ),
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

        self.check_last_audit_log(
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

        self.check_last_audit_log(
            operation_name=f"{self.service_1.display_name} service removed",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_delete_non_existent_service_fail(self):
        response: Response = self.client.delete(
            path=reverse(
                viewname="v2:service-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.get_non_existent_pk(model=ClusterObject)},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
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

        self.check_last_audit_log(
            operation_name=f"{self.service_1.display_name} service removed",
            operation_type="update",
            operation_result="denied",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_run_cluster_action_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:cluster-action-run", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_action.pk}
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_log(
            operation_name=f"{self.cluster_action.display_name} action launched",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_run_cluster_action_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:cluster-action-run",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_action.pk},
                ),
            )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.cluster_action.display_name} action launched",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_run_non_existent_cluster_action_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:cluster-action-run",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.get_non_existent_pk(model=Action)},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="{action_display_name} action launched",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_run_service_action_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:service-action-run",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk, "pk": self.service_action.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_log(
            operation_name=f"{self.service_action.display_name} action launched",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type="service",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_run_service_action_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="View service configurations"):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:service-action-run",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "service_pk": self.service_1.pk,
                        "pk": self.service_action.pk,
                    },
                ),
            )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.service_action.display_name} action launched",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type="service",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_run_service_action_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:service-action-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.get_non_existent_pk(model=Action),
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="{action_display_name} action launched",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type="service",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_run_component_action_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:component-action-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "pk": self.component_action.pk,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_log(
            operation_name=f"{self.component_action.display_name} action launched",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type="component",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_run_component_action_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.component_1, role_name="View component configurations"):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:component-action-run",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "service_pk": self.service_1.pk,
                        "component_pk": self.component_1.pk,
                        "pk": self.component_action.pk,
                    },
                ),
            )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.component_action.display_name} action launched",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type="component",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_run_component_action_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:component-action-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "pk": self.get_non_existent_pk(model=Action),
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="{action_display_name} action launched",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type="component",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_run_host_action_success(self):
        response: Response = self.client.post(
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

        self.check_last_audit_log(
            operation_name=f"{self.host_action.display_name} action launched",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.host_1.pk,
            audit_object__object_name=self.host_1.name,
            audit_object__object_type="host",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_run_host_action_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(
            to=self.test_user, on=self.host_1, role_name="View host configurations"
        ), self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
            response: Response = self.client.post(
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

        self.check_last_audit_log(
            operation_name=f"{self.host_action.display_name} action launched",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.host_1.pk,
            audit_object__object_name=self.host_1.name,
            audit_object__object_type="host",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_run_host_action_fail(self):
        response: Response = self.client.post(
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

        self.check_last_audit_log(
            operation_name="{action_display_name} action launched",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.host_1.pk,
            audit_object__object_name=self.host_1.name,
            audit_object__object_type="host",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_upgrade_cluster_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "pk": self.cluster_upgrade.pk,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_log(
            operation_name=f"{self.cluster_upgrade.action.display_name} upgrade launched",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_upgrade_cluster_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:upgrade-run",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "pk": self.cluster_upgrade.pk,
                    },
                ),
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_log(
            operation_name=f"{self.cluster_upgrade.action.display_name} upgrade launched",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_upgrade_cluster_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "pk": self.get_non_existent_pk(model=Upgrade),
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Upgraded to",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )


class TestHostproviderAudit(AuditBaseTestCase):  # pylint: disable=too-many-ancestors
    def setUp(self) -> None:
        super().setUp()

        self.config_post_data = {
            "config": {
                "group": {"map": {"integer_key": "100", "string_key": "new string"}},
                "activatable_group": {
                    "secretmap": {
                        "integer_key": "100",
                        "string_key": "new string",
                    }
                },
                "json": '{"key": "value", "new key": "new value"}',
            },
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "description": "new provider config",
        }
        self.provider_action = Action.objects.get(name="provider_action", prototype=self.provider.prototype)

        upgrade_bundle = self.add_bundle(source_dir=self.test_bundles_dir / "provider_upgrade")
        self.provider_upgrade = Upgrade.objects.get(bundle=upgrade_bundle, name="upgrade")

    def test_create_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:hostprovider-list"),
            data={"prototypeId": self.provider.prototype.pk, "name": "test_provider"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name="Provider created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=response.json()["id"],
            audit_object__object_name="test_provider",
            audit_object__object_type="provider",
            audit_object__is_deleted=False,
            user__username="admin",
        )

    def test_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response: Response = self.client.post(
            path=reverse(viewname="v2:hostprovider-list"),
            data={"prototypeId": self.provider.prototype.pk, "name": "test_provider"},
        )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_log(
            operation_name="Provider created",
            operation_type="create",
            operation_result="denied",
            audit_object__isnull=True,
            user__username=self.test_user.username,
        )

    def test_create_duplicate_name_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:hostprovider-list"),
            data={"prototypeId": self.provider.prototype.pk, "name": self.provider.name},
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        self.check_last_audit_log(
            operation_name="Provider created",
            operation_type="create",
            operation_result="fail",
            audit_object__isnull=True,
            user__username="admin",
        )

    def test_create_non_existent_proto_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:hostprovider-list"),
            data={"prototypeId": self.get_non_existent_pk(model=Prototype), "name": "test_provider"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Provider created",
            operation_type="create",
            operation_result="fail",
            audit_object__isnull=True,
            user__username="admin",
        )

    def test_delete_success(self):
        AuditObject.objects.get_or_create(
            object_id=self.provider.pk,
            object_name=self.provider.name,
            object_type="provider",
            is_deleted=False,
        )

        response: Response = self.client.delete(
            path=reverse(viewname="v2:hostprovider-detail", kwargs={"pk": self.provider.pk}),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_log(
            operation_name="Provider deleted",
            operation_type="delete",
            operation_result="success",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type="provider",
            audit_object__is_deleted=True,
            user__username="admin",
        )

    def test_delete_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.provider, role_name="View provider configurations"):
            response: Response = self.client.delete(
                path=reverse(viewname="v2:hostprovider-detail", kwargs={"pk": self.provider.pk}),
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_log(
            operation_name="Provider deleted",
            operation_type="delete",
            operation_result="denied",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type="provider",
            audit_object__is_deleted=False,
            user__username=self.test_user.username,
        )

    def test_delete_non_existent_fail(self):
        response: Response = self.client.delete(
            path=reverse(
                viewname="v2:hostprovider-detail", kwargs={"pk": self.get_non_existent_pk(model=HostProvider)}
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Provider deleted",
            operation_type="delete",
            operation_result="fail",
            audit_object__isnull=True,
            user__username="admin",
        )

    def test_update_config_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:provider-config-list", kwargs={"hostprovider_pk": self.provider.pk}),
            data=self.config_post_data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name="Provider configuration updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type="provider",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_update_config_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.provider, role_name="View provider configurations"):
            response: Response = self.client.post(
                path=reverse(viewname="v2:provider-config-list", kwargs={"hostprovider_pk": self.provider.pk}),
                data=self.config_post_data,
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_log(
            operation_name="Provider configuration updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type="provider",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_update_config_wrong_data_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:provider-config-list", kwargs={"hostprovider_pk": self.provider.pk}),
            data={"wrong": ["d", "a", "t", "a"]},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_log(
            operation_name="Provider configuration updated",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type="provider",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_update_config_not_exists_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:provider-config-list",
                kwargs={"hostprovider_pk": self.get_non_existent_pk(model=HostProvider)},
            ),
            data=self.config_post_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Provider configuration updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_run_action_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:provider-action-run",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.provider_action.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_log(
            operation_name=f"{self.provider_action.display_name} action launched",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type="provider",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_run_action_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.provider, role_name="View provider configurations"):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:provider-action-run",
                    kwargs={"hostprovider_pk": self.provider.pk, "pk": self.provider_action.pk},
                ),
            )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.provider_action.display_name} action launched",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type="provider",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_run_action_not_exists_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:provider-action-run",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.get_non_existent_pk(model=Action)},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="{action_display_name} action launched",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type="provider",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_upgrade_provider_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                    "pk": self.provider_upgrade.pk,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_log(
            operation_name=f"Upgraded to {self.provider_upgrade.name}",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type="provider",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_upgrade_provider_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.provider, role_name="View provider configurations"):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:upgrade-run",
                    kwargs={
                        "hostprovider_pk": self.provider.pk,
                        "pk": self.provider_upgrade.pk,
                    },
                ),
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_log(
            operation_name=f"Upgraded to {self.provider_upgrade.name}",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type="provider",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_upgrade_provider_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                    "pk": self.get_non_existent_pk(model=Upgrade),
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Upgraded to",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type="provider",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )


class TestADCMAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = create_user(**self.test_user_credentials)

        self.adcm = ADCM.objects.first()
        self.data = {
            "config": {
                "global": {"adcm_url": "http://127.0.0.1:8000", "verification_public_key": "\n"},
                "google_oauth": {"client_id": None, "secret": None},
                "yandex_oauth": {"client_id": None, "secret": None},
                "ansible_settings": {"forks": 5},
                "logrotate": {"size": "10M", "max_history": 10, "compress": False},
                "audit_data_retention": {
                    "log_rotation_on_fs": 365,
                    "log_rotation_in_db": 365,
                    "config_rotation_in_db": 0,
                    "retention_period": 1825,
                    "data_archiving": False,
                },
                "ldap_integration": {
                    "ldap_uri": "test_ldap_uri",
                    "ldap_user": "test_ldap_user",
                    "ldap_password": "test_ldap_password",
                    "user_search_base": "test_ldap_user_search_base",
                    "user_search_filter": "https://test_ldap.url",
                    "user_object_class": "user",
                    "user_name_attribute": "sAMAccountName",
                    "group_search_base": None,
                    "group_search_filter": None,
                    "group_object_class": "group",
                    "group_name_attribute": "cn",
                    "group_member_attribute_name": "member",
                    "sync_interval": 60,
                    "tls_ca_cert_file": None,
                },
                "statistics_collection": {"url": "statistics_url"},
                "auth_policy": {
                    "min_password_length": 12,
                    "max_password_length": 20,
                    "login_attempt_limit": 5,
                    "block_time": 5,
                },
            },
            "adcmMeta": {
                "/logrotate": {"isActive": False},
                "/ldap_integration": {"isActive": False},
                "/statistics_collection": {"isActive": False},
            },
            "description": "new ADCM config",
        }

        Action.objects.filter(name="test_ldap_connection")

    def test_adcm_config_change_success(self):
        response = self.client.post(path=reverse(viewname="v2:adcm-config-list"), data=self.data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.check_last_audit_log(
            operation_name="ADCM configuration updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.adcm.pk,
            audit_object__object_name=self.adcm.name,
            audit_object__object_type="adcm",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_adcm_config_change_fail(self):
        response = self.client.post(path=reverse(viewname="v2:adcm-config-list"), data={})
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_last_audit_log(
            operation_name="ADCM configuration updated",
            operation_type="update",
            operation_result="fail",
            user__username="admin",
        )

    def test_adcm_config_change_access_fail(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(path=reverse(viewname="v2:adcm-config-list"), data=self.data)

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="ADCM configuration updated",
            operation_type="update",
            operation_result="fail",
            user__username=self.test_user_credentials["username"],
        )

    def test_adcm_profile_password_change_success(self):
        response = self.client.put(
            path=reverse(viewname="v2:profile"), data={"newPassword": "newtestpassword", "currentPassword": "admin"}
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_log(
            operation_name="admin user changed password",
            operation_type="update",
            operation_result="success",
            audit_object__is_deleted=False,
            user__username="admin",
        )

    def test_adcm_profile_password_change_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.put(
            path=reverse(viewname="v2:profile"), data={"newPassword": "newtestpassword", "currentPassword": "admin"}
        )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name=f"{self.test_user_credentials['username']} user changed password",
            operation_type="update",
            operation_result="denied",
            audit_object__is_deleted=False,
            user__username=self.test_user_credentials["username"],
        )

    def test_adcm_run_action_fail(self):
        adcm_action_pk = Action.objects.filter(name="test_ldap_connection").first().pk

        response = self.client.post(path=reverse(viewname="v2:adcm-action-run", kwargs={"pk": adcm_action_pk}))

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.check_last_audit_log(
            operation_name="Test LDAP connection action launched",
            operation_type="update",
            operation_result="fail",
            audit_object__is_deleted=False,
            user__username="admin",
        )

    def test_adcm_run_action_denied(self):
        adcm_action_pk = Action.objects.filter(name="test_ldap_connection").first().pk
        self.client.login(**self.test_user_credentials)

        response = self.client.post(path=reverse(viewname="v2:adcm-action-run", kwargs={"pk": adcm_action_pk}))

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="Test LDAP connection action launched",
            operation_type="update",
            operation_result="denied",
            audit_object__is_deleted=False,
            user__username=self.test_user_credentials["username"],
        )


class TestServiceAudit(AuditBaseTestCase):  # pylint: disable=too-many-ancestors
    def setUp(self) -> None:
        super().setUp()

        self.config_post_data = {
            "config": {
                "group": {"password": "newpassword"},
                "activatable_group": {"text": "new text"},
                "string": "new string",
            },
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "description": "new config",
        }

        self.export_service = self.add_service_to_cluster(service_name="service", cluster=self.cluster_2)
        self.add_service_to_cluster(service_name="service_1", cluster=self.cluster_1)
        self.service_1 = ClusterObject.objects.get(cluster=self.cluster_1, prototype__name="service_1")

        self.service_action = Action.objects.get(name="action", prototype=self.service_1.prototype)

    def test_update_config_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:service-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk},
            ),
            data=self.config_post_data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name="Service configuration updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type="service",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_update_config_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="View service configurations"):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:service-config-list",
                    kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk},
                ),
                data=self.config_post_data,
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_log(
            operation_name="Service configuration updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type="service",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_update_config_wrong_data_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:service-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk},
            ),
            data={"wrong": ["d", "a", "t", "a"]},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_log(
            operation_name="Service configuration updated",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type="service",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_update_config_not_exists_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:service-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.get_non_existent_pk(model=ClusterObject)},
            ),
            data=self.config_post_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Service configuration updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_change_mm_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:service-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_log(
            operation_name="Service updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type="service",
            audit_object__is_deleted=False,
            object_changes={"current": {"maintenance_mode": "on"}, "previous": {"maintenance_mode": "off"}},
            user__username="admin",
        )

    def test_change_mm_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="View service configurations"):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:service-maintenance-mode",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_1.pk},
                ),
                data={"maintenanceMode": "on"},
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_log(
            operation_name="Service updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type="service",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_change_mm_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:service-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.get_non_existent_pk(model=ClusterObject)},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Service updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_run_action_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:service-action-run",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk, "pk": self.service_action.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_log(
            operation_name=f"{self.service_action.display_name} action launched",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type="service",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_run_action_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=self.service_1, role_name="View service configurations"):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:service-action-run",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "service_pk": self.service_1.pk,
                        "pk": self.service_action.pk,
                    },
                ),
            )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.service_action.display_name} action launched",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type="service",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_run_action_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:service-action-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.get_non_existent_pk(model=Action),
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="{action_display_name} action launched",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type="service",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_create_import_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:service-import-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk},
            ),
            data=[{"source": {"id": self.export_service.pk, "type": ObjectType.SERVICE}}],
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name="Service import updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type="service",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_create_import_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(
            to=self.test_user, on=self.service_1, role_name="View service configurations"
        ), self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:service-import-list",
                    kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk},
                ),
                data=[{"source": {"id": self.export_service.pk, "type": ObjectType.SERVICE}}],
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_log(
            operation_name="Service import updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type="service",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_create_import_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:service-import-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.get_non_existent_pk(model=ClusterObject)},
            ),
            data=[{"source": {"id": self.export_service.pk, "type": ObjectType.SERVICE}}],
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Service import updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )


class TestBundleAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = create_user(**self.test_user_credentials)

    def test_audit_upload_success(self):
        new_bundle_file = self.prepare_bundle_file(source_dir=self.test_bundles_dir / "cluster_actions")
        with open(settings.DOWNLOAD_DIR / new_bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = self.client.post(
                path=reverse(viewname="v2:bundle-list"),
                data={"file": f},
                format="multipart",
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.check_last_audit_log(
            operation_name="Bundle uploaded",
            operation_result="success",
            operation_type=AuditLogOperationType.CREATE,
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_audit_delete_success(self):
        bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_actions")
        response = self.client.delete(path=reverse(viewname="v2:bundle-detail", kwargs={"pk": bundle.pk}))
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.check_last_audit_log(
            operation_name="Bundle deleted",
            operation_type="delete",
            operation_result="success",
            audit_object__object_id=bundle.pk,
            audit_object__object_name=bundle.name,
            audit_object__object_type="bundle",
            audit_object__is_deleted=True,
            object_changes={},
            user__username="admin",
        )

    def test_audit_delete_non_existent_fail(self):
        response = self.client.delete(path=reverse(viewname="v2:bundle-detail", kwargs={"pk": 100}))
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="Bundle deleted",
            operation_type="delete",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_audit_delete_denied(self):
        bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_actions")
        self.client.login(**self.test_user_credentials)
        response = self.client.delete(path=reverse(viewname="v2:bundle-detail", kwargs={"pk": bundle.pk}))
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="Bundle deleted",
            operation_type="delete",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user_credentials["username"],
        )

    def test_audit_accept_license_success(self):
        bundle = Bundle.objects.filter(name="cluster_one").first()
        bundle_prototype = Prototype.objects.get(bundle=bundle, type="cluster")

        response = self.client.post(
            path=reverse(viewname="v2:prototype-accept-license", kwargs={"pk": bundle_prototype.pk})
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_log(
            operation_name="Bundle license accepted",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=bundle.pk,
            audit_object__object_name=bundle.name,
            object_changes={},
            user__username="admin",
        )


class TestComponentAudit(AuditBaseTestCase):  # pylint: disable=too-many-ancestors
    def setUp(self) -> None:
        super().setUp()

        self.add_service_to_cluster(service_name="service_1", cluster=self.cluster_1)
        self.service_1 = ClusterObject.objects.get(cluster=self.cluster_1, prototype__name="service_1")
        self.component_1 = ServiceComponent.objects.get(prototype__name="component_1", service=self.service_1)
        self.component_action = Action.objects.get(name="action_1_comp_1", prototype=self.component_1.prototype)
        self.config_post_data = {
            "config": {
                "group": {"file": "new content"},
                "activatable_group": {"secretfile": "new content"},
                "secrettext": "new secrettext",
            },
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "description": "new config",
        }

    def test_run_action_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:component-action-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "pk": self.component_action.pk,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_log(
            operation_name=f"{self.component_action.display_name} action launched",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type="component",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_run_action_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with (
            self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"),
            self.grant_permissions(to=self.test_user, on=self.service_1, role_name="View service configurations"),
            self.grant_permissions(to=self.test_user, on=self.component_1, role_name="View component configurations"),
        ):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:component-action-run",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "service_pk": self.service_1.pk,
                        "component_pk": self.component_1.pk,
                        "pk": self.component_action.pk,
                    },
                ),
            )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.component_action.display_name} action launched",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type="component",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_run_action_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:component-action-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "pk": self.get_non_existent_pk(model=Action),
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="{action_display_name} action launched",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type="component",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_update_config_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:component-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                },
            ),
            data=self.config_post_data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name="Component configuration updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type="component",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_update_config_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with (
            self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"),
            self.grant_permissions(to=self.test_user, on=self.service_1, role_name="View service configurations"),
            self.grant_permissions(to=self.test_user, on=self.component_1, role_name="View component configurations"),
        ):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:component-config-list",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "service_pk": self.service_1.pk,
                        "component_pk": self.component_1.pk,
                    },
                ),
                data=self.config_post_data,
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_log(
            operation_name="Component configuration updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type="component",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_update_config_wrong_data_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:component-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                },
            ),
            data={"wrong": ["d", "a", "t", "a"]},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.check_last_audit_log(
            operation_name="Component configuration updated",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type="component",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_update_config_not_exists_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:component-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.get_non_existent_pk(model=ServiceComponent),
                },
            ),
            data=self.config_post_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Component configuration updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_change_mm_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:component-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk, "pk": self.component_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_log(
            operation_name="Component updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type="component",
            audit_object__is_deleted=False,
            object_changes={"current": {"maintenance_mode": "on"}, "previous": {"maintenance_mode": "off"}},
            user__username="admin",
        )

    def test_change_mm_denied(self):
        self.client.login(**self.test_user_credentials)

        with (
            self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"),
            self.grant_permissions(to=self.test_user, on=self.service_1, role_name="View service configurations"),
            self.grant_permissions(to=self.test_user, on=self.component_1, role_name="View component configurations"),
        ):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:component-maintenance-mode",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "service_pk": self.service_1.pk,
                        "pk": self.component_1.pk,
                    },
                ),
                data={"maintenanceMode": "on"},
            )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_log(
            operation_name="Component updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type="component",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_change_mm_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:component-maintenance-mode",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.get_non_existent_pk(model=ServiceComponent),
                },
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Component updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )


class TestHostAudit(AuditBaseTestCase):  # pylint: disable=too-many-ancestors,too-many-public-methods
    def setUp(self) -> None:
        super().setUp()

        self.prototype = Prototype.objects.get(bundle=self.bundle_1, type=ObjectType.CLUSTER)
        self.host_1 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host")
        self.host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_2")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_1)

    def test_create_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:host-list"),
            data={
                "hostproviderId": self.provider.pk,
                "name": "new-test-host",
            },
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name="Host created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=response.json()["id"],
            audit_object__object_name="new-test-host",
            audit_object__object_type="host",
            audit_object__is_deleted=False,
            user__username="admin",
        )

    def test_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response: Response = self.client.post(
            path=reverse(viewname="v2:host-list"),
            data={
                "hostproviderId": self.provider.pk,
                "name": "new-test-host",
            },
        )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_log(
            operation_name="Host created",
            operation_type="create",
            operation_result="denied",
            user__username=self.test_user.username,
        )

    def test_update_success(self):
        response: Response = self.client.patch(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host_2.pk}),
            data={"name": "new.name"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_log(
            operation_name="Host updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.host_2.pk,
            audit_object__object_name="new.name",
            audit_object__object_type="host",
            audit_object__is_deleted=False,
            user__username="admin",
        )

    def test_update_not_found_fail(self):
        response: Response = self.client.patch(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": 1000}),
            data={"name": "new.name"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Host updated",
            operation_type="update",
            operation_result="fail",
            user__username="admin",
        )

    def test_update_denied(self):
        self.client.login(**self.test_user_credentials)
        response: Response = self.client.patch(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host_2.pk}),
            data={"name": "new.name"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Host updated",
            operation_type="update",
            operation_result="fail",
            user__username=self.test_user.username,
        )

    def test_delete_success(self):
        AuditObject.objects.get_or_create(
            object_id=self.host_2.pk,
            object_name=self.host_2.name,
            object_type="host",
            is_deleted=False,
        )
        expected_audit_object_kwargs = {
            "audit_object__object_id": self.host_2.pk,
            "audit_object__object_name": self.host_2.name,
            "audit_object__object_type": "host",
            "audit_object__is_deleted": True,
        }

        response: Response = self.client.delete(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host_2.pk}),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.check_last_audit_log(
            operation_name="Host deleted",
            operation_type="delete",
            operation_result="success",
            **expected_audit_object_kwargs,
            user__username="admin",
        )

    def test_delete_not_found_fail(self):
        response: Response = self.client.delete(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": 1000}),
            data={"name": "new.name"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Host deleted",
            operation_type="delete",
            operation_result="fail",
            user__username="admin",
        )

    def test_delete_denied(self):
        self.client.login(**self.test_user_credentials)
        response: Response = self.client.delete(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host_2.pk}),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Host deleted",
            operation_type="delete",
            operation_result="fail",
            user__username=self.test_user.username,
        )

    def test_remove_from_cluster_success(self):
        response: Response = self.client.delete(
            path=reverse(
                viewname="v2:host-cluster-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk}
            ),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_log(
            operation_name=f"{self.host_1.fqdn} host removed",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            user__username="admin",
        )

    def test_remove_from_cluster_not_found_fail(self):
        response: Response = self.client.delete(
            path=reverse(viewname="v2:host-cluster-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": 1000}),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Host removed",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type="cluster",
            audit_object__is_deleted=False,
            user__username="admin",
        )

    def test_remove_from_cluster_denied(self):
        self.client.login(**self.test_user_credentials)
        response: Response = self.client.delete(
            path=reverse(
                viewname="v2:host-cluster-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk}
            ),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.host_1.fqdn} host removed",
            operation_type="update",
            operation_result="denied",
            user__username=self.test_user.username,
        )

    def test_switch_maintenance_mode_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:host-maintenance-mode",
                kwargs={"pk": self.host_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_log(
            operation_name="Host updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.host_1.pk,
            audit_object__object_name=self.host_1.name,
            audit_object__object_type="host",
            audit_object__is_deleted=False,
            user__username="admin",
        )

    def test_switch_maintenance_mode_not_found_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:host-maintenance-mode",
                kwargs={"pk": 1000},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Host updated",
            operation_type="update",
            operation_result="fail",
            user__username="admin",
        )

    def test_switch_maintenance_mode_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:host-maintenance-mode",
                kwargs={"pk": self.host_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_log(
            operation_name="Host updated",
            operation_type="update",
            operation_result="denied",
            user__username=self.test_user.username,
        )

    def test_switch_maintenance_mode_cluster_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_log(
            operation_name="Host updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.host_1.pk,
            audit_object__object_name=self.host_1.name,
            audit_object__object_type="host",
            audit_object__is_deleted=False,
            user__username="admin",
        )

    def test_switch_maintenance_mode_cluster_not_found_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": 1000},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Host updated",
            operation_type="update",
            operation_result="fail",
            user__username="admin",
        )

    def test_switch_maintenance_mode_cluster_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host_1.pk},
            ),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Host updated",
            operation_type="update",
            operation_result="denied",
            user__username=self.test_user.username,
        )

    def test_update_host_config_success(self):
        data = {
            "config": {
                "activatable_group": {"option": "string2"},
                "group": {"list": ["value1", "value2", "value3", "value4"]},
                "structure": [
                    {"integer": 1, "string": "string1"},
                    {"integer": 2, "string": "string2"},
                    {"integer": 3, "string": "string3"},
                ],
                "variant": "value2",
            },
            "adcmMeta": {"/activatable_group": {"isActive": True}},
            "description": "new config",
        }
        response = self.client.post(
            path=reverse(viewname="v2:host-config-list", kwargs={"host_pk": self.host_1.pk}),
            data=data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name="Host configuration updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.host_1.pk,
            audit_object__object_name=self.host_1.name,
            audit_object__object_type="host",
            audit_object__is_deleted=False,
            user__username="admin",
        )

    def test_update_host_config_not_found_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-config-list", kwargs={"host_pk": 1000}),
            data={},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Host configuration updated",
            operation_type="update",
            operation_result="fail",
            user__username="admin",
        )

    def test_update_host_config_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(viewname="v2:host-config-list", kwargs={"host_pk": self.host_1.pk}),
            data={},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="Host configuration updated",
            operation_type="update",
            operation_result="denied",
            user__username=self.test_user.username,
        )


class TestTaskJobAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = create_user(**self.test_user_credentials)

        self.adcm = ADCM.objects.first()
        self.action = Action.objects.create(
            display_name="test_adcm_action",
            prototype=self.adcm.prototype,
            type=ActionType.JOB,
            state_available="any",
        )
        self.task_for_job = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=timezone.now(),
            finish_date=timezone.now(),
            action=self.action,
        )
        self.job = JobLog.objects.create(
            status=JobStatus.RUNNING,
            start_date=timezone.now() + timedelta(days=1),
            finish_date=timezone.now() + timedelta(days=2),
            action=self.action,
            task=self.task_for_job,
            pid=9999,
            sub_action=SubAction.objects.create(
                action=self.action,
                allow_to_terminate=True,
            ),
        )
        self.task = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=timezone.now(),
            finish_date=timezone.now(),
        )

    def test_job_terminate_success(self):
        with patch("cm.models.os.kill"):
            response: Response = self.client.post(
                path=reverse(viewname="v2:joblog-terminate", kwargs={"pk": self.job.pk}), data={}
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            self.check_last_audit_log(
                operation_name="Job terminated",
                operation_type="update",
                operation_result="success",
                audit_object__object_id=1,
                audit_object__object_name="ADCM",
                audit_object__object_type="adcm",
                audit_object__is_deleted=False,
                object_changes={},
                user__username="admin",
            )

    def test_job_terminate_not_found_fail(self):
        with patch("cm.models.os.kill"):
            response: Response = self.client.post(
                path=reverse(viewname="v2:joblog-terminate", kwargs={"pk": 100}), data={}
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            self.check_last_audit_log(
                operation_name="Job terminated",
                operation_type="update",
                operation_result="fail",
                object_changes={},
                user__username="admin",
            )

    def test_job_terminate_denied(self):
        self.client.login(**self.test_user_credentials)
        with patch("cm.models.os.kill"):
            response: Response = self.client.post(
                path=reverse(viewname="v2:joblog-terminate", kwargs={"pk": self.job.pk}), data={}
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            self.check_last_audit_log(
                operation_name="Job terminated",
                operation_type="update",
                operation_result="denied",
                object_changes={},
                user__username=self.test_user.username,
            )

    def test_task_cancel_success(self):
        with patch("cm.models.TaskLog.cancel"):
            response = self.client.post(path=reverse(viewname="v2:tasklog-terminate", kwargs={"pk": self.task.pk}))
            self.assertEqual(response.status_code, HTTP_200_OK)

            self.check_last_audit_log(
                operation_name="Task cancelled",
                operation_type="update",
                operation_result="success",
                audit_object__object_id=1,
                audit_object__object_name="ADCM",
                audit_object__object_type="adcm",
                audit_object__is_deleted=False,
                object_changes={},
                user__username="admin",
            )

    def test_task_cancel_not_found_fail(self):
        with patch("cm.models.TaskLog.cancel"):
            response = self.client.post(path=reverse(viewname="v2:tasklog-terminate", kwargs={"pk": 1000}))
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            self.check_last_audit_log(
                operation_name="Task cancelled",
                operation_type="update",
                operation_result="fail",
                object_changes={},
                user__username="admin",
            )

    def test_task_cancel_denied(self):
        self.client.login(**self.test_user_credentials)
        with patch("cm.models.TaskLog.cancel"):
            response = self.client.post(path=reverse(viewname="v2:tasklog-terminate", kwargs={"pk": self.task.pk}))
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            self.check_last_audit_log(
                operation_name="Task cancelled",
                operation_type="update",
                operation_result="denied",
                object_changes={},
                user__username=self.test_user.username,
            )


class TestGroupConfigAudit(BaseAPITestCase):  # pylint: disable=too-many-public-methods,too-many-instance-attributes
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = create_user(**self.test_user_credentials)

        self.cluster_1_group_config = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.cluster_1),
            object_id=self.cluster_1.pk,
        )
        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="host")
        self.cluster_1_group_config.hosts.add(self.host)
        self.new_host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="new_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.new_host)

        self.service_1 = self.add_service_to_cluster(service_name="service_1", cluster=self.cluster_1)
        self.service_1_group_config = GroupConfig.objects.create(
            name="service_1_group_config",
            object_type=ContentType.objects.get_for_model(self.service_1),
            object_id=self.service_1.pk,
        )
        self.service_1_group_config.hosts.add(self.host)
        self.host_for_service = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_for_service"
        )
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_for_service)

        self.component_1 = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_1"
        )
        self.component_1_group_config = GroupConfig.objects.create(
            name="component_1_group_config",
            object_type=ContentType.objects.get_for_model(self.component_1),
            object_id=self.component_1.pk,
        )
        self.provider_group_config = GroupConfig.objects.create(
            name="group_config",
            object_type=ContentType.objects.get_for_model(self.provider),
            object_id=self.provider.pk,
        )
        self.add_hostcomponent_map(
            cluster=self.cluster_1,
            hc_map=[
                {
                    "host_id": self.host_for_service.pk,
                    "service_id": self.service_1.pk,
                    "component_id": self.component_1.pk,
                }
            ],
        )
        self.cluster_config_data = {
            "config": {
                "activatable_group": {"integer": 100},
                "boolean": False,
                "group": {"float": 2.1},
                "list": ["value1", "value2", "value3", "value4"],
                "variant_not_strict": "value5",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": False},
                "/boolean": {"isSynchronized": False},
                "/group/float": {"isSynchronized": False},
                "/variant_not_strict": {"isSynchronized": False},
                "/list": {"isSynchronized": False},
                "/activatable_group/integer": {"isSynchronized": False},
            },
            "description": "new config",
        }
        self.service_config_data = {
            "config": {
                "group": {"password": "newpassword"},
                "activatable_group": {"text": "new text"},
                "string": "new string",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": False},
                "/activatable_group/text": {"isSynchronized": False},
                "/group/password": {"isSynchronized": False},
                "/string": {"isSynchronized": False},
            },
            "description": "new config",
        }
        self.component_config_data = {
            "config": {
                "group": {"file": "new content"},
                "activatable_group": {"secretfile": "new content"},
                "secrettext": "new secrettext",
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": False},
                "/activatable_group/secretfile": {"isSynchronized": False},
                "/group/file": {"isSynchronized": False},
                "/secrettext": {"isSynchronized": False},
            },
            "description": "new config",
        }
        self.provider_config_data = {
            "config": {
                "group": {"map": {"integer_key": "100", "string_key": "new string"}},
                "activatable_group": {
                    "secretmap": {
                        "integer_key": "100",
                        "string_key": "new string",
                    }
                },
                "json": '{"key": "value", "new key": "new value"}',
            },
            "adcmMeta": {
                "/activatable_group": {"isActive": True, "isSynchronized": False},
                "/json": {"isSynchronized": False},
                "/group/map": {"isSynchronized": False},
                "/activatable_group/secretmap": {"isSynchronized": False},
            },
            "description": "new config",
        }

    def test_cluster_create_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-group-config-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name="group-config-new configuration group created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type=AuditObjectType.CLUSTER,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_cluster_create_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-group-config-list", kwargs={"cluster_pk": 1000}),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            object_changes={},
            audit_object__isnull=True,
            user__username="admin",
        )

    def test_cluster_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(viewname="v2:cluster-group-config-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_provider_create_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:hostprovider-group-config-list", kwargs={"hostprovider_pk": self.provider.pk}),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name="group-config-new configuration group created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type=AuditObjectType.PROVIDER,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_provider_create_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:hostprovider-group-config-list", kwargs={"hostprovider_pk": 1000}),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_provider_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(viewname="v2:hostprovider-group-config-list", kwargs={"hostprovider_pk": self.provider.pk}),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_component_create_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                },
            ),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name="group-config-new configuration group created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type=AuditObjectType.COMPONENT,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_component_create_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": 1000,
                },
            ),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_component_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                },
            ),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_service_create_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk},
            ),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name="group-config-new configuration group created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type=AuditObjectType.SERVICE,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_service_create_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": 1000},
            ),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_service_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk},
            ),
            data={"name": "group-config-new", "description": "group-config-new"},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group created",
            operation_type="create",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_cluster_delete_success(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:cluster-group-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_1_group_config.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_log(
            operation_name=f"{self.cluster_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type=AuditObjectType.CLUSTER,
            audit_object__is_deleted=True,
            object_changes={},
            user__username="admin",
        )

    def test_cluster_delete_fail(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:cluster-group-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": 1000},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_cluster_delete_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.delete(
            path=reverse(
                viewname="v2:cluster-group-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_1_group_config.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_provider_delete_success(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:hostprovider-group-config-detail",
                kwargs={"hostprovider_pk": self.cluster_1.pk, "pk": self.provider_group_config.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_log(
            operation_name=f"{self.provider_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="success",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type=AuditObjectType.PROVIDER,
            audit_object__is_deleted=True,
            object_changes={},
            user__username="admin",
        )

    def test_provider_delete_fail(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:hostprovider-group-config-detail",
                kwargs={"hostprovider_pk": self.cluster_1.pk, "pk": 1000},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_provider_delete_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.delete(
            path=reverse(
                viewname="v2:hostprovider-group-config-detail",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.provider_group_config.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_service_delete_success(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:service-group-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.service_1_group_config.pk,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_log(
            operation_name=f"{self.service_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="success",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type=AuditObjectType.SERVICE,
            audit_object__is_deleted=True,
            object_changes={},
            user__username="admin",
        )

    def test_service_delete_fail(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:service-group-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk, "pk": 1000},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_service_delete_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.delete(
            path=reverse(
                viewname="v2:service-group-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.service_1_group_config.pk,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_component_delete_success(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:component-group-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "pk": self.component_1_group_config.pk,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_log(
            operation_name=f"{self.component_1_group_config.name} configuration group deleted",
            operation_type="delete",
            operation_result="success",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type=AuditObjectType.COMPONENT,
            audit_object__is_deleted=True,
            object_changes={},
            user__username="admin",
        )

    def test_component_delete_fail(self):
        response = self.client.delete(
            path=reverse(
                viewname="v2:component-group-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "pk": 1000,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_component_delete_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.delete(
            path=reverse(
                viewname="v2:component-group-config-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "pk": self.component_1_group_config.pk,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group deleted",
            operation_type="delete",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_cluster_update_success(self):
        response = self.client.patch(
            path=reverse(
                viewname="v2:cluster-group-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_1_group_config.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.check_last_audit_log(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type=AuditObjectType.CLUSTER,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_cluster_update_fail(self):
        response = self.client.patch(
            path=reverse(
                viewname="v2:cluster-group-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": 1000},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group updated",
            operation_type="update",
            operation_result="fail",
            user__username="admin",
        )

    def test_cluster_update_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.patch(
            path=reverse(
                viewname="v2:cluster-group-config-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_1_group_config.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="configuration group updated",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_cluster_config_create_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.cluster_1_group_config.pk},
            ),
            data=self.cluster_config_data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type=AuditObjectType.CLUSTER,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_cluster_config_create_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-config-list",
                kwargs={"cluster_pk": 1000, "group_config_pk": self.cluster_1_group_config.pk},
            ),
            data=self.cluster_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_cluster_config_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-config-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.cluster_1_group_config.pk},
            ),
            data=self.cluster_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.cluster_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_service_config_create_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "group_config_pk": self.service_1_group_config.pk,
                },
            ),
            data=self.service_config_data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.service_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type=AuditObjectType.SERVICE,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_service_config_create_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": 1000,
                    "group_config_pk": self.service_1_group_config.pk,
                },
            ),
            data=self.service_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.service_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_service_config_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "group_config_pk": self.service_1_group_config.pk,
                },
            ),
            data=self.service_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.service_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_component_config_create_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.component_1_group_config.pk,
                },
            ),
            data=self.component_config_data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.component_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type=AuditObjectType.COMPONENT,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_component_config_create_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": 1000,
                    "group_config_pk": self.service_1_group_config.pk,
                },
            ),
            data=self.component_config_data,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.service_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_component_config_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-config-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.component_1_group_config.pk,
                },
            ),
            data=self.component_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.component_1_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_hostprovider_config_create_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:hostprovider-group-config-config-list",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                    "group_config_pk": self.provider_group_config.pk,
                },
            ),
            data=self.provider_config_data,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.provider_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type=AuditObjectType.PROVIDER,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_hostprovider_config_create_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:hostprovider-group-config-config-list",
                kwargs={
                    "hostprovider_pk": 1000,
                    "group_config_pk": self.provider_group_config.pk,
                },
            ),
            data=self.provider_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.provider_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_hostprovider_config_create_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:hostprovider-group-config-config-list",
                kwargs={
                    "hostprovider_pk": self.provider.pk,
                    "group_config_pk": self.provider_group_config.pk,
                },
            ),
            data=self.provider_config_data,
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.provider_group_config.name} configuration group updated",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_provider_add_host_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:hostprovider-group-config-hosts-list",
                kwargs={"hostprovider_pk": self.provider.pk, "group_config_pk": self.provider_group_config.pk},
            ),
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.new_host.fqdn} host added to {self.provider_group_config.name} configuration group",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.provider.pk,
            audit_object__object_name=self.provider.name,
            audit_object__object_type=AuditObjectType.PROVIDER,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_provider_add_host_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:hostprovider-group-config-hosts-list",
                kwargs={"hostprovider_pk": 1000, "group_config_pk": self.provider_group_config.pk},
            ),
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.new_host.fqdn} host added to {self.provider_group_config.name} configuration group",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_provider_add_host_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:hostprovider-group-config-hosts-list",
                kwargs={"hostprovider_pk": self.provider.pk, "group_config_pk": self.provider_group_config.pk},
            ),
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.new_host.fqdn} host added to {self.provider_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_service_add_host_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-hosts-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "group_config_pk": self.service_1_group_config.pk,
                },
            ),
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.service_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.service_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}",
            audit_object__object_type=AuditObjectType.SERVICE,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_service_add_host_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-hosts-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": 1000,
                    "group_config_pk": self.service_1_group_config.pk,
                },
            ),
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.service_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_service_add_host_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:service-group-config-hosts-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "group_config_pk": self.service_1_group_config.pk,
                },
            ),
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.service_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_cluster_add_host_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-hosts-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.cluster_1_group_config.pk},
            ),
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.new_host.fqdn} host added to {self.cluster_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.cluster_1.pk,
            audit_object__object_name=self.cluster_1.name,
            audit_object__object_type=AuditObjectType.CLUSTER,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_cluster_add_host_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-hosts-list",
                kwargs={"cluster_pk": 1000, "group_config_pk": self.cluster_1_group_config.pk},
            ),
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.new_host.fqdn} host added to {self.cluster_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_cluster_add_host_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:cluster-group-config-hosts-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "group_config_pk": self.cluster_1_group_config.pk},
            ),
            data={"hostId": self.new_host.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.new_host.fqdn} host added to {self.cluster_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_component_add_host_success(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-hosts-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.component_1_group_config.pk,
                },
            ),
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.check_last_audit_log(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.component_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.component_1.pk,
            audit_object__object_name=f"{self.cluster_1.name}/{self.service_1.name}/{self.component_1.name}",
            audit_object__object_type=AuditObjectType.COMPONENT,
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_component_add_host_fail(self):
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-hosts-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": 1000,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.component_1_group_config.pk,
                },
            ),
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.component_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="fail",
            object_changes={},
            user__username="admin",
        )

    def test_component_add_host_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.post(
            path=reverse(
                viewname="v2:component-group-config-hosts-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "group_config_pk": self.component_1_group_config.pk,
                },
            ),
            data={"hostId": self.host_for_service.pk},
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name=f"{self.host_for_service.fqdn} host "
            f"added to {self.component_1_group_config.name} configuration group",
            operation_type="update",
            operation_result="denied",
            object_changes={},
            user__username=self.test_user.username,
        )


# pylint: disable-next=too-many-ancestors,too-many-instance-attributes, too-many-public-methods
class TestRBACAudit(AuditBaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.blocked_user = create_user(username="blocked_user", password="blocked_user_pswd")
        self.blocked_user.blocked_at = timezone.now()
        self.blocked_user.save(update_fields=["blocked_at"])

        self.user_create_data = {
            "username": "newuser",
            "password": "newusernewuser",
            "firstName": "newuser",
            "lastName": "newuser",
            "email": "newuser@newuser.newuser",
            "isSuperUser": False,
        }
        self.user_update_data = {"lastName": "new_last_name"}
        self.role_create_data = {
            "displayName": "Custom `view cluster configurations` role",
            "children": [Role.objects.get(name="View cluster configurations").pk],
        }
        self.group_update_data = {
            "displayName": "new display name",
            "description": "new description",
            "users": [self.blocked_user.pk],
        }
        self.custom_role = role_create(
            display_name="Custom `view service configurations` role",
            child=[Role.objects.get(name="View service configurations")],
        )
        self.custom_role_name = "Custom role name"
        custom_role_2 = role_create(
            display_name=self.custom_role_name,
            child=[Role.objects.get(name="View cluster configurations")],
        )
        self.group = create_group(name_to_display="Some group")
        self.policy_create_data = {
            "name": "New Policy",
            "role": {"id": custom_role_2.pk},
            "objects": [{"id": self.cluster_1.pk, "type": "cluster"}],
            "groups": [self.group.pk],
        }
        self.policy_update_data = {"name": "Updated name"}
        self.policy = policy_create(
            name="Test policy",
            role=Role.objects.get(name="View provider configurations"),
            group=[create_group(name_to_display="Other group")],
            object=[self.provider],
        )

    def test_user_create_success(self):
        response: Response = self.client.post(path=reverse(viewname="v2:rbac:user-list"), data=self.user_create_data)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.check_last_audit_log(
            operation_name="User created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=response.json()["id"],
            audit_object__object_name=self.user_create_data["username"],
            audit_object__object_type="user",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_user_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response: Response = self.client.post(path=reverse(viewname="v2:rbac:user-list"), data={"wrong": "data"})

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="User created",
            operation_type="create",
            operation_result="denied",
            audit_object__isnull=True,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_user_create_wrong_data_fail(self):
        response: Response = self.client.post(path=reverse(viewname="v2:rbac:user-list"), data={"wrong": "data"})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_last_audit_log(
            operation_name="User created",
            operation_type="create",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_user_update_success(self):
        response: Response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.test_user.pk}), data=self.user_update_data
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_log(
            operation_name="User updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.test_user.pk,
            audit_object__object_name=self.test_user.username,
            audit_object__object_type="user",
            audit_object__is_deleted=False,
            object_changes={"current": {"last_name": "new_last_name"}, "previous": {"last_name": ""}},
            user__username="admin",
        )

    def test_user_update_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View users"):
            response: Response = self.client.patch(
                path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.blocked_user.pk}),
                data=self.user_update_data,
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="User updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.blocked_user.pk,
            audit_object__object_name=self.blocked_user.username,
            audit_object__object_type="user",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_user_update_no_view_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response: Response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.blocked_user.pk}),
            data=self.user_update_data,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="User updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.blocked_user.pk,
            audit_object__object_name=self.blocked_user.username,
            audit_object__object_type="user",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_user_update_not_exists_fail(self):
        response: Response = self.client.patch(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.get_non_existent_pk(model=User)}),
            data=self.user_update_data,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="User updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_user_delete_success(self):
        AuditObject.objects.get_or_create(
            object_id=self.blocked_user.pk,
            object_name=self.blocked_user.name,
            object_type="user",
            is_deleted=False,
        )
        expected_audit_object_kwargs = {
            "audit_object__object_id": self.blocked_user.pk,
            "audit_object__object_name": self.blocked_user.name,
            "audit_object__object_type": "user",
            "audit_object__is_deleted": True,
        }

        response: Response = self.client.delete(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.blocked_user.pk})
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.check_last_audit_log(
            operation_name="User deleted",
            operation_type="delete",
            operation_result="success",
            **expected_audit_object_kwargs,
            object_changes={},
            user__username="admin",
        )

    def test_user_delete_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View users"):
            response: Response = self.client.delete(
                path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.blocked_user.pk})
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="User deleted",
            operation_type="delete",
            operation_result="denied",
            audit_object__object_id=self.blocked_user.pk,
            audit_object__object_name=self.blocked_user.username,
            audit_object__object_type="user",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_user_delete_non_existent_fail(self):
        response: Response = self.client.delete(
            path=reverse(viewname="v2:rbac:user-detail", kwargs={"pk": self.get_non_existent_pk(model=User)})
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="User deleted",
            operation_type="delete",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_user_unblock_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:rbac:user-unblock", kwargs={"pk": self.blocked_user.pk})
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_log(
            operation_name=f"{self.blocked_user.username} user unblocked",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.blocked_user.pk,
            audit_object__object_name=self.blocked_user.username,
            audit_object__object_type="user",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_user_unblock_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View users"):
            response: Response = self.client.post(
                path=reverse(viewname="v2:rbac:user-unblock", kwargs={"pk": self.blocked_user.pk})
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name=f"{self.blocked_user.username} user unblocked",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.blocked_user.pk,
            audit_object__object_name=self.blocked_user.username,
            audit_object__object_type="user",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_user_unblock_not_exists_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:rbac:user-unblock", kwargs={"pk": self.get_non_existent_pk(model=User)})
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="user unblocked",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_role_create_success(self):
        response = self.client.post(path=reverse(viewname="v2:rbac:role-list"), data=self.role_create_data)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.check_last_audit_log(
            operation_name="Role created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=response.json()["id"],
            audit_object__object_name=self.role_create_data["displayName"],
            audit_object__object_type="role",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_role_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(path=reverse(viewname="v2:rbac:role-list"), data=self.role_create_data)

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="Role created",
            operation_type="create",
            operation_result="denied",
            audit_object__isnull=True,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_role_create_wrong_data_fail(self):
        response = self.client.post(path=reverse(viewname="v2:rbac:role-list"), data={"displayName": "Some role"})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_last_audit_log(
            operation_name="Role created",
            operation_type="create",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_role_update_success(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.custom_role.pk}),
            data=self.role_create_data,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_log(
            operation_name="Role updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.custom_role.pk,
            audit_object__object_name=self.custom_role.name,
            audit_object__object_type="role",
            audit_object__is_deleted=False,
            object_changes={
                "current": {
                    "display_name": "Custom `view cluster configurations` role",
                    "child": ["View cluster configurations"],
                },
                "previous": {
                    "display_name": "Custom `view service configurations` role",
                    "child": ["View service configurations"],
                },
            },
            user__username="admin",
        )

    def test_role_update_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View roles"):
            response = self.client.patch(
                path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.custom_role.pk}),
                data=self.role_create_data,
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="Role updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.custom_role.pk,
            audit_object__object_name=self.custom_role.name,
            audit_object__object_type="role",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_role_update_duplicate_name_fail(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.custom_role.pk}),
            data={"display_name": self.custom_role_name},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.check_last_audit_log(
            operation_name="Role updated",
            operation_type="update",
            operation_result="fail",
            audit_object__object_id=self.custom_role.pk,
            audit_object__object_name=self.custom_role.name,
            audit_object__object_type="role",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_role_delete_success(self):
        AuditObject.objects.get_or_create(
            object_id=self.custom_role.pk,
            object_name=self.custom_role.name,
            object_type="role",
            is_deleted=False,
        )
        expected_audit_object_kwargs = {
            "audit_object__object_id": self.custom_role.pk,
            "audit_object__object_name": self.custom_role.name,
            "audit_object__object_type": "role",
            "audit_object__is_deleted": True,
        }
        response = self.client.delete(path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.custom_role.pk}))

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.check_last_audit_log(
            operation_name="Role deleted",
            operation_type="delete",
            operation_result="success",
            **expected_audit_object_kwargs,
            object_changes={},
            user__username="admin",
        )

    def test_role_delete_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View roles"):
            response = self.client.delete(
                path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.custom_role.pk})
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="Role deleted",
            operation_type="delete",
            operation_result="denied",
            audit_object__object_id=self.custom_role.pk,
            audit_object__object_name=self.custom_role.name,
            audit_object__object_type="role",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_role_delete_not_exists_fail(self):
        response = self.client.delete(
            path=reverse(viewname="v2:rbac:role-detail", kwargs={"pk": self.get_non_existent_pk(model=Role)})
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="Role deleted",
            operation_type="delete",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_group_create_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:rbac:group-list"),
            data={"displayName": "New test group"},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.check_last_audit_log(
            operation_name="Group created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=response.json()["id"],
            audit_object__object_name=response.json()["name"],
            audit_object__object_type="group",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_group_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View group"):
            response: Response = self.client.post(
                path=reverse(viewname="v2:rbac:group-list"),
                data={"displayName": "New test group"},
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="Group created",
            operation_type="create",
            operation_result="denied",
            audit_object__isnull=True,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_group_create_wrong_data_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:rbac:group-list"),
            data={"description": "dscr"},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_last_audit_log(
            operation_name="Group created",
            operation_type="create",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_group_update_success(self):
        expected_object_changes = {
            "current": {
                "description": "new description",
                "name": "new display name",
                "user": [self.blocked_user.username],
            },
            "previous": {"description": None, "name": "Some group", "user": []},
        }

        response: Response = self.client.patch(
            path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.group.pk}),
            data=self.group_update_data,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        last_audit_log = self.check_last_audit_log(
            operation_name="Group updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.group.pk,
            audit_object__object_name=f"{self.group_update_data['displayName']} [{self.group.type}]",
            audit_object__object_type="group",
            audit_object__is_deleted=False,
            user__username="admin",
        )
        self.assertDictEqual(last_audit_log.object_changes, expected_object_changes)

    def test_group_update_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View group"):
            response: Response = self.client.patch(
                path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.group.pk}),
                data=self.group_update_data,
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="Group updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.group.pk,
            audit_object__object_name=self.group.name,
            audit_object__object_type="group",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_group_update_not_exists_fail(self):
        response: Response = self.client.patch(
            path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.get_non_existent_pk(model=Group)}),
            data=self.group_update_data,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="Group updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_group_delete_success(self):
        AuditObject.objects.get_or_create(
            object_id=self.group.pk,
            object_name=self.group.name,
            object_type="group",
            is_deleted=False,
        )
        expected_audit_object_kwargs = {
            "audit_object__object_id": self.group.pk,
            "audit_object__object_name": self.group.name,
            "audit_object__object_type": "group",
            "audit_object__is_deleted": True,
        }

        response: Response = self.client.delete(
            path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.group.pk}),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.check_last_audit_log(
            operation_name="Group deleted",
            operation_type="delete",
            operation_result="success",
            object_changes={},
            **expected_audit_object_kwargs,
            user__username="admin",
        )

    def test_group_delete_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View group"):
            response: Response = self.client.delete(
                path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.group.pk}),
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="Group deleted",
            operation_type="delete",
            operation_result="denied",
            object_changes={},
            audit_object__object_id=self.group.pk,
            audit_object__object_name=self.group.name,
            audit_object__object_type="group",
            audit_object__is_deleted=False,
            user__username=self.test_user.username,
        )

    def test_group_delete_not_exists_fail(self):
        response: Response = self.client.delete(
            path=reverse(viewname="v2:rbac:group-detail", kwargs={"pk": self.get_non_existent_pk(model=Group)}),
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="Group deleted",
            operation_type="delete",
            operation_result="fail",
            object_changes={},
            audit_object__isnull=True,
            user__username="admin",
        )

    def test_policy_create_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:rbac:policy-list"),
            data=self.policy_create_data,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.check_last_audit_log(
            operation_name="Policy created",
            operation_type="create",
            operation_result="success",
            audit_object__object_id=response.json()["id"],
            audit_object__object_name=response.json()["name"],
            audit_object__object_type="policy",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_policy_create_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View policy"):
            response = self.client.post(
                path=reverse(viewname="v2:rbac:policy-list"),
                data=self.policy_create_data,
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="Policy created",
            operation_type="create",
            operation_result="denied",
            audit_object__isnull=True,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_policy_create_wrong_data_fail(self):
        wrong_data = self.policy_create_data.copy()
        wrong_data["objects"] = [{"id": self.provider.pk, "type": "provider"}]

        response = self.client.post(
            path=reverse(viewname="v2:rbac:policy-list"),
            data=wrong_data,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_last_audit_log(
            operation_name="Policy created",
            operation_type="create",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_policy_edit_success(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.policy.pk}),
            data=self.policy_update_data,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_log(
            operation_name="Policy updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.policy.pk,
            audit_object__object_name=self.policy_update_data["name"],
            audit_object__object_type="policy",
            audit_object__is_deleted=False,
            object_changes={"current": {"name": "Updated name"}, "previous": {"name": "Test policy"}},
            user__username="admin",
        )

    def test_policy_edit_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View policy"):
            response = self.client.patch(
                path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.policy.pk}),
                data=self.policy_update_data,
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="Policy updated",
            operation_type="update",
            operation_result="denied",
            audit_object__object_id=self.policy.pk,
            audit_object__object_name=self.policy.name,
            audit_object__object_type="policy",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_policy_edit_not_exists_fail(self):
        response = self.client.patch(
            path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.get_non_existent_pk(model=Policy)}),
            data=self.policy_update_data,
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="Policy updated",
            operation_type="update",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )

    def test_policy_delete_success(self):
        AuditObject.objects.get_or_create(
            object_id=self.policy.pk,
            object_name=self.policy.name,
            object_type="policy",
            is_deleted=False,
        )
        expected_audit_object_kwargs = {
            "audit_object__object_id": self.policy.pk,
            "audit_object__object_name": self.policy.name,
            "audit_object__object_type": "policy",
            "audit_object__is_deleted": True,
        }

        response = self.client.delete(path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.policy.pk}))

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.check_last_audit_log(
            operation_name="Policy deleted",
            operation_type="delete",
            operation_result="success",
            **expected_audit_object_kwargs,
            object_changes={},
            user__username="admin",
        )

    def test_policy_delete_no_perms_denied(self):
        self.client.login(**self.test_user_credentials)

        with self.grant_permissions(to=self.test_user, on=[], role_name="View policy"):
            response = self.client.delete(path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.policy.pk}))

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_log(
            operation_name="Policy deleted",
            operation_type="delete",
            operation_result="denied",
            audit_object__object_id=self.policy.pk,
            audit_object__object_name=self.policy.name,
            audit_object__object_type="policy",
            audit_object__is_deleted=False,
            object_changes={},
            user__username=self.test_user.username,
        )

    def test_policy_delete_not_exists_fail(self):
        response = self.client.delete(
            path=reverse(viewname="v2:rbac:policy-detail", kwargs={"pk": self.get_non_existent_pk(model=Policy)})
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="Policy deleted",
            operation_type="delete",
            operation_result="fail",
            audit_object__isnull=True,
            object_changes={},
            user__username="admin",
        )
