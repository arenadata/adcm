# pylint: disable=W0621

import allure
import pytest
from adcm_client.objects import ADCMClient, Service, Host, Cluster, Bundle, Provider
from adcm_pytest_plugin.utils import get_data_subdirs_as_parameters, random_string

from tests.ui_tests.app.configuration import Configuration
from tests.ui_tests.app.locators import Common


GROUP_NAME = "test_group"
CLUSTER_NAME = "test_cluster"
SERVICE_NAME = "test_service"
PROVIDER_NAME = "test_provider"
HOST_NAME = "test_host"


@pytest.fixture()
@allure.step("Uploading bundle")
def bundle(request, sdk_client_fs: ADCMClient) -> Bundle:
    """Assume request.param to be path to the bundle"""
    return sdk_client_fs.upload_from_fs(request.param)


@pytest.fixture()
def cluster(bundle: Bundle) -> Cluster:
    return bundle.cluster_create(name=CLUSTER_NAME)


@pytest.fixture()
def cluster_config_ui(app_fs, cluster: Cluster):
    return Configuration(
        app_fs.driver,
        "{}/cluster/{}/config".format(
            app_fs.adcm.url, cluster.cluster_id
        )
    )


@pytest.fixture()
@allure.step("Prepare cluster with service")
def service(cluster: Cluster, sdk_client_fs: ADCMClient) -> Service:
    cluster.service_add(name=SERVICE_NAME)
    return cluster.service(name=SERVICE_NAME)


@pytest.fixture()
@allure.step("Retrieving service configuration from UI")
def service_config_ui(app_fs, service: Service) -> Configuration:
    return Configuration(
        app_fs.driver,
        "{}/cluster/{}/service/{}/config".format(
            app_fs.adcm.url, service.cluster_id, service.id
        ),
    )


@pytest.fixture()
def provider(bundle: Bundle):
    return bundle.provider_create(name=PROVIDER_NAME + random_string())


@pytest.fixture()
def provider_config_ui(app_fs, provider: Provider) -> Configuration:
    return Configuration(
        app_fs.driver,
        "{}/provider/{}/config".format(
            app_fs.adcm.url, provider.provider_id
        ),
    )


@pytest.fixture()
@allure.step("Uploading bundle, creating provider and host")
def host(provider: Provider) -> Host:
    return provider.host_create(fqdn=HOST_NAME + random_string())


@pytest.fixture()
def host_config_ui(app_fs, host: Host) -> Configuration:
    return Configuration(
        app_fs.driver,
        "{}/host/{}/config".format(app_fs.adcm.url, host.id),
    )


def _get_field_input(field):
    return field.find_element(*Common.mat_input_element)


def _get_group_field_with_input(config: Configuration, group):
    field = config.get_form_field(group)
    field_input = _get_field_input(field)
    return field, field_input


def _get_form_field_with_input(config: Configuration):
    field = config.get_app_fields()[0]
    field_input = _get_field_input(field)
    return field, field_input


@allure.step("Update config property value")
def _update_config_property_check(
    config: Configuration, get_field_with_input, value, group_name=None
):
    args = [config]
    if group_name:
        group = config.get_group_by_name(group_name)
        args.append(group)

    _, field_input = get_field_with_input(*args)
    field_input.send_keys(value)

    assert config.save_button_status()
    config.save_configuration()


@allure.step("Check config property value")
def _check_config_property_value(
    config: Configuration, get_field_with_input, value, group_name=None
):
    args = [config]
    if group_name:
        group = config.get_group_by_name(group_name)
        config.assert_group_status(group)
        args.append(group)

    field, _ = get_field_with_input(*args)
    config.assert_field_content_equal(type(value), field, value)


