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
from cm.api import add_cluster, add_host, add_host_provider, add_host_to_cluster
from cm.bundle import prepare_bundle
from cm.models import ADCM, Cluster, ConfigLog, Host, ObjectType, Prototype
from django.conf import settings
from init_db import init
from rbac.upgrade.role import init_roles
from rest_framework.test import APITestCase


class BaseAPITestCase(APITestCase):  # pylint: disable=too-many-instance-attributes
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        init_roles()
        init()

        adcm = ADCM.objects.first()
        config_log = ConfigLog.objects.get(obj_ref=adcm.config)
        config_log.config["auth_policy"]["max_password_length"] = 20
        config_log.save(update_fields=["config"])

    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        cluster_bundle_1_path = settings.BASE_DIR / "python" / "api_v2" / "tests" / "files" / "cluster_one"
        cluster_bundle_2_path = settings.BASE_DIR / "python" / "api_v2" / "tests" / "files" / "cluster_two"
        provider_bundle_path = settings.BASE_DIR / "python" / "api_v2" / "tests" / "files" / "provider"

        self.bundle_1 = prepare_bundle(bundle_file="cluster_1", bundle_hash="cluster_1", path=cluster_bundle_1_path)
        self.bundle_2 = prepare_bundle(bundle_file="cluster_2", bundle_hash="cluster_2", path=cluster_bundle_2_path)
        self.provider_bundle = prepare_bundle(bundle_file="provider", bundle_hash="provider", path=provider_bundle_path)
        self.cluster_1_prototype = Prototype.objects.filter(bundle=self.bundle_1, type=ObjectType.CLUSTER).first()
        self.cluster_1 = add_cluster(prototype=self.cluster_1_prototype, name="cluster_1", description="cluster_1")
        self.cluster_2_prototype = Prototype.objects.filter(bundle=self.bundle_2, type=ObjectType.CLUSTER).first()
        self.cluster_2 = add_cluster(prototype=self.cluster_2_prototype, name="cluster_2", description="cluster_2")
        self.provider_prototype = Prototype.objects.filter(
            bundle=self.provider_bundle, type=ObjectType.PROVIDER
        ).first()
        self.provider = add_host_provider(prototype=self.provider_prototype, name="provider", description="provider")
        self.host_prototype = Prototype.objects.filter(bundle=self.provider_bundle, type=ObjectType.HOST).first()

    def add_host(self, fqdn: str) -> Host:
        return add_host(prototype=self.host_prototype, provider=self.provider, fqdn=fqdn, description=fqdn)

    @staticmethod
    def add_host_to_cluster(cluster: Cluster, host: Host) -> Host:
        return add_host_to_cluster(cluster=cluster, host=host)
