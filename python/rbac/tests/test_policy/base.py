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

from adcm.tests.base import BaseTestCase
from cm.models import Bundle, Host, ObjectType, Prototype, Service

from rbac.models import Group


class PolicyBaseTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.new_user_password = "new_user_password"
        self.new_user_group = Group.objects.create(name="new_group")
        self.new_user = self.get_new_user(
            username="new_user", password=self.new_user_password, group_pk=self.new_user_group.pk
        )

        bundle = self.upload_and_load_bundle(
            path=(self.base_dir / "python" / "rbac" / "tests" / "files" / "test_cluster_for_cluster_admin_role.tar"),
        )
        self.cluster = self.create_cluster(bundle_pk=bundle.pk, name="Test Cluster")
        self.provider = self.create_provider(
            bundle_path=self.base_dir / "python" / "rbac" / "tests" / "files" / "provider.tar",
            name="Test Provider",
        )
        host_pks = self.create_hosts()
        self.first_host_pk = host_pks[0]
        self.last_host_pk = host_pks[-1]
        self.service_6_proto = Prototype.objects.get(
            bundle=Bundle.objects.get(name="test_cluster_for_cluster_admin_role"),
            name="service_6_manual_add",
            type=ObjectType.SERVICE,
        )
        service_ids = self.get_service_ids()
        self.last_service_pk = service_ids[-1]
        self.host_component = self.get_host_components()
        self.last_component_pk = self.host_component[-1]["component_id"]

    def create_hosts(self) -> list[int]:
        host_ids = []

        for host_num in range(5):
            name = f"host-{host_num}"
            host = self.create_host_in_cluster(provider_pk=self.provider.pk, name=name, cluster_pk=self.cluster.pk)
            host_ids.append(host.pk)

        return host_ids

    def get_service_ids(self) -> list[int]:
        service_prototypes = Prototype.objects.filter(
            bundle=Bundle.objects.get(name="test_cluster_for_cluster_admin_role"), type=ObjectType.SERVICE
        ).exclude(pk=self.service_6_proto.pk)
        service_ids = []

        for service_prototype in service_prototypes:
            service = self.create_service(cluster_pk=self.cluster.pk, name=service_prototype.name)
            service_ids.append(service.pk)

        return service_ids

    def get_host_components(self) -> list[dict]:
        host_pks = [host.pk for host in Host.objects.order_by("id")]
        services = list(Service.objects.order_by("id"))
        hostcomponent_data = []

        for host_pk, service in zip(host_pks, services):
            hostcomponent_data.extend(self.get_hostcomponent_data(service_pk=service.pk, host_pk=host_pk))

        self.create_hostcomponent(cluster_pk=self.cluster.pk, hostcomponent_data=hostcomponent_data)

        return hostcomponent_data