def _test_save_configuration_button(config: Configuration, group_name=None):
    # button enabled when group is presented and disabled otherwise
    assert config.save_button_status() == (group_name is not None)

    if group_name:
        config.activate_group_by_name(group_name)
        assert not config.save_button_status()

    get_field_with_input = (
        _get_group_field_with_input if group_name else _get_form_field_with_input
    )

    value_to_check = random_string()
    _update_config_property_check(
        config, get_field_with_input, value_to_check, group_name
    )
    config.refresh()
    _check_config_property_value(
        config, get_field_with_input, value_to_check, group_name
    )


@pytest.mark.parametrize(
    "bundle",
    get_data_subdirs_as_parameters(__file__, "cluster_config", "with_switch")[0],
    indirect=True,
)
@pytest.mark.usefixtures("login_to_adcm")
def test_save_configuration_button_on_cluster_with_switch(cluster_config_ui, bundle):
    """UI autotest for cluster config 'Save' action under switched section"""
    _test_save_configuration_button(cluster_config_ui, GROUP_NAME)


@pytest.mark.parametrize(
    "bundle",
    get_data_subdirs_as_parameters(__file__, "cluster_config", "without_switch")[0],
    indirect=True,
)
@pytest.mark.usefixtures("login_to_adcm")
def test_save_configuration_button_on_cluster_without_switch(cluster_config_ui, bundle):
    """UI autotest for cluster config 'Save' action"""
    _test_save_configuration_button(cluster_config_ui)


@pytest.mark.parametrize(
    "bundle",
    get_data_subdirs_as_parameters(__file__, "service_config", "with_switch")[0],
    indirect=True,
)
@pytest.mark.usefixtures("login_to_adcm")
def test_save_configuration_button_on_service_with_switch(service_config_ui, bundle):
    """UI autotest for service config 'Save' action under switched section"""
    _test_save_configuration_button(service_config_ui, GROUP_NAME)


@pytest.mark.parametrize(
    "bundle",
    get_data_subdirs_as_parameters(__file__, "service_config", "without_switch")[0],
    indirect=True,
)
@pytest.mark.usefixtures("login_to_adcm")
def test_save_configuration_button_on_service_without_switch(service_config_ui, bundle):
    """UI autotest for service config 'Save' action"""
    _test_save_configuration_button(service_config_ui)


@pytest.mark.parametrize(
    "bundle",
    get_data_subdirs_as_parameters(__file__, "provider_config", "with_switch")[0],
    indirect=True,
)
@pytest.mark.usefixtures("login_to_adcm")
def test_save_configuration_button_on_provider_with_switch(provider_config_ui, bundle):
    """UI autotest for provider config 'Save' action under switched section"""
    _test_save_configuration_button(provider_config_ui, GROUP_NAME)


@pytest.mark.parametrize(
    "bundle",
    get_data_subdirs_as_parameters(__file__, "provider_config", "without_switch")[0],
    indirect=True,
)
@pytest.mark.usefixtures("login_to_adcm")
def test_save_configuration_button_on_provider_without_switch(provider_config_ui, bundle):
    """UI autotest for provider config 'Save' action"""
    _test_save_configuration_button(provider_config_ui)


@pytest.mark.parametrize(
    "bundle",
    get_data_subdirs_as_parameters(__file__, "host_config", "with_switch")[0],
    indirect=True,
)
@pytest.mark.usefixtures("login_to_adcm")
def test_save_configuration_button_on_host_with_switch(host_config_ui, bundle):
    """UI autotest for host config 'Save' action under switched section"""
    _test_save_configuration_button(host_config_ui, GROUP_NAME)


# will be possible after changes in adcm_pytest_plugin
# @parametrize_by_data_subdirs(
#     __file__,
#     "host_config", "without_switch",
#     param_name="host",
#     indirect=True
# )
@pytest.mark.parametrize(
    "bundle",
    get_data_subdirs_as_parameters(__file__, "host_config", "without_switch")[0],
    indirect=True,
)
@pytest.mark.usefixtures("login_to_adcm")
def test_save_configuration_button_on_host_without_switch(host_config_ui, bundle):
    """UI autotest for host config 'Save' action"""
    _test_save_configuration_button(host_config_ui)
