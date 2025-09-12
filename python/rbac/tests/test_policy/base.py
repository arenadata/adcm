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
from cm.models import Bundle, ObjectType, Prototype

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
        self.service_6_proto = Prototype.objects.get(
            bundle=Bundle.objects.get(name="test_cluster_for_cluster_admin_role"),
            name="service_6_manual_add",
            type=ObjectType.SERVICE,
        )
