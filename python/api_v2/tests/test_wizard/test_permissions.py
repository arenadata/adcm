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


from contextlib import contextmanager
from uuid import uuid4

from cm.legacy.services.action_process.schema_validation import ProcessOperationType
from rest_framework.status import HTTP_404_NOT_FOUND
from tests.deprecated import BusinessLogicMixin
from tests.suites import ADCMDjangoAPISuite

from api_v2.tests.base import APIV2Mixin
from api_v2.tests.test_wizard.helpers import WizardProcessHelpers


class TestWizardActionProcessPermissions(ADCMDjangoAPISuite, APIV2Mixin, WizardProcessHelpers, BusinessLogicMixin):
    def setUp(self) -> None:
        super().setUp()

        cluster_bundle = self.test_bundles_dir / "wizard_action"
        self.bundle = self.create_bundle(src=cluster_bundle)

        suffix = uuid4().hex[:8]
        self.cluster_1 = self.create_cluster(
            bundle=self.bundle,
            name=f"cluster_1_{suffix}",
            description=f"cluster_1_{suffix}",
        )

        self.action = self.get_object_action_with_process(self.cluster_1)
        self.action_id = self.action.pk

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

        self.process = self.start_process(self.cluster_1, self.action_id)
        self.step_id = self.process.current_step_id  # pyright: ignore[reportAttributeAccessIssue]

    def case_expect_not_found_on_get_step(self) -> None:
        with self.subTest("get-step-404"):
            self.get_step_r(
                target=self.cluster_1,
                action=self.action,
                process_id=self.process.pk,
                step_id=self.step_id,
                expected_status=HTTP_404_NOT_FOUND,
            )

    def case_expect_not_found_on_submit_step(self) -> None:
        data = {
            "method": ProcessOperationType.SUBMIT,
            "params": {"step_id": self.step_id, "process_sync_key": self.process.sync_key},
        }
        with self.subTest("submit-step-404"):
            self.submit_step_r(
                target=self.cluster_1,
                action=self.action,
                process_id=self.process.pk,
                data=data,
                expected_status=HTTP_404_NOT_FOUND,
            )

    def case_expect_not_found_on_get_process(self) -> None:
        with self.subTest("get-process-404"):
            self.get_process_r(
                target=self.cluster_1,
                action=self.action,
                process_id=self.process.pk,
                expected_status=HTTP_404_NOT_FOUND,
            )

    def case_expect_not_found_on_start_process(self) -> None:
        with self.subTest("submit-process-404"):
            self.start_process_r(self.cluster_1, self.action_id, expected_status=HTTP_404_NOT_FOUND)

    @contextmanager
    def no_view_permission_subtest(self):
        with self.subTest("no-view-permissions"):
            yield

    @contextmanager
    def only_view_permission_subtest(self):
        with self.subTest("only-view-permissions"):
            with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="View cluster configurations"):
                yield

    def test_cases(self):
        self.client.login(**self.test_user_credentials)

        permission_cases = (self.no_view_permission_subtest, self.only_view_permission_subtest)

        operation_cases = (
            self.case_expect_not_found_on_start_process,
            self.case_expect_not_found_on_get_process,
            self.case_expect_not_found_on_get_step,
            self.case_expect_not_found_on_submit_step,
        )

        for permission_context in permission_cases:
            with permission_context():
                for test_case in operation_cases:
                    test_case()
