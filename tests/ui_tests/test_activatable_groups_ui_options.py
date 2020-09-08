# pylint: disable=W0611, W0621, C0302, R0914

from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import parametrize_by_data_subdirs

from .utils import prepare_cluster_and_get_config


def _check_that_field_is_invisible_if_group_active_or_not(sdk_client: ADCMClient, path, app):
    """Check that field is invisible if group is active or not
    """
    _, config = prepare_cluster_and_get_config(sdk_client, path, app)

    group_name = path.split("/")[-1]
    group_active = config.group_is_active_by_name(group_name)
    assert not group_active
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    assert group_names, group_names
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    config.activate_group_by_name(
        group_name)
    group_active = config.group_is_active_by_name(group_name)
    assert group_active
    group_names = config.get_group_elements()
    assert group_names, group_names
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


def _check_that_field_invisible_if_activatable_group_active_and_not(
        sdk_client: ADCMClient, path, app):
    """Check that field invisible if activatable group active and not
    """
    _, config = prepare_cluster_and_get_config(sdk_client, path, app)

    group_name = path.split("/")[-1]
    group_active = config.group_is_active_by_name(group_name)
    assert group_active
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    assert group_names, group_names
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    config.activate_group_by_name(
        group_name)
    group_active = config.group_is_active_by_name(group_name)
    assert group_active
    group_names = config.get_group_elements()
    assert group_names, group_names
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


def _check_that_all_fields_and_groups_invisible(
        sdk_client: ADCMClient, path, app):
    """Check that all fields and groups invisible.
    """
    _, config = prepare_cluster_and_get_config(sdk_client, path, app)

    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert not group_names, group_names
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert not group_names
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


def _check_that_all_field_is_visible_if_advanced_and_activatable_true(
        sdk_client: ADCMClient, path, app):
    """Field visible if advanced and activatable true
    """
    _, config = prepare_cluster_and_get_config(sdk_client, path, app)

    group_name = path.split("/")[-1]
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert not group_names, group_names
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    config.activate_group_by_name(
        group_name)
    group_active = config.group_is_active_by_name(group_name)
    assert group_active
    group_names = config.get_group_elements()
    assert group_names, group_names
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    fields = config.get_field_groups()
    for field in fields:
        assert field.is_displayed(), field.get_attribute("class")


def _check_that_all_field_is_invisible(
        sdk_client: ADCMClient, path, app):
    """Check that field invisible
    """
    _, config = prepare_cluster_and_get_config(sdk_client, path, app)

    group_name = path.split("/")[-1]
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert not group_names, group_names
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    group_active = config.group_is_active_by_name(group_name)
    assert group_active
    group_names = config.get_group_elements()
    assert group_names, group_names
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_false_field_advanced_false_invisible_false_activiatable_false")
def test_group_advanced_false_invisible_false_field_advanced_false_invisible_false_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that group not active and field is invisible until group is not active.
    """
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    group_name = path.split("/")[-1]
    group_active = config.group_is_active_by_name(group_name)
    assert not group_active
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    assert group_names, group_names
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    config.activate_group_by_name(
        group_name)
    group_active = config.group_is_active_by_name(group_name)
    assert group_active
    group_names = config.get_group_elements()
    assert group_names, group_names
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    fields = config.get_field_groups()
    for field in fields:
        assert field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_false_field_advanced_false_invisible_false_activiatable_true")
def test_group_advanced_false_invisible_false_field_advanced_false_invisible_false_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that group active and all fields always visible
    """
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    group_name = path.split("/")[-1]
    group_active = config.group_is_active_by_name(group_name)
    assert group_active
    fields = config.get_field_groups()
    for field in fields:
        assert field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    assert group_names, group_names
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    config.activate_group_by_name(
        group_name)
    group_active = config.group_is_active_by_name(group_name)
    assert group_active
    group_names = config.get_group_elements()
    assert group_names, group_names
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    fields = config.get_field_groups()
    for field in fields:
        assert field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_false_field_advanced_false_invisible_true_activiatable_false")
