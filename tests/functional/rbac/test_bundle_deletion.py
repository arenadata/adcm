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

"""Test events concerning roles after bundle removal"""

from typing import Iterable, Set

import allure
import pytest
from adcm_client.objects import ADCMClient, Bundle, Role
from adcm_pytest_plugin.utils import get_data_dir
from tests.functional.rbac.action_role_utils import get_roles_of_type
from tests.functional.rbac.conftest import RoleType, extract_role_short_info
from tests.library.assertions import sets_are_equal

pytestmark = [pytest.mark.extra_rbac]

BUNDLE_V1 = 'cluster'
BUNDLE_V2 = 'cluster_v2'
ANOTHER_BUNDLE = 'another_cluster'

ACTION_BUSINESS_ROLE_INFIX = ' Action: '

ACTION_NAME = 'just_action'
ACTION_DISPLAY_NAME = 'Just Leave Me Here'


def test_single_bundle_deletion(sdk_client_fs):
    """Upload one bundle, then delete it"""
    check_no_action_business_roles(sdk_client_fs)
    bundle = upload_bundle(sdk_client_fs, BUNDLE_V1)
    bundle_display_name = bundle.cluster_prototype().display_name
    check_categories_are_presented(sdk_client_fs, bundle_display_name)
    check_action_business_roles_have_hidden_roles(sdk_client_fs, [bundle])
    bundle.delete()
    check_categories_not_presented(sdk_client_fs, bundle_display_name)
    check_no_action_business_roles(sdk_client_fs)


def test_delete_one_version_of_bundle(sdk_client_fs):
    """
    Upload two versions of one bundle, version of another bundle, delete one of bundles with two versions
    """
    check_no_action_business_roles(sdk_client_fs)
    with allure.step('Upload bundles and check roles'):
        bundles = []
        bundle_category_names = []
        for bundle_name in (BUNDLE_V1, BUNDLE_V2, ANOTHER_BUNDLE):
            bundle = upload_bundle(sdk_client_fs, bundle_name)
            bundles.append(bundle)
            bundle_category_names.append(bundle.cluster_prototype().display_name)
            check_categories_are_presented(sdk_client_fs, *bundle_category_names)
            check_action_business_roles_have_hidden_roles(sdk_client_fs, bundles)
    bundle_v1, bundle_v2, another_bundle = bundles  # pylint: disable=unbalanced-tuple-unpacking
    bundle_v1.delete()
    # v2 cat == v1 cat
    check_categories_are_presented(sdk_client_fs, *bundle_category_names)
    check_action_business_roles_have_hidden_roles(sdk_client_fs, [bundle_v2, another_bundle])


def test_instance_deletion_effect(sdk_client_fs):
    """Check that creation-deletion of instances (clusters) doesn't affect roles"""
    bundle = upload_bundle(sdk_client_fs, BUNDLE_V1)
    category = bundle.cluster_prototype().display_name
    check_categories_are_presented(sdk_client_fs, category)
    check_action_business_roles_have_hidden_roles(sdk_client_fs, [bundle])
    cluster = bundle.cluster_create(name='Test Cluster')
    check_categories_are_presented(sdk_client_fs, category)
    check_action_business_roles_have_hidden_roles(sdk_client_fs, [bundle])
    cluster.delete()
    check_categories_are_presented(sdk_client_fs, category)
    check_action_business_roles_have_hidden_roles(sdk_client_fs, [bundle])


def upload_bundle(client: ADCMClient, bundle_name: str) -> Bundle:
    """Upload bundle by directory name"""
    return client.upload_from_fs(get_data_dir(__file__, bundle_name))


@allure.step("Check there's no action business roles")
def check_no_action_business_roles(client: ADCMClient):
    """Check there's no action business roles"""
    assert all(
        ACTION_BUSINESS_ROLE_INFIX not in br.name for br in get_roles_of_type(RoleType.BUSINESS, client)
    ), f"There shouldn't be any business role that contains '{ACTION_BUSINESS_ROLE_INFIX}'"


@allure.step("Check that categories are presented in any of roles")
def check_categories_are_presented(client: ADCMClient, *categories: str):
    """Check categories are presented in all action roles"""
    roles = tuple(
        map(
            extract_role_short_info,
            filter(
                lambda x: ACTION_BUSINESS_ROLE_INFIX in x.name,
                get_roles_of_type(RoleType.BUSINESS, client),
            ),
        )
    )
    for category in categories:
        assert all(
            category in role.categories for role in roles
        ), f'Category {category} should be presented in all action business roles'


@allure.step("Check that categories aren't presented in any of roles")
def check_categories_not_presented(client: ADCMClient, *categories: str):
    """Check categories aren't presented in all business roles"""
    roles = tuple(map(extract_role_short_info, get_roles_of_type(RoleType.BUSINESS, client)))
    for category in categories:
        assert all(
            category not in role.categories for role in roles
        ), f'Category {category} should not be presented in any business roles'


@allure.step("Check action business roles have correct hidden children")
def check_action_business_roles_have_hidden_roles(client: ADCMClient, bundles: Iterable[Bundle]):
    """
    Check that action business roles for cluster, service and component
    have hidden action roles of given bundles
    """
    for object_type, extraction_function in zip(
        ('Cluster', 'Service', 'Component'),
        (
            _generate_cluster_hidden_action_role_names,
            _generate_service_hidden_action_role_names,
            _generate_component_hidden_action_role_names,
        ),
    ):
        with allure.step(f'Check {object_type} action role has correct children'):
            role = client.role(name=f'{object_type} Action: {ACTION_DISPLAY_NAME}')
            actual_child_names = _get_children_names(role)
            expected_child_names = extraction_function(bundles)
            sets_are_equal(
                actual_child_names,
                expected_child_names,
                "Children of a business action role aren't correct",
            )


def _get_children_names(role: Role) -> Set[str]:
    """Get names of children of a role"""
    return {r.name for r in role.child_list()}


def _generate_cluster_hidden_action_role_names(bundles: Iterable[Bundle]) -> Set[str]:
    return {
        f'{bundle.name}_{bundle.version}_{bundle.edition}_cluster_' f'{bundle.cluster_prototype().name}_{ACTION_NAME}'
        for bundle in bundles
    }


def _generate_service_hidden_action_role_names(bundles: Iterable[Bundle]) -> Set[str]:
    return {
        # it's always test_service
        f'{bundle.name}_{bundle.version}_{bundle.edition}_service_test_service_{ACTION_NAME}'
        for bundle in bundles
    }


def _generate_component_hidden_action_role_names(bundles: Iterable[Bundle]) -> Set[str]:
    return {
        # it's always test_component
        f'{bundle.name}_{bundle.version}_{bundle.edition}_service_test_service_component_test_component_{ACTION_NAME}'
        for bundle in bundles
    }
