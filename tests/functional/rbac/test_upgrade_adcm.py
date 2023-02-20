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

"""Tests ADCM upgrade from last non-RBAC version to RBAC one"""

import os

import allure
import pytest
from adcm_client.objects import ADCMClient, Bundle
from adcm_pytest_plugin.utils import get_data_dir, random_string

from tests.functional.rbac.action_role_utils import (
    check_cluster_actions_roles_are_created_correctly,
    check_provider_based_object_action_roles_are_created_correctly,
    check_roles_does_not_have_category,
    check_service_and_components_roles_are_created_correctly,
    get_bundle_prefix_for_role_name,
    get_roles_of_type,
)
from tests.functional.rbac.conftest import DATA_DIR, RoleType, extract_role_short_info
from tests.library.utils import previous_adcm_version_tag
from tests.upgrade_utils import upgrade_adcm_version

LAST_NON_RBAC_VER = "2021.11.22.15"
SERVICE_NAMES = "test_service", "new_service"
NEW_USER_CREDS = "bestname", "nevergonnabreakmedown"


@pytest.mark.extra_rbac()
@pytest.mark.parametrize("adcm_is_upgradable", [True], indirect=True)
@pytest.mark.parametrize(
    "image",
    [(previous_adcm_version_tag()[0], LAST_NON_RBAC_VER)],  # [0] to get repo
    ids=repr,
    indirect=True,
)
def test_rbac_init_on_upgrade(
    launcher,
    sdk_client_fs: ADCMClient,
    adcm_api_credentials: dict,
    adcm_image_tags: tuple[str, str],
):
    """
    Test that roles are created on bundles uploaded before an upgrade
    """
    bundles = upload_bundles(sdk_client_fs)
    upgrade_adcm_version(launcher, sdk_client_fs, adcm_api_credentials, adcm_image_tags)
    check_roles_are_created(sdk_client_fs, bundles)


@allure.step("Upload bundles")
def upload_bundles(client: ADCMClient) -> tuple[Bundle, Bundle, Bundle, Bundle]:
    """Upload sample bundles"""
    cluster_bundles_dir = get_data_dir(__file__)
    return tuple(
        client.upload_from_fs(os.path.join(directory, bundle))
        for directory, bundle in (
            (cluster_bundles_dir, "cluster"),
            (cluster_bundles_dir, "second_cluster"),
            (DATA_DIR, "provider"),
            (DATA_DIR, "second_provider"),
        )
    )


@allure.step("Check that roles are created correctly after ADCM upgrade")
def check_roles_are_created(client, bundles: tuple[Bundle, Bundle, Bundle, Bundle]):
    """Check that roles for pre-uploaded bundles were created correctly"""
    hidden_role_names = {role.name for role in get_roles_of_type(RoleType.HIDDEN, client)}

    with allure.step("Check cluster roles were created correctly"):
        first_bundle, second_bundle, *_ = bundles
        for cluster_bundle in (first_bundle, second_bundle):
            hidden_role_prefix = get_bundle_prefix_for_role_name(cluster_bundle)
            cluster = cluster_bundle.cluster_create(name=f"Test cluster {random_string(4)}")
            check_cluster_actions_roles_are_created_correctly(client, cluster, hidden_role_names, hidden_role_prefix)
            for service_name in SERVICE_NAMES:
                check_service_and_components_roles_are_created_correctly(
                    client,
                    cluster.service_add(name=service_name),
                    hidden_role_names,
                    hidden_role_prefix,
                )

    with allure.step("Check provider roles were created correctly"):
        *_, first_bundle, second_bundle = bundles
        for provider_bundle in (first_bundle, second_bundle):
            hidden_role_prefix = get_bundle_prefix_for_role_name(provider_bundle)
            check_provider_based_object_action_roles_are_created_correctly(
                provider_bundle.provider_prototype(),
                client,
                hidden_role_names,
                hidden_role_prefix,
            )

            provider = provider_bundle.provider_create(f"Test Provider {random_string(4)}")
            host = provider.host_create(fqdn=f"test-host-{random_string(4)}")
            check_provider_based_object_action_roles_are_created_correctly(
                host.prototype(),
                client,
                hidden_role_names,
                hidden_role_prefix,
            )

            check_roles_does_not_have_category(
                provider_bundle.provider_prototype().display_name,
                map(extract_role_short_info, get_roles_of_type(RoleType.BUSINESS, client)),
            )
