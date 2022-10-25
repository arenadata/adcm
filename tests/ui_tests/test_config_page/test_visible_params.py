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

"""Test config page with visible params in bundles"""

from dataclasses import asdict, dataclass

import allure
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.webdriver.remote.webelement import WebElement

from tests.ui_tests.app.helpers.configs_generator import (
    TYPES,
    generate_configs,
    generate_group_configs,
    prepare_config,
    prepare_group_config,
)
from tests.ui_tests.app.page.cluster.page import ClusterGroupConfigConfig, ClusterConfigPage
from tests.ui_tests.utils import prepare_cluster_and_open_config_page

# pylint: disable=too-many-arguments,too-many-locals,too-many-boolean-expressions, too-many-statements

pytestmark = [
    pytest.mark.usefixtures("_cleanup_browser_logs", "_attach_debug_info_on_ui_test_fail", "_login_over_api_ms")
]


def check_default_field_values_in_configs(
    cluster_config_page: ClusterConfigPage, config_item: WebElement, field_type: str, config
):
    """Check that input value in config is equal to the default one"""
    main_config = config['config'][0]['subs'][0] if "subs" in config['config'][0] else config['config'][0]
    if field_type == 'boolean':
        cluster_config_page.config.assert_checkbox_state(config_item, expected_value=main_config['default'])
    elif field_type in ("password", "secrettext"):
        is_password_value = bool(field_type == "password")
        cluster_config_page.config.assert_input_value_is(
            expected_value='********', display_name=field_type, is_password=is_password_value
        )
    elif field_type == "list":
        cluster_config_page.config.assert_list_value_is(expected_value=main_config['default'], display_name=field_type)
    elif field_type == "map":
        cluster_config_page.config.assert_map_value_is(expected_value=main_config['default'], display_name=field_type)
    elif field_type == "file":
        cluster_config_page.config.assert_input_value_is(expected_value="test", display_name=field_type)
    else:
        expected_value = (
            str(main_config['default']) if field_type in ("integer", "float", "json") else main_config['default']
        )
        cluster_config_page.config.assert_input_value_is(expected_value=expected_value, display_name=field_type)


@allure.step("Check save button and save config")
def check_save_in_configs(cluster_config_page, field_type, expected_state, is_default):
    """
    Check save button and save config.
    It is a workaround for each type of field because it won't work other way on ui with selenium.
    """

    config_row = cluster_config_page.config.get_config_row(field_type)
    if field_type == 'list':
        cluster_config_page.config.click_add_item_btn_in_row(config_row)
    if field_type in ['string', 'integer', 'text', 'float', 'file', 'json']:
        config_row.click()
    if field_type == 'secrettext':
        cluster_config_page.config.reset_to_default(config_row)
    if field_type == 'boolean' and is_default:
        for _ in range(3):
            cluster_config_page.config.click_boolean_checkbox(config_row)
    if field_type == 'password':
        if is_default:
            cluster_config_page.config.reset_to_default(config_row)
        else:
            config_row.click()
    if field_type == 'map':
        cluster_config_page.config.click_add_item_btn_in_row(config_row)
        cluster_config_page.config.reset_to_default(config_row)
    cluster_config_page.config.check_save_btn_state_and_save_conf(expected_state)


@dataclass()
class ParamCombination:  # pylint: disable=too-many-instance-attributes
    """Container for params used in test to generate config"""

    field_type: str
    activatable: bool
    active: bool
    group_advanced: bool
    default: bool
    required: bool
    read_only: bool
    field_invisible: bool
    field_advanced: bool


def _prepare_combinations():
    return [
        ParamCombination(
            field_type, group_advanced, is_default, is_required, is_read_only, activatable, active, invisible, advanced
        )
        for field_type in TYPES
        for group_advanced in (True, False)
        for is_default in (True, False)
        for is_required in (True, False)
        for is_read_only in (True, False)
        for activatable in (True, False)
        for active in (True, False)
        for invisible in (True, False)
        for advanced in (True, False)
    ]


