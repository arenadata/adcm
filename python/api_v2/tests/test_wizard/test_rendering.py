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


from cm.models import Action
from tests.suites import ADCMDjangoAPISuite

from api_v2.tests.base import APIV2Mixin


class TestImplementDescription(ADCMDjangoAPISuite, APIV2Mixin):
    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        cls.cluster_bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "wizard_rendering_description")
        cls.step_descr_mapping = {
            "action_step_config": "Config step description",
            "action_step_operation": "Operational step description",
            "action_step_mapping": "Mapping step description",
            "action_no_desc": "",
        }
        cls.stage_descr_mapping = {
            "action_step_config": "Stage description",
            "action_no_desc": "",
        }

    def test_rendering_step_description(self):
        for action_name, description in self.step_descr_mapping.items():
            with self.subTest(f"Check the step description field for '{action_name}' case"):
                cluster = self.create_cluster(bundle=self.cluster_bundle, name=f"test_cluster_with_{action_name}")
                action = Action.objects.get(name=action_name, prototype=cluster.prototype)
                process_id = self.start_process_r(cluster, action.pk).json()["id"]
                response_data = self.get_process_r(cluster, action.pk, process_id).json()
                first_step_data = response_data["stages"][0]["steps"][0]
                step_type, step_id = first_step_data["type"], first_step_data["id"]

                with self.subTest(f"Check the step's description field from the process '{process_id}'"):
                    self.assertEqual(first_step_data["description"], description)

                with self.subTest(f"Check the description from spec of the '{step_type}' step"):
                    response_data = self.get_step_r(cluster, action.pk, process_id, step_id).json()
                    self.assertEqual(response_data["description"], description)

    def test_rendering_stage_description(self):
        for action_name, description in self.stage_descr_mapping.items():
            with self.subTest(f"Check the stage description field for '{action_name}' case"):
                cluster = self.create_cluster(bundle=self.cluster_bundle, name=f"test_cluster_with_{action_name}")
                action = Action.objects.get(name=action_name, prototype=cluster.prototype)
                process_id = self.start_process_r(cluster, action.pk).json()["id"]
                stage_data = self.get_process_r(cluster, action.pk, process_id).json()["stages"][0]

                with self.subTest(f"Check the step's description field from the process '{process_id}'"):
                    self.assertEqual(stage_data["description"], description)
