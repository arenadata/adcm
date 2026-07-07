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

from collections.abc import Callable
from enum import Enum, auto
from urllib.parse import urlsplit

from cm.models import Bundle
from core.bundle import ContractVersion, InstalledBundleVersion
from core.scenarios.adcm import DefaultURL
from dishka import Container, Scope
from django.db import connection
from integrations.consul import ClientSettings
from packaging.version import Version
import core.bundle

CONTRACT_VERSION_FIELD_NAME = "contract_version"

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
OUTDATED_VERSION_ERROR = (
    "UPGRADE BLOCKED - COMPATIBILITY ISSUES:\n"
    "✗ Requires contract_version functionality.\n"
    "Minimum required version to upgrade from is ADCM 2.10.1\n"
    "Please upgrade to ADCM 2.10.1 first before upgrading to the current version."
)
SUCCESS_TEMPLATE = "✓ All installed bundles have supported contract_version.\n"


class CheckStatuses(str, Enum):
    NO_TABLE = auto()
    NO_FIELD = auto()
    SUCCESS = auto()


def check_contract_version_field_exists() -> CheckStatuses:
    table_name = Bundle._meta.db_table

    with connection.cursor() as cursor:
        if table_name not in connection.introspection.table_names(cursor):
            return CheckStatuses.NO_TABLE

        columns = connection.introspection.get_table_description(cursor, table_name)

    if CONTRACT_VERSION_FIELD_NAME not in {col.name for col in columns}:
        return CheckStatuses.NO_FIELD

    return CheckStatuses.SUCCESS


def validate_default_adcm_url(*, container: Container, failure_exc: type[BaseException]) -> None:
    """Validate ``DEFAULT_ADCM_URL`` url. Also, It is mandatory once Consul registration is enabled."""
    default_adcm_url = container.get(DefaultURL | None)
    consul_settings = container.get(ClientSettings | None)

    if default_adcm_url is None and consul_settings:
        message = "DEFAULT_ADCM_URL is mandatory when ADCM is configured to run with Consul (CONSUL_URL is set)"
        raise failure_exc(message)

    if default_adcm_url:
        parts = urlsplit(default_adcm_url)
        if not parts.scheme or not parts.hostname or not parts.port:
            message = f"DEFAULT_ADCM_URL is not a valid URL: {default_adcm_url!r}"
            raise failure_exc(message)

    return


def check_adcm_start_is_allowed(
    *,
    container: Container,
    failure_exc: type[BaseException],
    report_message: Callable,
    report_warning: Callable,
) -> None:
    result = check_contract_version_field_exists()
    if result == CheckStatuses.NO_FIELD:
        message = OUTDATED_VERSION_ERROR
        raise failure_exc(message)

    if result == CheckStatuses.NO_TABLE:
        return

    with container(scope=Scope.REQUEST) as cont:
        check_bundle = cont.get(core.bundle.BundleService).find_contract_compatibility_violations()

    if check_bundle.unsupported_version_bundles:
        message = _build_details_message(
            COMPATIBILITY_ERROR_TEMPLATE, check_bundle.unsupported_version_bundles, check_bundle.supported_versions
        )
        raise failure_exc(message)

    if check_bundle.deprecated_version_bundles:
        message = _build_details_message(
            DEPRECATION_WARNING_TEMPLATE, check_bundle.deprecated_version_bundles, check_bundle.deprecated_versions
        )
        report_warning(message)
    else:
        message = SUCCESS_TEMPLATE
        report_message(message)


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
