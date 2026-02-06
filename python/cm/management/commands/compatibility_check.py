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

from adcm.dependencies import prepare_container
from core.bundle import BundleCompatibilityReport, ContractVersion, InstalledBundleVersion
from dishka import Scope
from django.core.management import BaseCommand, CommandError
from packaging.version import Version
from use_cases.bundle import CompatibilityCheck

COMPATIBILITY_ERROR_TEMPLATE = (
    "UPGRADE BLOCKED - COMPATIBILITY ISSUES:\n"
    "✗ Found bundles with incompatible contract_version:\n{bundles_info}\n"
    "Upgrade products to bundles with supported contract versions: {versions}\n"
)
DEPRECATION_WARNING_TEMPLATE = (
    "DEPRECATION WARNING:\n{bundles_info}\n"
    "These versions are deprecated now and their support will be dropped"
    " in the future: {versions}"
)
SUCCESS_TEMPLATE = "✓ All installed bundles have supported contract_version"


class Command(BaseCommand):
    help = """
    Verify if a specific migration has been applied, ensuring installed bundles
    compatibility before allowing upgrade to current version.
    """

    def handle(self, *_, **_kw):
        report = self._get_compatibility_report()

        if report.unsupported_version_bundles:
            message = self._build_details_message(
                COMPATIBILITY_ERROR_TEMPLATE, report.unsupported_version_bundles, report.supported_versions
            )
            raise CommandError(message)

        if report.deprecated_version_bundles:
            message = self._build_details_message(
                DEPRECATION_WARNING_TEMPLATE, report.deprecated_version_bundles, report.deprecated_versions
            )
            warning = self.style.WARNING(message)
            self.stderr.write(warning)
        else:
            success_message = self.style.SUCCESS(SUCCESS_TEMPLATE)
            self.stdout.write(success_message)

    @staticmethod
    def _get_compatibility_report() -> BundleCompatibilityReport:
        container = prepare_container()
        with container(scope=Scope.REQUEST) as c:
            return c.get(CompatibilityCheck).do()

    @staticmethod
    def _build_details_message(
        message_template: str, bundle_info: set[InstalledBundleVersion], versions: set[ContractVersion]
    ) -> str:
        sorted_info = sorted(bundle_info, key=lambda bundle: (bundle.name, bundle.contract_version))
        versions_details_repr = "\n".join(
            f"{i}: {bundle.name} {bundle.edition} {bundle.version} (contract: {bundle.contract_version})"
            for i, bundle in enumerate(sorted_info, start=1)
        )

        sorted_versions = sorted(versions, key=Version)
        versions_repr = ", ".join(sorted_versions)

        return message_template.format(bundles_info=versions_details_repr, versions=versions_repr)
