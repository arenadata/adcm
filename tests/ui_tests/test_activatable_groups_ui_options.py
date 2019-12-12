import pytest
# pylint: disable=W0611, W0621, C0302

from adcm_client.objects import ADCMClient

from adcm_pytest_plugin.utils import parametrize_by_data_subdirs

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.pages import Configuration, LoginPage


@pytest.fixture(scope="module")
def app(adcm):
    app = ADCMTest(adcm)
    app.driver.get(app.adcm.url)
    login = LoginPage(app.driver)
    login.login("admin", "admin")
    return app


@parametrize_by_data_subdirs(
    __file__,
    "group_advanced_false_invisible_false_field_advanced_false_invisible_false_activiatable_false")
def test_group_advanced_false_invisible_false_field_advanced_false_invisible_false_active_false(
        sdk_client_ms: ADCMClient, path, app):
    """Check that group not active and field is invisible until group is not active.
    :param sdk_client_ms:
    :param path:
    :param app:
    :return:
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Check that group active and all fields always visible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Check that field is invisible if group is active or not
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Check that field invisible if activatable group active and not
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Check that field visible if advanced group is enabled.
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Check that field is visible if group active and advanced enabled
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Check that field is invisible if activatable group is active and not
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Check that field invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Check thats all fields and groups invisible.
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Check thats all fields and groups invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Check that fields and groups invisible.
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """All invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """All invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """All invisible
    :return:
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """All invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """All invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Fields visible only if advanced enabled
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Field visible if advanced and activatable true
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Field invisible, group visible if advanced
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Check that field invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Check that field and group visible if advanced button clicked
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Check that field visible if advanced clicked.
    :return:
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Field always invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """Field invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    group_name = path.split("/")[-1]
    cluster_name = "_".join(path.split("/")[-2:])
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """All invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """All invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """All invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """All invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """All invisible

    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """All invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """All invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
        sdk_client_ms: ADCMClient, path, app):
    """All invisible
    """
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
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
