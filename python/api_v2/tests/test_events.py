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

from pathlib import Path

from cm.models import ConfigHostGroup
from core.types import ADCMHostGroupType
from django.contrib.contenttypes.models import ContentType
from djangorestframework_camel_case.util import camelize
from rbac.models import Group, Role, User
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from tests.base import WithPreparedFSAndInitADCM
from tests.client import ADCMTestClient
from tests.dependencies import get_status_scenarios_manager
from tests.deprecated import BusinessLogicMixin
from tests.utils import assert_dict_contains_subset
import django.test


class TestEventIsSent(django.test.TransactionTestCase, WithPreparedFSAndInitADCM, BusinessLogicMixin):
    client: ADCMTestClient
    client_class = ADCMTestClient

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_bundles_dir = Path(__file__).parent / "bundles"
        cls.test_files_dir = Path(__file__).parent / "files"

    def setUp(self) -> None:
        get_status_scenarios_manager().reset()
        self.client.login(username="admin", password="admin")

        cluster_bundle_1_path = self.test_bundles_dir / "cluster_one"
        provider_bundle_path = self.test_bundles_dir / "provider"

        self.bundle_1 = self.uc.upload_bundle(cluster_bundle_1_path)
        self.provider_bundle = self.uc.upload_bundle(provider_bundle_path)

        self.cluster_1 = self.uc.add_cluster(bundle=self.bundle_1, name="cluster_1", description="cluster_1")
        self.provider = self.uc.add_provider(bundle=self.provider_bundle, name="provider", description="provider")

        self.host_1 = self.uc.add_host(provider=self.provider, fqdn="host-1")
        self.group = Group.objects.create(name="test_group")
        self.role = role_create(display_name="Test role", child=[Role.objects.get(name="Create user", built_in=True)])
        self.policy = policy_create(
            name="Test Policy",
            role=self.role,
            group=[self.group],
            object=[],
            description="second description",
        )
        self.host_group = ConfigHostGroup.objects.create(
            name="config_host_group",
            object_type=ContentType.objects.get_for_model(self.provider),
            object_id=self.provider.pk,
        )

    def test_update_event_is_sent(self):
        request_events_dict = {
            "api_v2.cluster.views.send_object_update_event": (
                self.cluster_1,
                {"name": "new_name"},
            ),
            "api_v2.host.views.send_object_update_event": (
                self.host_1,
                {"name": "new-fqdn"},
            ),
            "api_v2.generic.config_host_group.views.send_object_update_event": (
                self.host_group,
                {"name": "new_name"},
            ),
            "rbac.services.user.send_object_update_event": (
                User.objects.first(),
                {"first_name": "new_name"},
            ),
            "rbac.services.group.send_object_update_event": (
                self.group,
                {"displayName": "new_name"},
            ),
            "rbac.services.role.send_object_update_event": (
                self.role,
                {"displayName": "new_name"},
            ),
            "rbac.services.policy.send_object_update_event": (
                self.policy,
                {"name": "new_name"},
            ),
        }

        manager = get_status_scenarios_manager()
        for event_func, [patched_obj, params] in request_events_dict.items():
            with self.subTest(event_func=event_func):
                manager.reset()
                response = self.client.v2[patched_obj].patch(data=params)
                self.assertEqual(response.status_code, 200)
                manager.expect_called_once("send_object_update_event")
                event = manager.send_object_update_event_calls[-1]

                obj_id, obj_type = event.obj_id, event.obj_type
                changes = event.changes

                self.assertEqual(obj_id, patched_obj.id)

                patched_obj_type = patched_obj.__class__.__name__.lower()

                if ADCMHostGroupType.CONFIG.value == obj_type:
                    patched_obj_type = "-".join(patched_obj.__class__.__name__.lower().split("host"))

                self.assertEqual(obj_type, patched_obj_type)
                assert_dict_contains_subset(camelize(params), changes)
