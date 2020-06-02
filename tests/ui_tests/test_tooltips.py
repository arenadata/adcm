import os

import pytest
from adcm_pytest_plugin.utils import get_data_dir

# pylint: disable=W0611, W0621
from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.configuration import Configuration
from tests.ui_tests.app.pages import LoginPage

DATADIR = get_data_dir(__file__)
BUNDLES = os.path.join(os.path.dirname(__file__), "../stack/")

NO_TOOLTIP_FIELDS = ['string_required_by_default_without_type',
                     'string_read_only_any_without_type']


@pytest.fixture(scope='function')
def service(sdk_client_fs):
    bundle = sdk_client_fs.upload_from_fs(DATADIR)
    cluster = bundle.cluster_create(name='tooltips')
    cluster.service_add(name='tooltips_test')
    return cluster.service(name="tooltips_test")


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


@pytest.fixture()
def ui_config(app, login, service):
    return Configuration(app.driver,
                         "{}/cluster/{}/service/{}/config".format(app.adcm.url,
                                                                  service.cluster_id,
                                                                  service.service_id)
                         )


@pytest.fixture()
def tooltips(ui_config, service):
    config = service.prototype().config
    descriptions = [field['description'] for field in config[1:] if field['description'] != ""]
    app_fields = ui_config.get_app_fields()
    tooltips = []
    for app_field in app_fields:
        ttip = app_field.text.split(":")[0]
        if ttip in descriptions and ttip != "":
            tooltips.append(ui_config.get_tooltip_text_for_element(app_field))
    return tooltips, descriptions


def test_tooltip_presented(tooltips, screenshot_on_failure):
    """Check that field have description tooltip presented
    """
    _ = screenshot_on_failure
    assert len(tooltips[0]) == 8


@pytest.mark.xfail
def test_tooltip_text(tooltips):
    """Check description in tooltip
    """
    assert set(tooltips[0]).issubset(set(tooltips[1]))


@pytest.mark.parametrize("field", NO_TOOLTIP_FIELDS)
def test_tooltip_not_presented(field, ui_config, screenshot_on_failure):
    """Check that we haven't tooltip for fields without description
    """
    _ = screenshot_on_failure
    textboxes = ui_config.get_textboxes()
    for textbox in textboxes:
        if field == textbox.text.split(":")[0]:
            assert not ui_config.check_tooltip_for_field(textbox)
