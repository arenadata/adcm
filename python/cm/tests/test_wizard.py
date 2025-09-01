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

from typing import TypeAlias
from uuid import uuid4

from adcm.tests.base import BaseTestCase
from core.types import ADCMCoreType

from cm.models import Action, Bundle, ObjectType, Process, ProcessStep, Prototype
from cm.services.wizard.operations import find_current_and_last_completed_steps
from cm.services.wizard.types import ProcessStepState

StepName: TypeAlias = str


class TestWizardLogic(BaseTestCase):
    def _create_dummy_process_with_steps(self, num_steps: int) -> Process:
        bundle = Bundle.objects.create(name="dummy_bundle", version="1", hash="dummy")
        prototype = Prototype.objects.create(
            bundle=bundle, name="dummy_cluster_prototype", type=ObjectType.CLUSTER, version="`"
        )
        action = Action.objects.create(prototype=prototype)

        flow_spec = []
        for i in range(num_steps):
            stage_name = f"stage_for_step_{i}"
            step_name = f"step_{i}"

            flow_spec.append(
                {
                    "name": stage_name,
                    "display_name": stage_name.capitalize(),
                    "steps": [
                        {
                            "name": step_name,
                            "display_name": step_name.capitalize(),
                            "config_template": {"file": {"path": "some/path.j2"}, "engine": {"type": "jinja2"}},
                        }
                    ],
                }
            )
        process = Process.objects.create(
            action=action, object_id=0, object_type=ADCMCoreType.CLUSTER, flow_spec=flow_spec, sync_key=uuid4()
        )

        steps_data = []
        for i in range(num_steps):
            name = f"step_{i}"
            steps_data.append(ProcessStep(process_id=process.id, name=name, display_name=name.capitalize()))

        if steps_data:
            ProcessStep.objects.bulk_create(steps_data)

        self.assertEqual(
            ProcessStep.objects.filter(
                process_id=process.id, name__startswith="step_", display_name__startswith="Step_"
            ).count(),
            num_steps,
        )

        return process

    def _set_process_state_by_name(self, process_id: int, map_: dict[tuple[StepName, ...], ProcessStepState]):
        """Sets 'created' state for unspecified steps"""

        ProcessStep.objects.filter(process_id=process_id).update(state=ProcessStepState.CREATED)
        for names, state in map_.items():
            ProcessStep.objects.filter(process_id=process_id, name__in=names).update(state=state)

    def test_retrieve_current_last_completed(self):
        process = self._create_dummy_process_with_steps(num_steps=5)
        self.assertSetEqual(
            set(ProcessStep.objects.filter(process_id=process.id).values_list("state", flat=True)),
            {ProcessStepState.CREATED},
        )

        steps_name_id_map = {
            name: id_ for id_, name in ProcessStep.objects.filter(process_id=process.id).values_list("id", "name")
        }

        with self.subTest("Just created Steps"):
            current, last_completed = find_current_and_last_completed_steps(
                steps=ProcessStep.objects.filter(process_id=process.id)
            )
            self.assertEqual(current, steps_name_id_map["step_0"])
            self.assertIsNone(last_completed)

        with self.subTest("0, 1 steps completed"):
            self._set_process_state_by_name(
                process_id=process.id, map_={("step_0", "step_1"): ProcessStepState.COMPLETED}
            )

            current, last_completed = find_current_and_last_completed_steps(
                steps=ProcessStep.objects.filter(process_id=process.id)
            )
            self.assertEqual(current, steps_name_id_map["step_2"])
            self.assertEqual(last_completed, steps_name_id_map["step_1"])

        with self.subTest("0, 1 steps completed, 2 running"):
            self._set_process_state_by_name(
                process_id=process.id,
                map_={("step_0", "step_1"): ProcessStepState.COMPLETED, ("step_2",): ProcessStepState.RUNNING},
            )

            current, last_completed = find_current_and_last_completed_steps(
                steps=ProcessStep.objects.filter(process_id=process.id)
            )
            self.assertEqual(current, steps_name_id_map["step_2"])
            self.assertEqual(last_completed, steps_name_id_map["step_1"])

        with self.subTest("all 5 steps completed"):
            self._set_process_state_by_name(
                process_id=process.id,
                map_={("step_0", "step_1", "step_2", "step_3", "step_4"): ProcessStepState.COMPLETED},
            )

            current, last_completed = find_current_and_last_completed_steps(
                steps=ProcessStep.objects.filter(process_id=process.id)
            )
            self.assertIsNone(current)
            self.assertEqual(last_completed, steps_name_id_map["step_4"])