def _check_expectations_for_group_configs_fields(page, combo: ParamCombination, alerts_expected, config):
    with allure.step('Check that group field is visible'):
        group_name = page.config.get_group_names()[0].text
        assert group_name == 'group', "Group with name 'group' should be visible"

    # why ?
    if not combo.activatable:  # group activatable
        return

    if not page.config.advanced:
        page.config.check_group_is_active(group_name, config['config'][0]['active'])

    # rewrite this condition, it's unreadable
    if not (
        not combo.field_invisible and ((page.config.advanced and combo.field_advanced) or not combo.field_advanced)
    ):
        with allure.step("Check field is invisible"):
            assert len(page.config.get_all_config_rows()) == 1, "Field should not be visible"
            return

    page.config.expand_or_close_group(group_name, expand=True)

    def _check_field_is_visible_after_group_is_epanded():
        assert len(page.config.get_all_config_rows()) >= 2, "Field should be visible"

    wait_until_step_succeeds(_check_field_is_visible_after_group_is_epanded, timeout=5, period=0.2)

    config_item = page.config.get_all_config_rows()[1]

    if combo.default:
        check_default_field_values_in_configs(page, config_item, combo.field_type, config)

    if combo.read_only and config_item.tag_name == 'app-field':
        assert page.config.is_element_read_only(config_item), f"Config field {combo.field_type} should be read only"

    if alerts_expected and not combo.read_only:
        if combo.field_type == "map":
            is_advanced = page.config.advanced
            page.driver.refresh()
            if is_advanced:
                page.config.click_on_advanced()
            page.config.expand_or_close_group(group_name, expand=True)
        if combo.field_type == "password":
            page.config.reset_to_default(config_item)
        else:
            page.config.click_on_advanced()
            page.config.click_on_advanced()
        page.config.check_invalid_value_message(combo.field_type)


@pytest.mark.full()
@pytest.mark.parametrize(
    "combo", _prepare_combinations(), ids=lambda c: "-".join(f"{k}_{v}" for k, v in asdict(c).items())
)
def test_group_configs_fields(combo: ParamCombination, sdk_client_ms: ADCMClient, app_ms, objects_to_delete):
    """Test group configs with not-invisible fields"""
    config, expected, path = prepare_group_config(generate_group_configs(group_invisible=False, **asdict(combo)))
    cluster, page = prepare_cluster_and_open_config_page(sdk_client_ms, path, app_ms)
    objects_to_delete.append(cluster)

    if combo.group_advanced:
        page.config.check_no_rows_or_groups_on_page()
    else:
        _check_expectations_for_group_configs_fields(
            page=page, combo=combo, alerts_expected=expected['alerts'], config=config
        )
    page.config.click_on_advanced()
    _check_expectations_for_group_configs_fields(
        page=page, combo=combo, alerts_expected=expected['alerts'], config=config
    )
    if (not combo.read_only) and (not combo.field_invisible) and (not combo.required) and combo.default:
        check_save_in_configs(page, combo.field_type, expected["save"], combo.default)


