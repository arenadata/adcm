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

from unittest import TestCase

from parameterized import parameterized

from core.action import wizard


class TestWizardActionOperations(TestCase):
    case_1 = (
        "Broken step is current, completed step is last completed.",
        (
            (wizard.StepState.COMPLETED, 1),
            (wizard.StepState.BROKEN, 2),
        ),
        (2, 1),
    )

    case_2 = (
        "Created step is current, skipped step is last completed.",
        (
            (wizard.StepState.SKIPPED, 2),
            (wizard.StepState.CREATED, 3),
        ),
        (3, 2),
    )

    case_3 = (
        "Reverse check: broken step is current, skipped step is last completed",
        (
            (wizard.StepState.BROKEN, 3),
            (wizard.StepState.SKIPPED, 2),
            (wizard.StepState.COMPLETED, 1),
        ),
        (3, 2),
    )

    case_4 = (
        "Only the current step is defined (broken)",
        ((wizard.StepState.BROKEN, 1),),
        (1, None),
    )
    case_5 = (
        "Only the current step is defined (created)",
        ((wizard.StepState.CREATED, 1),),
        (1, None),
    )
    case_6 = (
        "Only the last completed step is defined (skipped)",
        ((wizard.StepState.SKIPPED, 1),),
        (None, 1),
    )
    case_7 = (
        "Only the last completed step is defined (completed)",
        ((wizard.StepState.COMPLETED, 1),),
        (None, 1),
    )
    case_8 = (
        "Only the current step (broken) out of two possible ones is determined",
        (
            (wizard.StepState.BROKEN, 1),
            (wizard.StepState.CREATED, 2),
        ),
        (1, None),
    )
    case_9 = (
        "Check base algorithm",
        (
            (wizard.StepState.COMPLETED, 1),
            (wizard.StepState.COMPLETED, 2),
            (wizard.StepState.CREATED, 3),
            (wizard.StepState.CREATED, 4),
        ),
        (3, 2),
    )
    case_10 = ("Check empty collection", (), (None, None))

    @parameterized.expand(input=[case_1, case_2, case_3, case_4, case_5, case_6, case_7, case_8, case_9, case_10])
    def test_get_current_and_last_completed_step_ids(self, _, input_steps, expected_steps):
        res = wizard.operations.get_current_and_last_completed_step_ids(input_steps)
        self.assertEqual(res, expected_steps)
