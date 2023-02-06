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

"""Test categories (filters for roles)"""

import os
from typing import Dict, Generator, Set
from urllib import parse

import allure
import requests
from adcm_client.objects import ADCMClient
from tests.functional.rbac.conftest import (
    DATA_DIR,
    RoleShortInfo,
    extract_role_short_info,
)
from tests.library.assertions import is_empty, is_superset_of

CATEGORIES_SUFFIX = "api/v1/rbac/role/category"


def test_category_lifecycle(sdk_client_fs):
    """Test categories' behavior during bundles upload/removal"""
    expected_categories = set()
    filepaths = {
        "clusters": {
            "first": os.path.join(DATA_DIR, "categories", "cluster"),
            "second": os.path.join(DATA_DIR, "categories", "second_cluster"),
        },
        "providers": {"first": os.path.join(DATA_DIR, "categories", "provider")},
    }

    check_categories_before_bundle_upload(sdk_client_fs, expected_categories)
    check_categories_during_cluster_bundle_uploads(sdk_client_fs, filepaths["clusters"], expected_categories)
    check_categories_after_provider_bundle_upload(sdk_client_fs, filepaths["providers"]["first"], expected_categories)


@allure.step("Check categories before upload of any bundle")
def check_categories_before_bundle_upload(client: ADCMClient, expected_categories: Set[str]):
    """Check that there's only one default category"""
    _check_category_list(client, expected_categories)
    roles_with_categories = tuple(filter(lambda role: len(role.categories) != 0, _get_all_roles_info(client)))
    is_empty(roles_with_categories, "There should be no role with category.")


@allure.step("Check categories after cluster bundle uploads")
def check_categories_during_cluster_bundle_uploads(
    client: ADCMClient, cluster_bundle_paths: Dict[str, str], expected_categories: Set[str]
):
    """Check categories between and after two cluster bundles upload"""
    first_fp, second_fp = cluster_bundle_paths.values()

    with allure.step("Upload first cluster and check that category is now presented"):
        first_bundle = client.upload_from_fs(first_fp)
        first_bundle_category = first_bundle.cluster_prototype().display_name
        expected_categories.add(first_bundle_category)
        _check_category_list(client, expected_categories)
        assert any(
            first_bundle_category in role.categories for role in _get_all_roles_info(client)
        ), f"None of roles has new bundle's category '{first_bundle_category}'"

    with allure.step(
        "Upload second cluster and check that new category has appeared and action roles have two categories"
    ):
        second_bundle = client.upload_from_fs(second_fp)
        second_bundle_category = second_bundle.cluster_prototype().display_name
        expected_categories.add(second_bundle_category)
        _check_category_list(client, expected_categories)
        # since actions are identical, so all "{obj_type} Action: {action_name}" should now have two categories
        expected_actions_categories = {first_bundle_category, second_bundle_category}
        for action_role in filter(lambda role: "Action" in role.name, _get_all_roles_info(client)):
            is_superset_of(
                set(action_role.categories),
                expected_actions_categories,
                f"Role {action_role.name} should have two categories: {expected_actions_categories}",
            )

    with allure.step("Remove one of bundles and check categories"):
        second_bundle.delete()
        expected_categories.remove(second_bundle_category)
        _check_category_list(client, expected_categories)
        assert all(
            second_bundle_category not in role.categories for role in _get_all_roles_info(client)
        ), f'None of roles may have category "{second_bundle_category}"'


@allure.step("Check categories after provider bundle upload")
def check_categories_after_provider_bundle_upload(client: ADCMClient, bundle_path: str, expected_categories: Set[str]):
    """Check that new categories wasn't created after provider bundle upload"""
    bundle = client.upload_from_fs(bundle_path)
    category_name = bundle.provider_prototype().display_name
    _check_category_list(client, expected_categories)
    assert all(
        category_name not in role.categories for role in _get_all_roles_info(client)
    ), f'None of roles may have category "{category_name}"'


@allure.step("Check list of categories")
def _check_category_list(client: ADCMClient, categories: Set[str]):
    """Check if category list is the same as expected"""
    categories_request = requests.get(
        parse.urljoin(client.url, CATEGORIES_SUFFIX),
        headers={"Authorization": f"Token {client.api_token()}"},
    )
    categories_request.raise_for_status()
    category_list = categories_request.json()
    assert (actual := len(category_list)) == (
        expected := len(categories)
    ), f"Amount of categories should be exactly {expected}, not {actual}"
    # is superset is ok, because length is the same, but if one day we have "is_equal_to", change it
    is_superset_of(
        set(category_list),
        categories,
        "Categories list is incorrect. See attachment for more details.",
    )


def _get_all_roles_info(client: ADCMClient) -> Generator[RoleShortInfo, None, None]:
    """Get all roles (500) info"""
    for role in client.role_list(paging={"limit": 500}):
        yield extract_role_short_info(role)
