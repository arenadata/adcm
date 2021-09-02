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


import allure
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import parametrize_by_data_subdirs

from tests.ui_tests.app.configuration import Configuration
from .utils import prepare_cluster_and_get_config, check_that_all_fields_and_groups_invisible

pytestmark = [pytest.mark.usefixtures("login_to_adcm_over_api")]


@allure.step("Check invisible and advanced for groups false for fields true")
def _check_invisible_and_advanced_for_groups_false_for_fields_true(sdk_client: ADCMClient, path, app):
    _, config = prepare_cluster_and_get_config(sdk_client, path, app)
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert group_names, group_names
    config.show_advanced()
    assert config.advanced
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert group_names
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


@allure.step("Check that fields and groups visible only if advanced enabled")
def _check_groups_and_fields_visible_if_advanced_enabled(sdk_client: ADCMClient, path, app):
    _, config = prepare_cluster_and_get_config(sdk_client, path, app)
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert not group_names, group_names
    config.show_advanced()
    assert config.advanced
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert group_names
    for field in fields:
        assert field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(__file__, "group_advanced_false_invisible_false_field_advanced_false_invisible_false")
def test_all_false(sdk_client_fs: ADCMClient, path, app_fs):
    """Check group and field ui options when advanced and invisible is false
    Scenario:
    1. Create cluster
    2. Get list of fields
    3. Check that 1 field is visible
    4. Check that 1 group visible
    5. Enable advanced
    6. Check that 1 field is visible
    7. Check that 1 group is visible
    """

    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app_fs.driver, "{}/cluster/{}/config".format(app_fs.adcm.url, cluster.cluster_id))

    groups = config.get_field_groups()
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")
    group_names = config.get_group_elements()
    with allure.step('Check that 1 field and 1 group is visible'):
        assert len(group_names) == 1
        assert group_names[0].text == cluster_name
        assert group_names, group_names
    config.show_advanced()
    assert config.advanced
    group_names = config.get_group_elements()
    with allure.step('Check that 1 field and 1 group is visible'):
        assert group_names, group_names
        assert len(group_names) == 1
        assert group_names[0].text == cluster_name
        groups = config.get_field_groups()
        for group in groups:
            assert group.is_displayed(), group.get_attribute("class")


@parametrize_by_data_subdirs(__file__, "group_advanced_true_invisible_true_field_advanced_true_invisible_true")
def test_all_true(sdk_client_fs: ADCMClient, path, app_fs):
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")
    group_names = config.get_group_elements()
    assert not group_names, group_names
    config.show_advanced()
    assert config.advanced
    with allure.step('Check group and field ui options when advanced and invisible is true'):
        groups = config.get_field_groups()
        group_names = config.get_group_elements()
        assert not group_names
        for group in groups:
            assert not group.is_displayed(), group.get_attribute("class")


