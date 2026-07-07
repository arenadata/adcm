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

from unittest_parametrize import ParametrizedTestCase, param, parametrize

from core.action import wizard


class TestWizardActionOperations(ParametrizedTestCase, TestCase):
    case_1 = param(
        (
            (wizard.StepState.COMPLETED, 1),
            (wizard.StepState.BROKEN, 2),
        ),
        (2, 1),
        id="broken_step_is_current_completed_step_is_last_completed",
    )

    case_2 = param(
        (
            (wizard.StepState.SKIPPED, 2),
            (wizard.StepState.CREATED, 3),
        ),
        (3, 2),
        id="created_step_is_current_skipped_step_is_last_completed",
    )

    case_3 = param(
        (
            (wizard.StepState.BROKEN, 3),
            (wizard.StepState.SKIPPED, 2),
            (wizard.StepState.COMPLETED, 1),
        ),
        (3, 2),
        id="reverse_check_broken_step_is_current_skipped_step_is_last_completed",
    )

    case_4 = param(
        ((wizard.StepState.BROKEN, 1),),
        (1, None),
        id="only_the_current_step_is_defined_broken_",
    )
    case_5 = param(
        ((wizard.StepState.CREATED, 1),),
        (1, None),
        id="only_the_current_step_is_defined_created_",
    )
    case_6 = param(
        ((wizard.StepState.SKIPPED, 1),),
        (None, 1),
        id="only_the_last_completed_step_is_defined_skipped",
    )
    case_7 = param(
        ((wizard.StepState.COMPLETED, 1),),
        (None, 1),
        id="only_the_last_completed_step_is_defined_completed",
    )
    case_8 = param(
        (
            (wizard.StepState.BROKEN, 1),
            (wizard.StepState.CREATED, 2),
        ),
        (1, None),
        id="only_the_current_step_broken_out_of_two_possible_ones_is_determined",
    )
    case_9 = param(
        (
            (wizard.StepState.COMPLETED, 1),
            (wizard.StepState.COMPLETED, 2),
            (wizard.StepState.CREATED, 3),
            (wizard.StepState.CREATED, 4),
        ),
        (3, 2),
        id="check_base_algorithm",
    )
    case_10 = param((), (None, None), id="check_empt_collection")

    @parametrize(
        ("input_steps", "expected_steps"),
        [case_1, case_2, case_3, case_4, case_5, case_6, case_7, case_8, case_9, case_10],
    )
    def test_get_current_and_last_completed_step_ids(self, input_steps, expected_steps):
        res = wizard.operations.get_current_and_last_completed_step_ids(input_steps)
        self.assertEqual(res, expected_steps)
