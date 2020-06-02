import os

import pytest
from adcm_pytest_plugin.utils import get_data_dir

# pylint: disable=W0611, W0621
from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.configuration import Configuration
from tests.ui_tests.app.pages import LoginPage

DATADIR = get_data_dir(__file__)
BUNDLES = os.path.join(os.path.dirname(__file__), "../stack/")


@pytest.fixture(scope='function')
def ui_hell_fs(sdk_client_fs):
    bundle = sdk_client_fs.upload_from_fs(DATADIR)
    cluster = bundle.cluster_create(name='my cluster')
    cluster.service_add(name='ui_config_hell')
    service = cluster.service(name="ui_config_hell")
    return service


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
def prototype_display_names(ui_hell_fs):
    display_header_name = ui_hell_fs.display_name
    display_names = {config['display_name'] for config in ui_hell_fs.prototype().config}
    return display_header_name, display_names


@pytest.fixture()
def ui_display_names(login, app, ui_hell_fs):
    ui_config = Configuration(app.driver,
                              "{}/cluster/{}/service/{}/config".format(app.adcm.url,
                                                                       ui_hell_fs.cluster_id,
                                                                       ui_hell_fs.service_id))
    return ui_config.get_display_names()


def test_display_names(prototype_display_names, ui_display_names, screenshot_on_failure):
    """Scenario:
    1. Get Service configuration
    2. Get display names from UI
    3. Check that config name in prototype is correct
    4. Check that in UI we have full list of display names from prototype
    """
    _ = screenshot_on_failure
    assert prototype_display_names[0] == "UI Config Hell"
    for d_name in ui_display_names:
        assert d_name in prototype_display_names[1]
