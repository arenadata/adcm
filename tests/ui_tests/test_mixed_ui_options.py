import pytest
# pylint: disable=W0611, W0621

from adcm_client.objects import ADCMClient

from adcm_pytest_plugin.utils import parametrize_by_data_subdirs

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.pages import Configuration, LoginPage


@pytest.fixture()
def app(adcm_fs):
    app = ADCMTest(adcm_fs)
    yield app
    app.destroy()


@pytest.fixture()
def login(app):
    app.driver.get(app.adcm.url)
    login = LoginPage(app.driver)
    login.login("admin", "admin")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_false_invisible_false_field_advanced_false_invisible_false")
def test_all_false(sdk_client_fs: ADCMClient, path, app, login):
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
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    groups = config.get_field_groups()
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")
    group_names = config.get_group_elements()
    assert len(group_names) == 1
    assert group_names[0].text == cluster_name
    assert group_names, group_names
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    group_names = config.get_group_elements()
    assert group_names, group_names
    assert len(group_names) == 1
    assert group_names[0].text == cluster_name
    groups = config.get_field_groups()
    for group in groups:
        assert group.is_displayed(), group.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_true_invisible_true_field_advanced_true_invisible_true")
def test_all_true(sdk_client_fs: ADCMClient, path, app, login):
    """Check group and field ui options when advanced and invisible is true"""
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    groups = config.get_field_groups()
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")
    group_names = config.get_group_elements()
    assert not group_names, group_names
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    groups = config.get_field_groups()
    group_names = config.get_group_elements()
    assert not group_names
    for group in groups:
        assert not group.is_displayed(), group.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_false_invisible_false_field_advanced_true_invisible_true")
def test_groups_false_fields_true(sdk_client_fs: ADCMClient, path, app, login):
    """Invisible and advanced for groups false for fields true

    """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert group_names, group_names
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert group_names
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_true_invisible_true_field_advanced_false_invisible_false")
def test_groups_true_fields_false(sdk_client_fs: ADCMClient, path, app, login):
    """Invisible and advanced for groups true for fields false.
     In this case no elements presented on page
    """
    bundle = sdk_client_fs.upload_from_fs(path)
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
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert not group_names
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_false_invisible_true_field_advanced_false_invisible_true")
def test_invisible_true_advanced_false(sdk_client_fs: ADCMClient, path, app, login):
    """ Invisible true for groups and fields. In this case no elements presented on page
    """
    bundle = sdk_client_fs.upload_from_fs(path)
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
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert not group_names
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_true_invisible_false_field_advanced_true_invisible_false")
def test_invisible_false_advanced_true(sdk_client_fs: ADCMClient, path, app, login):
    """Advanced true for groups and fields.
     In this case we can see groups and fields if advanced option enabled
    """
    bundle = sdk_client_fs.upload_from_fs(path)
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
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert group_names
    for field in fields:
        assert field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_false_invisible_false_field_advanced_false_invisible_true")
def test_group_advanced_false_invisible_false_field_advanced_false_invisible_true(
        sdk_client_fs: ADCMClient, path, app, login):
    """In this case group is visible field invisible.
    """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert group_names, group_names
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert group_names
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_false_invisible_false_field_advanced_true_invisible_false")
def test_group_advanced_false_invisible_false_field_advanced_true_invisible_false(
        sdk_client_fs: ADCMClient, path, app, login):
    """Groups is visible always, field only if advanced enabled.
    """
    bundle = sdk_client_fs.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    config = Configuration(app.driver)
    fields = config.get_field_groups()
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
    group_names = config.get_group_elements()
    assert group_names, group_names
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert group_names
    for field in fields:
        assert field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_false_invisible_true_field_advanced_false_invisible_false")
def test_group_advanced_false_invisible_true_field_advanced_false_invisible_false(
        sdk_client_fs: ADCMClient, path, app, login):
    """All fields and group invisible.
    """
    bundle = sdk_client_fs.upload_from_fs(path)
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
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert not group_names
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_false_invisible_true_field_advanced_true_invisible_false")
def test_group_advanced_false_invisible_true_field_advanced_true_invisible_false(
        sdk_client_fs: ADCMClient, path, app, login):
    """All fields and group invisible.
    """
    bundle = sdk_client_fs.upload_from_fs(path)
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
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert not group_names
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_false_invisible_true_field_advanced_true_invisible_true")
def test_group_advanced_false_invisible_true_field_advanced_true_invisible_true(
        sdk_client_fs: ADCMClient, path, app, login):
    """All fields and group invisible.
    """
    bundle = sdk_client_fs.upload_from_fs(path)
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
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert not group_names
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_true_invisible_false_field_advanced_false_invisible_false")
def test_group_advanced_true_invisible_false_field_advanced_false_invisible_false(
        sdk_client_fs: ADCMClient, path, app, login):
    """Fields and groups visible only if advanced enabled.
    """
    bundle = sdk_client_fs.upload_from_fs(path)
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
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert group_names
    for field in fields:
        assert field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_true_invisible_false_field_advanced_false_invisible_true")
def test_group_advanced_true_invisible_false_field_advanced_false_invisible_true(
        sdk_client_fs: ADCMClient, path, app, login):
    """Only group is visible if advanced enabled

    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(path)
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
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert group_names
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_true_invisible_false_field_advanced_true_invisible_true")
def test_group_advanced_true_invisible_false_field_advanced_true_invisible_true(
        sdk_client_fs: ADCMClient, path, app, login):
    """Group is visible with advanced option and field is invisible
    """
    bundle = sdk_client_fs.upload_from_fs(path)
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
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert group_names
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_true_invisible_true_field_advanced_false_invisible_true")
def test_group_advanced_true_invisible_true_field_advanced_false_invisible_true(
        sdk_client_fs: ADCMClient, path, app, login):
    """All fields invisible.
    """
    bundle = sdk_client_fs.upload_from_fs(path)
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
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert not group_names
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")


@parametrize_by_data_subdirs(
    __file__, "group_advanced_true_invisible_true_field_advanced_true_invisible_false")
def test_group_advanced_true_invisible_true_field_advanced_true_invisible_false(
        sdk_client_fs: ADCMClient, path, app, login):
    """All fields invisible.
    """
    bundle = sdk_client_fs.upload_from_fs(path)
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
    if not config.advanced():
        config.click_advanced()
    assert config.advanced()
    fields = config.get_field_groups()
    group_names = config.get_group_elements()
    assert not group_names
    for field in fields:
        assert not field.is_displayed(), field.get_attribute("class")
