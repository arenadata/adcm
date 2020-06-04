import pytest
import random
import string
# pylint: disable=W0611, W0621, C0302, R0914

from adcm_client.objects import ADCMClient

from adcm_pytest_plugin.utils import parametrize_by_data_subdirs

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.configuration import Configuration
from tests.ui_tests.app.pages import LoginPage


def random_string(lenght=8):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.sample(letters, lenght))


@pytest.fixture(scope="module")
def app(adcm_ms):
    app = ADCMTest(adcm_ms)
    yield app
    app.destroy()


@pytest.fixture(scope="module")
def login_on_adcm(app):
    """Login on page ADCM
    :param app:
    :return:
    """
    app.driver.implicitly_wait(0)
    app.driver.get(app.adcm.url)
    login = LoginPage(app.driver)
    login.login("admin", "admin")


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_false_field_advanced_false_invisible_false_activiatable_false")
def test_group_advanced_false_invisible_false_field_advanced_false_invisible_false_active_false(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Check that group not active and field is invisible until group is not active.
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Check that group active and all fields always visible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Check that field is invisible if group is active or not
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_false_field_advanced_false_invisible_true_activiatable_true")
def test_group_advanced_false_invisible_false_field_advanced_false_invisible_true_active_true(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Check that field invisible if activatable group active and not
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_false_field_advanced_true_invisible_false_activiatable_false")
def test_group_advanced_false_invisible_false_field_advanced_true_invisible_false_active_false(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Check that field visible if advanced group is enabled.
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Check that field is visible if group active and advanced enabled
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Check that field is invisible if activatable group is active and not
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_false_field_advanced_true_invisible_true_activiatable_true")
def test_group_advanced_false_invisible_false_field_advanced_true_invisible_true_active_true(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Check that field invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_false_invisible_false_activiatable_false")
def test_group_advanced_false_invisible_true_field_advanced_false_invisible_false_active_false(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Check thats all fields and groups invisible.
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_false_invisible_false_activiatable_true")
def test_group_advanced_false_invisible_true_field_advanced_false_invisible_false_active_true(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Check thats all fields and groups invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_false_invisible_true_activiatable_false")
def test_group_advanced_false_invisible_true_field_advanced_false_invisible_true_active_false(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Check that fields and groups invisible.
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_false_invisible_true_activiatable_true")
def test_group_advanced_false_invisible_true_field_advanced_false_invisible_true_active_true(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """All invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_true_invisible_false_activiatable_false")
def test_group_advanced_false_invisible_true_field_advanced_true_invisible_false_active_false(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """All invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_true_invisible_false_activiatable_true")
def test_group_advanced_false_invisible_true_field_advanced_true_invisible_false_active_true(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """All invisible
    :return:
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_true_invisible_true_activiatable_false")
def test_group_advanced_false_invisible_true_field_advanced_true_invisible_true_active_false(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs):
    """All invisible
    """
    _ = login_on_adcm, gather_logs
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_true_field_advanced_true_invisible_true_activiatable_true")
def test_group_advanced_false_invisible_true_field_advanced_true_invisible_true_active_true(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """All invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_false_field_advanced_false_invisible_false_activiatable_false")
def test_group_advanced_true_invisible_false_field_advanced_false_invisible_false_active_false(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Fields visible only if advanced enabled
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_false_field_advanced_false_invisible_false_activiatable_true")
def test_group_advanced_true_invisible_false_field_advanced_false_invisible_false_active_true(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Field visible if advanced and activatable true
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_false_field_advanced_false_invisible_true_activiatable_false")
def test_group_advanced_true_invisible_false_field_advanced_false_invisible_true_active_false(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Field invisible, group visible if advanced
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Check that field invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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
    "group_advanced_true_invisible_false_field_advanced_true_invisible_false_activiatable_false")
def test_group_advanced_true_invisible_false_field_advanced_true_invisible_false_active_false(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Check that field and group visible if advanced button clicked
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Check that field visible if advanced clicked.
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Field always invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """Field invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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
    "group_advanced_true_invisible_true_field_advanced_false_invisible_false_activiatable_false")
def test_group_advanced_true_invisible_true_field_advanced_false_invisible_false_active_false(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """All invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_true_field_advanced_false_invisible_false_activiatable_true")
def test_group_advanced_true_invisible_true_field_advanced_false_invisible_false_active_true(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """All invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_true_field_advanced_false_invisible_true_activiatable_false")
def test_group_advanced_true_invisible_true_field_advanced_false_invisible_true_active_false(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """All invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_true_field_advanced_true_invisible_false_activiatable_false")
def test_group_advanced_true_invisible_true_field_advanced_true_invisible_false_active_false(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """All invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_true_field_advanced_false_invisible_true_activiatable_true")
def test_group_advanced_true_invisible_true_field_advanced_false_invisible_true_active_true(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """All invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_true_field_advanced_true_invisible_false_activiatable_true")
def test_group_advanced_true_invisible_true_field_advanced_true_invisible_false_active_true(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """All invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_true_field_advanced_true_invisible_true_activiatable_false")
def test_group_advanced_true_invisible_true_field_advanced_true_invisible_true_active_false(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """All invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_true_invisible_true_field_advanced_true_invisible_true_activiatable_true")
def test_group_advanced_true_invisible_true_field_advanced_true_invisible_true_active_true(
        sdk_client_ms: ADCMClient, path, app, login_on_adcm, gather_logs, screenshot_on_failure):
    """All invisible
    """
    _ = login_on_adcm, gather_logs, screenshot_on_failure
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-2:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           "{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
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