@pytest.mark.full()
@pytest.mark.parametrize("field_type", TYPES)
@pytest.mark.parametrize("is_advanced", [True, False], ids=("field_advanced", "field_non-advanced"))
@pytest.mark.parametrize("is_default", [True, False], ids=("default", "not_default"))
@pytest.mark.parametrize("is_required", [True, False], ids=("required", "not_required"))
@pytest.mark.parametrize("is_read_only", [True, False], ids=("read_only", "not_read_only"))
@pytest.mark.parametrize(
    "config_group_customization",
    [True, False, None],
    ids=("config_group_customization_true", "config_group_customization_false", "no_config_group_customization"),
)
@pytest.mark.parametrize(
    "group_customization",
    [True, False, None],
    ids=("group_customization_true", "group_customization_false", "no_group_customization"),
)
def test_visible_group_config_fields(
    sdk_client_ms,
    app_ms,
    field_type,
    is_advanced,
    is_default,
    is_required,
    is_read_only,
    config_group_customization,
    group_customization,
    objects_to_delete,
):
    """Test group config fields that aren't invisible"""
    config, expected, path = prepare_config(
        generate_configs(
            field_type=field_type,
            invisible=False,
            advanced=is_advanced,
            default=is_default,
            required=is_required,
            read_only=is_read_only,
            config_group_customization=config_group_customization,
            group_customization=group_customization,
        )
    )
    cluster, *_ = prepare_cluster_and_open_config_page(sdk_client_ms, path, app_ms)
    objects_to_delete.append(cluster)
    cluster_group_config = cluster.group_config_create(name="Test group")
    cluster_config_page = ClusterGroupConfigConfig(
        app_ms.driver, app_ms.adcm.url, cluster.id, cluster_group_config.id
    ).open()

    def check_expectations():
        with allure.step('Check that field is visible'):
            assert len(
                cluster_config_page.group_config.get_all_group_config_rows(timeout=1)
            ), f"Config field {field_type} should be visible"
            config_row = cluster_config_page.group_config.get_all_group_config_rows(timeout=0.5)[0]

        if is_default:
            with allure.step("Check defaults"):
                check_default_field_values_in_configs(cluster_config_page, config_row, field_type, config)
                if not config_group_customization:
                    cluster_config_page.config.check_inputs_disabled(config_row, is_password=field_type == "password")

        if is_read_only:
            with allure.step("Check read only"):
                assert cluster_config_page.config.is_element_read_only(
                    config_row
                ), f"Config field {field_type} should be read only"

        if not config_group_customization:
            with allure.step("Check group customization checkbox is disabled"):
                assert cluster_config_page.group_config.is_customization_chbx_disabled(
                    config_row
                ), f"Checkbox for field {field_type} should be disabled"
        elif expected['alerts'] and (not is_read_only):
            if not cluster_config_page.group_config.is_customization_chbx_checked(config_row):
                cluster_config_page.config.activate_group_chbx(config_row)
            cluster_config_page.config.check_invalid_value_message(field_type)

    if is_advanced:
        cluster_config_page.config.check_no_rows_or_groups_on_page()
    else:
        check_expectations()
    cluster_config_page.config.click_on_advanced()
    check_expectations()
    if not (config_group_customization and not is_read_only):
        return
    config_row = cluster_config_page.config.get_config_row(field_type)
    if not cluster_config_page.group_config.is_customization_chbx_checked(config_row):
        cluster_config_page.config.activate_group_chbx(config_row)
    if not is_required:
        check_save_in_configs(cluster_config_page, field_type, expected["save"], is_default)
    assert cluster_config_page.group_config.is_customization_chbx_checked(
        cluster_config_page.config.get_config_row(field_type)
    ), f"Config field {field_type} should be checked"


