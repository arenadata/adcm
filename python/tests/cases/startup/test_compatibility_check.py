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

from unittest.mock import Mock, patch

from application.startup.checks import (
    OUTDATED_VERSION_ERROR,
    SUPPORTED_CONTRACT_VERSION_SUCCESS_TEMPLATE,
    check_adcm_start_is_allowed,
)
from cm.models import Bundle, ObjectType, Prototype
from core.bundle import AvailableContractVersions, ContractVersionStatus
from django.core.management.base import CommandError
from django.db import connection, models

from tests.base import BaseTestCase


class FakeBundle(models.Model):
    class Meta:
        app_label = "tests"
        db_table = "fake_bundle"


class TestADCMStartIsAllowed(BaseTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.supported_cv = "2.1"
        cls.unsupported_cv = "3"

        (
            cls.bundle_cl1,
            cls.bundle_cl2,
            cls.bundle_pr1,
            cls.bundle_pr2,
        ) = cls.create_bundle_and_prototype_records(
            ("supported_bundle_cl1", cls.supported_cv, ObjectType.CLUSTER),
            ("unsupported_bundle_cl2", cls.unsupported_cv, ObjectType.CLUSTER),
            ("supported_bundle_pr1", cls.supported_cv, ObjectType.PROVIDER),
            ("unsupported_bundle_pr2", cls.unsupported_cv, ObjectType.PROVIDER),
        )

        cls.supported_cluster = cls.uc.add_cluster(bundle=cls.bundle_cl1, name="supported_cluster")
        cls.supported_provider = cls.uc.add_provider(bundle=cls.bundle_pr1, name="supported_provider")

        cls.available_contract_versions = cls.uc.container.get(AvailableContractVersions)

    @staticmethod
    def create_fake_bundle_table() -> None:
        with connection.schema_editor() as editor:
            editor.create_model(FakeBundle)

    def update_bundles_contract_version_to_supported(self) -> None:
        Bundle.objects.update(contract_version=self.supported_cv)

    @staticmethod
    def get_supported_version_tags(available_cv: AvailableContractVersions) -> list[str]:
        return [
            version_info.tag for version_info in available_cv if version_info.status == ContractVersionStatus.SUPPORTED
        ]

    @staticmethod
    def create_bundle_and_prototype_records(*bundle_specs: tuple[str, str, ObjectType]) -> tuple[Bundle, ...]:
        bundles = tuple(
            Bundle.objects.bulk_create(
                objs=[
                    Bundle(
                        name=name,
                        version="1.0",
                        hash="hash",
                        contract_version=contract_version,
                    )
                    for name, contract_version, _ in bundle_specs
                ]
            )
        )

        bundle_records = zip(bundles, bundle_specs, strict=True)
        Prototype.objects.bulk_create(
            objs=[
                Prototype(
                    bundle=bundle,
                    type=obj_type,
                    name=bundle.name,
                    version=bundle.version,
                )
                for bundle, (_, _, obj_type) in bundle_records
            ]
        )

        return bundles

    @patch("application.startup.checks.Bundle", FakeBundle)
    def test_adcm_version_without_contract_version_field(self) -> None:
        with self.subTest("Bundle table doesn't exist"):
            check_adcm_start_is_allowed(
                container=self.uc.container,
                failure_exc=CommandError,
                report_message=Mock(),
                report_warning=Mock(),
            )

        with self.subTest("Bundle table has no contract_version field"):
            self.create_fake_bundle_table()

            with self.assertRaises(CommandError) as error:
                check_adcm_start_is_allowed(
                    container=self.uc.container,
                    failure_exc=CommandError,
                    report_message=Mock(),
                    report_warning=Mock(),
                )

        err_message = str(error.exception)
        self.assertEqual(err_message, OUTDATED_VERSION_ERROR)

    def test_error_due_to_unsupported_created_objects(self) -> None:
        self.uc.set_unsupported_contract_version(
            prototype=self.supported_cluster.prototype, contract_version=self.unsupported_cv
        )
        self.uc.set_unsupported_contract_version(
            prototype=self.supported_provider.prototype, contract_version=self.unsupported_cv
        )

        sv_tags = self.get_supported_version_tags(self.available_contract_versions)
        expected_unsupported_objects_error = (
            "UPGRADE BLOCKED - COMPATIBILITY ISSUES:\n"
            "✗ Found Clusters or Hostproviders which are use unsupported bundles with incompatible "
            "contract_version: "
            f"1: {self.bundle_cl1.name} community 1.0 (contract: {self.unsupported_cv})\n"
            f"2: {self.bundle_pr1.name} community 1.0 (contract: {self.unsupported_cv})\n"
            f"Upgrade products to bundles with supported contract versions: {", ".join(sv_tags)}\n"
        )

        with self.assertRaises(CommandError) as error:
            check_adcm_start_is_allowed(
                container=self.uc.container,
                failure_exc=CommandError,
                report_message=Mock(),
                report_warning=Mock(),
            )

        err_message = str(error.exception)
        self.assertEqual(err_message, expected_unsupported_objects_error)

    def test_warning_about_unsupported_bundles(self) -> None:
        report_warning = Mock()
        expected_warting_about_unsuppotred_versions = (
            "Δ Found unsupported bundles with incompatible contract_version:\n"
            f"1: {self.bundle_cl2.name} community 1.0 (contract: {self.unsupported_cv})\n"
            f"2: {self.bundle_pr2.name} community 1.0 (contract: {self.unsupported_cv})\n"
        )

        check_adcm_start_is_allowed(
            container=self.uc.container,
            failure_exc=CommandError,
            report_message=Mock(),
            report_warning=report_warning,
        )

        report_warning.assert_called_once()

        unsupported_message = report_warning.call_args.args[0]
        self.assertEqual(unsupported_message, expected_warting_about_unsuppotred_versions)

    def test_success_compatibility(self) -> None:
        self.update_bundles_contract_version_to_supported()
        report_message = Mock()
        report_warning = Mock()

        check_adcm_start_is_allowed(
            container=self.uc.container,
            failure_exc=CommandError,
            report_message=report_message,
            report_warning=report_warning,
        )

        report_warning.assert_not_called()

        expected_message = SUPPORTED_CONTRACT_VERSION_SUCCESS_TEMPLATE
        report_message.assert_called_once_with(expected_message)
