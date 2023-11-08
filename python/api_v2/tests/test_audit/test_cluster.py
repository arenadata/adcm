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

from api_v2.tests.base import BaseAPITestCase
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
from rbac.services.user import create_user
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


class TestClusterAudit(BaseAPITestCase):  # pylint:disable=too-many-public-methods, too-many-instance-attributes
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = create_user(**self.test_user_credentials)

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
        response = self.client.post(
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

        response = self.client.post(
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
        response = self.client.post(
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
        response = self.client.patch(
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

        response = self.client.patch(
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
        response = self.client.patch(
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

        response = self.client.delete(
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

        response = self.client.delete(
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
        response = self.client.delete(
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
        response = self.client.post(
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

        response = self.client.post(
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
        response = self.client.post(
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
        response = self.client.post(
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

        response = self.client.post(
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
        response = self.client.post(
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
        response = self.client.post(
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

        response = self.client.post(
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
        response = self.client.post(
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
        response = self.client.delete(
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

        response = self.client.delete(
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
        response = self.client.delete(
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
        response = self.client.post(
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

        response = self.client.post(
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
        response = self.client.post(
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
        response = self.client.post(
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

        response = self.client.post(
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
        response = self.client.post(
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
        response = self.client.post(
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

        response = self.client.post(
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
        response = self.client.post(
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
        response = self.client.delete(
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

        response = self.client.delete(
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
        response = self.client.delete(
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
        response = self.client.delete(
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
        response = self.client.post(
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
            response = self.client.post(
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
        response = self.client.post(
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