@pytest.mark.full()
@pytest.mark.parametrize("field_type", TYPES)
@pytest.mark.parametrize("activatable", [True, False], ids=("activatable", "non-activatable"))
@pytest.mark.parametrize("is_default", [True, False], ids=("default", "not_default"))
@pytest.mark.parametrize("group_advanced", [True, False], ids=("group_advanced", "group_non-advanced"))
@pytest.mark.parametrize("is_read_only", [True, False], ids=("read_only", "not_read_only"))
@pytest.mark.parametrize(
    "field_advanced",
    [
        pytest.param(True, id="field_advanced", marks=pytest.mark.regression),
        pytest.param(False, id="field_non_advanced"),
    ],
)
@pytest.mark.parametrize(
    "config_group_customization",
    [True, False, None],
    ids=("config_group_customization_true", "config_group_customization_false", "no_config_group_customization"),
)
@pytest.mark.parametrize(
    "group_customization",
    [True, False, None],
    ids=("group_customization_true", "group_customization_false", "no_group_customization"),
)
@pytest.mark.parametrize(
    "field_customization",
    [True, False, None],
    ids=("field_customization_true", "field_customization_false", "no_field_customization"),
)
def test_group_configs_fields_in_group_invisible_false(
    sdk_client_ms: ADCMClient,
    app_ms,
    field_type,
    activatable,
    is_default,
    group_advanced,
    is_read_only,
    field_advanced,
    config_group_customization,
    group_customization,
    field_customization,
    objects_to_delete,
):
    """Test group configs with not-invisible fields"""
    config, expected, path = prepare_group_config(
        generate_group_configs(
            field_type=field_type,
            activatable=activatable,
            active=True,
            group_invisible=False,
            group_advanced=group_advanced,
            default=is_default,
            required=False,
            read_only=is_read_only,
            field_invisible=False,
            field_advanced=field_advanced,
            config_group_customization=config_group_customization,
            group_customization=group_customization,
            field_customization=field_customization,
        )
    )
    cluster, *_ = prepare_cluster_and_open_config_page(sdk_client_ms, path, app_ms)
    objects_to_delete.append(cluster)
    cluster_group_config = cluster.group_config_create(name="Test group")
    cluster_config_page = ClusterGroupConfigConfig(
        app_ms.driver, app_ms.adcm.url, cluster.id, cluster_group_config.id
    ).open()

    def check_expectations():
        with allure.step('Check that field visible'):
            group_name = cluster_config_page.config.get_group_names()[0].text
            assert group_name == 'group', "Should be group 'group' visible"

        if not activatable:
            return

        if not cluster_config_page.config.advanced:
            cluster_config_page.config.check_group_is_active(group_name, config['config'][0]['active'])

        if not ((cluster_config_page.config.advanced and field_advanced) or not field_advanced):
            with allure.step("Check that config field is invisible"):
                assert len(cluster_config_page.config.get_all_config_rows()) == 1, "Field should not be visible"
            return

        with allure.step("Expand group and check field is visible"):
            cluster_config_page.config.expand_or_close_group(group_name, expand=True)
            assert len(cluster_config_page.config.get_all_config_rows()) >= 2, "Field should be visible"

        config_row = cluster_config_page.group_config.get_all_group_config_rows()[0]

        if is_default:
            check_default_field_values_in_configs(cluster_config_page, config_row, field_type, config)

        if is_read_only:
            if config_row.tag_name == 'app-field':
                assert cluster_config_page.config.is_element_read_only(
                    config_row
                ), f"Config field {field_type} should be read only"
            return

        if (
            (config_group_customization is False or config_group_customization is None)
            and (field_customization is False or field_customization is None)
        ) or ((config_group_customization is not False) and (field_customization is False)):
            cluster_config_page.config.check_inputs_disabled(config_row, is_password=bool(field_type == "password"))
            assert cluster_config_page.group_config.is_customization_chbx_disabled(
                config_row
            ), f"Checkbox for field {field_type} should be disabled"
            return

        with allure.step("Activate group and check checkbox is enabled"):
            cluster_config_page.config.activate_group_chbx(config_row)
            cluster_config_page.config.check_inputs_enabled(config_row, is_password=field_type == "password")
            assert not cluster_config_page.group_config.is_customization_chbx_disabled(
                config_row
            ), f"Checkbox for field {field_type} should not be disabled"

        if not cluster_config_page.group_config.is_customization_chbx_checked(config_row):
            cluster_config_page.group_config.click_on_customization_chbx(config_row)
        assert cluster_config_page.group_config.is_customization_chbx_checked(
            config_row
        ), f"Config field {field_type} should be checked"

        if not expected['alerts']:
            return

        if field_type == "map":
            is_advanced = cluster_config_page.config.advanced
            cluster_config_page.driver.refresh()
            if is_advanced:
                cluster_config_page.config.click_on_advanced()
            cluster_config_page.config.expand_or_close_group(group_name, expand=True)
        else:
            cluster_config_page.config.click_on_advanced()
            cluster_config_page.config.click_on_advanced()
        cluster_config_page.config.check_invalid_value_message(field_type)

    if group_advanced:
        cluster_config_page.config.check_no_rows_or_groups_on_page()
        cluster_config_page.group_config.check_no_rows()
    else:
        check_expectations()
    cluster_config_page.config.click_on_advanced()
    check_expectations()

    if not (config_group_customization is not False and not is_read_only):
        return

    group_row = cluster_config_page.group_config.get_all_group_rows()[0]
    config_row = cluster_config_page.group_config.get_all_group_config_rows()[0]

    if (
        activatable
        and group_customization
        and not cluster_config_page.group_config.is_customization_chbx_checked(group_row)
        and not cluster_config_page.group_config.is_customization_chbx_disabled(group_row)
    ):
        cluster_config_page.group_config.click_on_customization_chbx(group_row)

    if not field_customization:
        return

    if not cluster_config_page.group_config.is_customization_chbx_checked(config_row):
        cluster_config_page.config.activate_group_chbx(config_row)

    if not is_read_only:
        check_save_in_configs(cluster_config_page, field_type, expected["save"], is_default)

    with allure.step("Check that group configuration checkbox is checked"):
        assert cluster_config_page.group_config.is_customization_chbx_checked(
            cluster_config_page.config.get_config_row(field_type)
        ), f"Config field {field_type} should be checked"