@parametrize_by_data_subdirs(__file__, "group_advanced_false_invisible_false_field_advanced_true_invisible_true")
def test_groups_false_fields_true(sdk_client_fs: ADCMClient, path, app_fs):
    """Invisible and advanced for groups false for fields true."""

    _check_invisible_and_advanced_for_groups_false_for_fields_true(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(__file__, "group_advanced_true_invisible_true_field_advanced_false_invisible_false")
def test_groups_true_fields_false(sdk_client_fs: ADCMClient, path, app_fs):
    """Invisible and advanced for groups true for fields false.
    In this case no elements presented on page
    """
    check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(__file__, "group_advanced_false_invisible_true_field_advanced_false_invisible_true")
def test_invisible_true_advanced_false(sdk_client_fs: ADCMClient, path, app_fs):
    """Invisible and advanced for groups true for fields false.
    In this case no elements presented on page
    """
    check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(__file__, "group_advanced_true_invisible_false_field_advanced_true_invisible_false")
def test_invisible_false_advanced_true(sdk_client_fs: ADCMClient, path, app_fs):
    """Fields and groups visible only if advanced enabled."""
    _check_groups_and_fields_visible_if_advanced_enabled(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(__file__, "group_advanced_false_invisible_false_field_advanced_false_invisible_true")
def test_group_advanced_false_invisible_false_field_advanced_false_invisible_true(
    sdk_client_fs: ADCMClient, path, app_fs
):
    """Invisible and advanced for groups false for fields true"""
    _check_invisible_and_advanced_for_groups_false_for_fields_true(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(__file__, "group_advanced_false_invisible_false_field_advanced_true_invisible_false")
def test_group_advanced_false_invisible_false_field_advanced_true_invisible_false(
    sdk_client_fs: ADCMClient, path, app_fs
):
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert group_names, group_names
    config.show_advanced()
    assert config.advanced
    with allure.step('Check groups are visible always, field only if advanced enabled'):
        fields = config.get_field_groups()
        group_names = config.get_group_elements()
        assert group_names
        for field in fields:
            assert field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(__file__, "group_advanced_false_invisible_true_field_advanced_false_invisible_false")
def test_group_advanced_false_invisible_true_field_advanced_false_invisible_false(
    sdk_client_fs: ADCMClient, path, app_fs
):
    """Invisible and advanced for groups true for fields false.
    In this case no elements presented on page
    """
    check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(__file__, "group_advanced_false_invisible_true_field_advanced_true_invisible_false")
def test_group_advanced_false_invisible_true_field_advanced_true_invisible_false(
    sdk_client_fs: ADCMClient, path, app_fs
):
    """Invisible and advanced for groups true for fields false.
    In this case no elements presented on page
    """
    check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(__file__, "group_advanced_false_invisible_true_field_advanced_true_invisible_true")
def test_group_advanced_false_invisible_true_field_advanced_true_invisible_true(
    sdk_client_fs: ADCMClient, path, app_fs
):
    """Invisible and advanced for groups true for fields false.
    In this case no elements presented on page
    """
    check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(__file__, "group_advanced_true_invisible_false_field_advanced_false_invisible_false")
def test_group_advanced_true_invisible_false_field_advanced_false_invisible_false(
    sdk_client_fs: ADCMClient, path, app_fs
):
    """Fields and groups visible only if advanced enabled."""
    _check_groups_and_fields_visible_if_advanced_enabled(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(__file__, "group_advanced_true_invisible_false_field_advanced_false_invisible_true")
def test_group_advanced_true_invisible_false_field_advanced_false_invisible_true(
    sdk_client_fs: ADCMClient, path, app_fs
):
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert not group_names, group_names
    config.show_advanced()
    assert config.advanced
    with allure.step('Check that only group is visible if advanced enabled'):
        fields = config.get_field_groups()
        group_names = config.get_group_elements()
        assert group_names
        for field in fields:
            assert not field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(__file__, "group_advanced_true_invisible_false_field_advanced_true_invisible_true")
def test_group_advanced_true_invisible_false_field_advanced_true_invisible_true(
    sdk_client_fs: ADCMClient, path, app_fs
):
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert not group_names, group_names
    config.show_advanced()
    assert config.advanced
    with allure.step('Check that group is visible with advanced option and field is invisible'):
        fields = config.get_field_groups()
        group_names = config.get_group_elements()
        assert group_names
        for field in fields:
            assert not field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(__file__, "group_advanced_true_invisible_true_field_advanced_false_invisible_true")
def test_group_advanced_true_invisible_true_field_advanced_false_invisible_true(
    sdk_client_fs: ADCMClient, path, app_fs
):
    """Invisible and advanced for groups true for fields false.
    In this case no elements presented on page
    """
    check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(__file__, "group_advanced_true_invisible_true_field_advanced_true_invisible_false")
def test_group_advanced_true_invisible_true_field_advanced_true_invisible_false(
    sdk_client_fs: ADCMClient, path, app_fs
):
    """Invisible and advanced for groups true for fields false.
    In this case no elements presented on page
    """
    check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)