def test_group_advanced_false_invisible_false_field_advanced_false_invisible_true_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that field is invisible if group is active or not
    """
    _check_that_field_is_invisible_if_group_active_or_not(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_false_field_advanced_false_invisible_true_activiatable_true")
def test_group_advanced_false_invisible_false_field_advanced_false_invisible_true_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that field invisible if activatable group active and not
    """
    _check_that_field_invisible_if_activatable_group_active_and_not(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_false_field_advanced_true_invisible_false_activiatable_false")
def test_group_advanced_false_invisible_false_field_advanced_true_invisible_false_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that field visible if advanced group is enabled.
    """
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    group_name = path.split("/")[-1]
    group_active = config.group_is_active_by_name(group_name)
    assert not group_active
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    assert group_names, group_names
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    config.activate_group_by_name(
        group_name)
    group_active = config.group_is_active_by_name(group_name)
    assert group_active
    group_names = config.get_group_elements()
    assert group_names, group_names
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    fields = config.get_field_groups()
    for field in fields:
        assert field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_false_field_advanced_true_invisible_false_activiatable_true")
def test_group_advanced_false_invisible_false_field_advanced_true_invisible_false_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that field is visible if group active and advanced enabled
    """
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    group_name = path.split("/")[-1]
    group_active = config.group_is_active_by_name(group_name)
    assert group_active
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    assert group_names, group_names
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    config.activate_group_by_name(
        group_name)
    group_active = config.group_is_active_by_name(group_name)
    assert group_active
    group_names = config.get_group_elements()
    assert group_names, group_names
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    fields = config.get_field_groups()
    for field in fields:
        assert field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_false_field_advanced_true_invisible_true_activiatable_false")
def test_group_advanced_false_invisible_false_field_advanced_true_invisible_true_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that field is invisible if group is active or not
    """
    _check_that_field_is_invisible_if_group_active_or_not(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_false_field_advanced_true_invisible_true_activiatable_true")
def test_group_advanced_false_invisible_false_field_advanced_true_invisible_true_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that field invisible if activatable group active and not
    """
    _check_that_field_invisible_if_activatable_group_active_and_not(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_false_invisible_false_activiatable_false")
def test_group_advanced_false_invisible_true_field_advanced_false_invisible_false_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_false_invisible_false_activiatable_true")
def test_group_advanced_false_invisible_true_field_advanced_false_invisible_false_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_false_invisible_true_activiatable_false")
def test_group_advanced_false_invisible_true_field_advanced_false_invisible_true_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_false_invisible_true_activiatable_true")
def test_group_advanced_false_invisible_true_field_advanced_false_invisible_true_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_true_invisible_false_activiatable_false")
def test_group_advanced_false_invisible_true_field_advanced_true_invisible_false_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_true_invisible_false_activiatable_true")
def test_group_advanced_false_invisible_true_field_advanced_true_invisible_false_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_true_invisible_true_activiatable_false")
def test_group_advanced_false_invisible_true_field_advanced_true_invisible_true_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_true_invisible_true_activiatable_true")
def test_group_advanced_false_invisible_true_field_advanced_true_invisible_true_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_false_field_advanced_false_invisible_false_activiatable_false")
def test_group_advanced_true_invisible_false_field_advanced_false_invisible_false_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Field visible if advanced and activatable true
    """
    _check_that_all_field_is_visible_if_advanced_and_activatable_true(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_false_field_advanced_false_invisible_false_activiatable_true")
def test_group_advanced_true_invisible_false_field_advanced_false_invisible_false_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Field visible if advanced and activatable true
    """
    _check_that_all_field_is_visible_if_advanced_and_activatable_true(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_false_field_advanced_false_invisible_true_activiatable_false")
def test_group_advanced_true_invisible_false_field_advanced_false_invisible_true_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Field invisible, group visible if advanced
    """
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    group_name = path.split("/")[-1]
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert not group_names, group_names
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    group_active = config.group_is_active_by_name(group_name)
    assert not group_active
    config.activate_group_by_name(
        group_name)
    group_active = config.group_is_active_by_name(group_name)
    assert group_active
    group_names = config.get_group_elements()
    assert group_names, group_names
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_false_field_advanced_false_invisible_true_activiatable_true")
def test_group_advanced_true_invisible_false_field_advanced_false_invisible_true_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that field invisible
    """
    _check_that_all_field_is_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_false_field_advanced_true_invisible_false_activiatable_false")
def test_group_advanced_true_invisible_false_field_advanced_true_invisible_false_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that field and group visible if advanced button clicked
    """
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    group_name = path.split("/")[-1]
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert not group_names, group_names
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    group_active = config.group_is_active_by_name(group_name)
    assert not group_active
    config.activate_group_by_name(
        group_name)
    group_active = config.group_is_active_by_name(group_name)
    assert group_active
    group_names = config.get_group_elements()
    assert group_names, group_names
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    fields = config.get_field_groups()
    for field in fields:
        assert field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_false_field_advanced_true_invisible_false_activiatable_true")
def test_group_advanced_true_invisible_false_field_advanced_true_invisible_false_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that field visible if advanced clicked.
    """
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    group_name = path.split("/")[-1]
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert not group_names, group_names
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    group_active = config.group_is_active_by_name(group_name)
    assert group_active
    group_names = config.get_group_elements()
    assert group_names, group_names
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    fields = config.get_field_groups()
    for field in fields:
        assert field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_false_field_advanced_true_invisible_true_activiatable_false")
def test_group_advanced_true_invisible_false_field_advanced_true_invisible_true_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Field always invisible
    """
    _, config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    group_name = path.split("/")[-1]
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert not group_names, group_names
    if not config.advanced:
        config.click_advanced()
    assert config.advanced
    config.activate_group_by_name(group_name)
    group_active = config.group_is_active_by_name(group_name)
    assert group_active
    group_names = config.get_group_elements()
    assert group_names, group_names
    assert len(group_names) == 1
    assert group_names[0].text == group_name
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_false_field_advanced_true_invisible_true_activiatable_true")
def test_group_advanced_true_invisible_false_field_advanced_true_invisible_true_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that field invisible
    """
    _check_that_all_field_is_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_true_field_advanced_false_invisible_false_activiatable_false")
def test_group_advanced_true_invisible_true_field_advanced_false_invisible_false_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_true_field_advanced_false_invisible_false_activiatable_true")
def test_group_advanced_true_invisible_true_field_advanced_false_invisible_false_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_true_field_advanced_false_invisible_true_activiatable_false")
def test_group_advanced_true_invisible_true_field_advanced_false_invisible_true_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_true_field_advanced_true_invisible_false_activiatable_false")
def test_group_advanced_true_invisible_true_field_advanced_true_invisible_false_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_true_field_advanced_false_invisible_true_activiatable_true")
def test_group_advanced_true_invisible_true_field_advanced_false_invisible_true_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_true_field_advanced_true_invisible_false_activiatable_true")
def test_group_advanced_true_invisible_true_field_advanced_true_invisible_false_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_true_field_advanced_true_invisible_true_activiatable_false")
def test_group_advanced_true_invisible_true_field_advanced_true_invisible_true_active_false(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_true_field_advanced_true_invisible_true_activiatable_true")
def test_group_advanced_true_invisible_true_field_advanced_true_invisible_true_active_true(
        sdk_client_fs: ADCMClient, path, app_fs, login_to_adcm):
    """Check that all fields and groups invisible.
    """
    _check_that_all_fields_and_groups_invisible(sdk_client_fs, path, app_fs)