# pylint: disable=too-many-locals
@pytest.mark.full()
@pytest.mark.parametrize("field_type", TYPES)
@pytest.mark.parametrize("is_advanced", [True, False], ids=("field_advanced", "field_non-advanced"))
@pytest.mark.parametrize("is_default", [True, False], ids=("default", "not_default"))
@pytest.mark.parametrize("is_required", [True, False], ids=("required", "not_required"))
@pytest.mark.parametrize("is_read_only", [True, False], ids=("read_only", "not_read_only"))
@pytest.mark.parametrize(
    "config_group_customization",
    [
        pytest.param(True, id="config_group_customization_true", marks=pytest.mark.regression),
        pytest.param(False, id="config_group_customization_false", marks=pytest.mark.regression),
    ],
)
@pytest.mark.parametrize(
    "group_customization",
    [
        pytest.param(True, id="group_customization_true", marks=pytest.mark.regression),
        pytest.param(False, id="group_customization_false", marks=pytest.mark.regression),
    ],
)
def test_configs_fields_invisible_false(
    sdk_client_ms: ADCMClient,
    app_ms,
    field_type,
    is_advanced,
    is_default,
    is_required,
    is_read_only,
    config_group_customization,
    group_customization,
    objects_to_delete,
):
    """Test config fields that aren't invisible"""
    config, expected, path = prepare_config(
        generate_configs(
            field_type=field_type,
            invisible=False,
            advanced=is_advanced,
            default=is_default,
            required=is_required,
            read_only=is_read_only,
            config_group_customization=config_group_customization,
            group_customization=group_customization,
        )
    )
    cluster, cluster_config_page = prepare_cluster_and_open_config_page(sdk_client_ms, path, app_ms)
    objects_to_delete.append(cluster)

    def check_expectations():
        with allure.step('Check that field visible'):
            rows = cluster_config_page.config.get_all_config_rows()
            assert len(rows), "Config row should be presented"
            config_row = rows[0]

        if is_default:
            with allure.step("Check default value"):
                check_default_field_values_in_configs(cluster_config_page, config_row, field_type, config)

        if is_read_only:
            with allure.step("Check is read only"):
                assert cluster_config_page.config.is_element_read_only(
                    config_row
                ), f"Config field {field_type} should be read only"

        if expected['alerts'] and not is_read_only:
            cluster_config_page.config.check_invalid_value_message(field_type)

    if is_read_only or (is_required and not is_default):
        with allure.step('Check that save button is disabled'):
            assert cluster_config_page.config.is_save_btn_disabled(), 'Save button should be disabled'
    else:
        with allure.step('Check that save button is enabled'):
            assert not cluster_config_page.config.is_save_btn_disabled(), 'Save button should be enabled'
    if is_advanced:
        cluster_config_page.config.check_no_rows_or_groups_on_page()
    else:
        check_expectations()
    cluster_config_page.config.click_on_advanced()
    check_expectations()
