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

"""Test config page with invisible params in bundles"""

import allure
import pytest
from adcm_client.objects import ADCMClient

from tests.ui_tests.app.helpers.configs_generator import (
    TYPES,
    generate_configs,
    generate_group_configs,
    prepare_config,
    prepare_group_config,
)
from tests.ui_tests.app.page.cluster.page import ClusterGroupConfigConfig
from tests.ui_tests.utils import prepare_cluster_and_open_config_page


@pytest.mark.full()
@pytest.mark.usefixtures("_login_to_adcm_over_api")
def test_group_configs_fields_invisible_true(sdk_client_fs: ADCMClient, app_fs):
    """Test complex configuration group with all fields invisible"""
    with allure.step("Prepare big config"):
        res = [
            generate_group_configs(
                field_type=field_type,
                activatable=activatable,
                active=active,
                group_advanced=group_advanced,
                default=is_default,
                required=is_required,
                read_only=is_read_only,
                field_invisible=field_invisible,
                field_advanced=field_advanced,
            )[0]
            for field_type in TYPES
            for field_advanced in (True, False)
            for field_invisible in (True, False)
            for is_default in (True, False)
            for is_required in (True, False)
            for is_read_only in (True, False)
            for activatable in (True, False)
            for active in (True, False)
            for group_advanced in (True, False)
        ]
        full_config = [
            {**combination[0]["config"][0], "name": f"{combination[0]['config'][0]['name']}_{i}"}
            for i, combination in enumerate(res)
        ]
        _, _, path = prepare_group_config(([{**res[0][0], "config": full_config}], None), enforce_file=True)

    cluster, _ = prepare_cluster_and_open_config_page(sdk_client_fs, path, app_fs)
    cluster_group_config = cluster.group_config_create(name="Test group")
    cluster_config_page = ClusterGroupConfigConfig(
        app_fs.driver, app_fs.adcm.url, cluster.id, cluster_group_config.id
    ).open()
    cluster_config_page.wait_page_is_opened()
    cluster_config_page.config.check_no_rows_or_groups_on_page()
    cluster_config_page.config.check_no_rows_or_groups_on_page_with_advanced()
    with allure.step('Check that save button is disabled'):
        assert cluster_config_page.config.is_save_btn_disabled(), 'Save button should be disabled'


@pytest.mark.full()
@pytest.mark.usefixtures("_login_to_adcm_over_api")
def test_configs_fields_invisible_true(sdk_client_fs: ADCMClient, app_fs):
    """Check RO different variations of invisible config params"""
    with allure.step("Prepare big config"):
        res = [
            generate_configs(
                field_type=field_type,
                advanced=is_advanced,
                default=is_default,
                required=is_required,
                read_only=is_read_only,
                config_group_customization=config_group_customization,
                group_customization=group_customization,
            )[0]
            for field_type in TYPES
            for is_advanced in (True, False)
            for is_default in (True, False)
            for is_required in (True, False)
            for is_read_only in (True, False)
            for config_group_customization in (True, False)
            for group_customization in (True, False)
        ]
        full_config = [
            {**combination[0]["config"][0], "name": f"{combination[0]['config'][0]['name']}_{i}"}
            for i, combination in enumerate(res)
        ]
        _, _, path = prepare_config(([{**res[0][0], "config": full_config}], None), enforce_file=True)

    _, cluster_config_page = prepare_cluster_and_open_config_page(sdk_client_fs, path, app_fs)
    cluster_config_page.config.check_no_rows_or_groups_on_page()
    cluster_config_page.config.check_no_rows_or_groups_on_page_with_advanced()
    with allure.step('Check that save button is disabled'):
        assert cluster_config_page.config.is_save_btn_disabled(), 'Save button should be disabled'
