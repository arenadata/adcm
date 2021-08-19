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

# pylint: disable=redefined-outer-name
import itertools
import os
import shutil

import allure
import pytest
import yaml
from adcm_client.objects import ADCMClient, Service, Host, Cluster, Bundle, Provider
from adcm_pytest_plugin.utils import random_string, get_data_dir

from tests.ui_tests.app.configuration import Configuration
from tests.ui_tests.utils import (
    ClusterDefinition,
    ProviderDefinition,
    HostDefinition,
    ServiceDefinition,
    FieldDefinition,
    GroupDefinition,
    BundleObjectDefinition,
)

pytestmark = [pytest.mark.usefixtures("bundle")]

GROUP_NAME = "group"
CLUSTER_NAME = "cluster"
SERVICE_NAME = "service"
PROVIDER_NAME = "provider"
HOST_NAME = "host"
PROPERTY_NAME = "property"

CONFIG_DATA = {
    "string": "some_string_value",
    "text": "_".join("some_string_value" * 17),
    "integer": 42,
    "boolean": True,
}

CONFIG_USE_GROUP = "CONFIG_USE_GROUP"
CONFIG_USE_ADVANCED = "CONFIG_USE_ADVANCED"

CONFIG_OPTS = [CONFIG_USE_GROUP, CONFIG_USE_ADVANCED]


def _generate_bundle_config(bundle_type, entity_type, prop_types):
    params = []
    ids = []

    for mask in itertools.product([True, False], repeat=len(CONFIG_OPTS)):
        selected_opts = [opt for (i, opt) in enumerate(CONFIG_OPTS) if mask[i]]

        # bundle
        bundle_proto = []
        if bundle_type == "cluster_service":
            bundle_proto.append(ClusterDefinition(name=CLUSTER_NAME, version="0.1-cluster"))
            bundle_proto.append(ServiceDefinition(name=SERVICE_NAME, version="0.1-service"))
        elif bundle_type == "provider_host":
            bundle_proto.append(ProviderDefinition(name=PROVIDER_NAME, version="0.1-provider"))
            bundle_proto.append(HostDefinition(name=HOST_NAME, version="0.1-host"))

        # config
        config_proto = [
            FieldDefinition(prop_type=prop_type, prop_name=f"{prop_type}_{PROPERTY_NAME}")
            for prop_type in prop_types
            if prop_type in ["string", "text", "boolean", "integer"]
        ]  # scalar types

        if "structure" in prop_types:
            struct_property = FieldDefinition(
                prop_type="structure", prop_name=f"structure_{PROPERTY_NAME}"
            )
            struct_property["yspec"] = "struct_conf.yaml"
            config_proto.append(struct_property)

        if CONFIG_USE_GROUP in selected_opts:
            config_proto = [GroupDefinition(name=GROUP_NAME).add_fields(*config_proto)]
        if CONFIG_USE_ADVANCED in selected_opts:
            for k, _ in enumerate(config_proto):
                config_proto[k].set_advanced(True)

        # assign config
        for k, v in enumerate(bundle_proto):
            if v["type"] == entity_type:
                bundle_proto[k]["config"] = config_proto

        ids.append("-".join(selected_opts).lower() if len(selected_opts) > 0 else "default")
        params.append(
            {
                "opts": (selected_opts, prop_types),
                "bundle": BundleObjectDefinition.to_dict(bundle_proto),
            }
        )

    return pytest.mark.parametrize("bundle_content", params, ids=ids, indirect=True)


@pytest.fixture()
def bundle_content(request, tmp_path):
    struct_filename = "struct_conf.yaml"
    struct_path_src = os.path.join(get_data_dir(__file__), struct_filename)
    struct_path_dest = os.path.join(tmp_path, struct_filename)
    shutil.copyfile(
        struct_path_src,
        struct_path_dest,
    )

    bundle_filename = "config.yaml"
    bundle_path = os.path.join(tmp_path, bundle_filename)
    with allure.step("Dump YAML config to file"):
        with open(bundle_path, "w", encoding='utf_8') as stream:
            yaml.dump(request.param["bundle"], stream, sort_keys=False)
            allure.attach.file(
                bundle_path,
                name=bundle_filename,
                attachment_type=allure.attachment_type.YAML,
            )

    yield request.param["opts"], tmp_path

    os.remove(bundle_path)
    os.remove(struct_path_dest)


@pytest.fixture()
def bundle(bundle_content, sdk_client_fs: ADCMClient) -> Bundle:
    """Assume request.param to be path to the bundle"""
    _, bundle_path = bundle_content
    return sdk_client_fs.upload_from_fs(bundle_path)


@pytest.fixture()
def cluster(bundle: Bundle) -> Cluster:
    return bundle.cluster_create(name=CLUSTER_NAME)


@pytest.fixture()
def cluster_config_page(
    app_fs, cluster: Cluster, login_to_adcm_over_api
):  # pylint: disable=unused-argument
    return Configuration(
        app_fs.driver, "{}/cluster/{}/config".format(app_fs.adcm.url, cluster.cluster_id)
    )


@pytest.fixture()
def service(cluster: Cluster) -> Service:
    cluster.service_add(name=SERVICE_NAME)
    return cluster.service(name=SERVICE_NAME)


@pytest.fixture()
# pylint: disable-next=unused-argument
def service_config_page(app_fs, service: Service, login_to_adcm_over_api) -> Configuration:
    return Configuration.from_service(app_fs, service)


@pytest.fixture()
def provider(bundle: Bundle) -> Provider:
    return bundle.provider_create(name=PROVIDER_NAME + random_string())


@pytest.fixture()
# pylint: disable-next=unused-argument
def provider_config_page(app_fs, provider: Provider, login_to_adcm_over_api) -> Configuration:

    return Configuration(
        app_fs.driver,
        "{}/provider/{}/config".format(app_fs.adcm.url, provider.provider_id),
    )


@pytest.fixture()
def host(provider: Provider) -> Host:
    return provider.host_create(fqdn=f"{HOST_NAME}_{random_string()}")


@pytest.fixture()
# pylint: disable-next=unused-argument
def host_config_page(app_fs, host: Host, login_to_adcm_over_api) -> Configuration:
    return Configuration(
        app_fs.driver,
        "{}/host/{}/config".format(app_fs.adcm.url, host.id),
    )


def _get_test_value(value_type):
    return CONFIG_DATA[value_type] if value_type in CONFIG_DATA else None


def _update_config_property(config_page: Configuration, field, field_type: str):
    if field_type in ["string", "text", "integer"]:
        field_input = config_page.get_field_input(field)
        field_input.send_keys(_get_test_value(field_type))
    if field_type == "boolean":
        config_page.get_field_checkbox(field).click()
    if field_type == "structure":
        nested_field = config_page.get_form_field(field)
        field_input = config_page.get_field_input(nested_field)
        # hardcoded field value, see struct_conf.yaml
        field_input.send_keys(_get_test_value("string"))

    assert config_page.save_button_status()


def _test_save_configuration_button(
    config_page: Configuration, prop_types: list, group_name=None, use_advanced=False
):
    if use_advanced:
        config_page.click_advanced()
    if group_name:
        config_page.activate_group_by_name(group_name)

    assert len(config_page.get_app_fields()) == len(prop_types), "Unexpected count of fields"
    with allure.step("Update config properties"):
        for field_type, field in zip(prop_types, config_page.get_app_fields()):
            _update_config_property(config_page, field, field_type)

    config_page.save_configuration()
    config_page.refresh()

    if use_advanced:
        config_page.click_advanced()
    if group_name:
        group = config_page.get_group_by_name(group_name)
        config_page.assert_group_status(group)

    with allure.step("Check config properties values"):
        for field_type, field in zip(prop_types, config_page.get_app_fields()):
            value_to_check = _get_test_value(field_type)
            if field_type == "boolean":
                assert (
                    config_page.get_checkbox_element_status(config_page.get_field_checkbox(field))
                    == value_to_check
                )
            else:
                if field_type == "structure":
                    # workaround
                    field_type = "string"
                    field = config_page.get_form_field(field)
                    value_to_check = _get_test_value(field_type)
                config_page.assert_field_content_equal(field_type, field, value_to_check)


def _get_default_props_list() -> list:
    return [
        "string",
        "text",
        "boolean",
        "integer",
        "structure",
    ]


@_generate_bundle_config(
    bundle_type="cluster_service",
    entity_type="cluster",
    prop_types=_get_default_props_list(),
)
def test_cluster_configuration_save_button(bundle_content, cluster_config_page):
    (selected_opts, prop_types), _ = bundle_content
    _test_save_configuration_button(
        cluster_config_page,
        group_name=GROUP_NAME if CONFIG_USE_GROUP in selected_opts else None,
        use_advanced=CONFIG_USE_ADVANCED in selected_opts,
        prop_types=prop_types,
    )


@_generate_bundle_config(
    bundle_type="cluster_service",
    entity_type="service",
    prop_types=_get_default_props_list(),
)
def test_service_configuration_save_button(bundle_content, service_config_page):
    (selected_opts, prop_types), _ = bundle_content
    _test_save_configuration_button(
        service_config_page,
        group_name=GROUP_NAME if CONFIG_USE_GROUP in selected_opts else None,
        use_advanced=CONFIG_USE_ADVANCED in selected_opts,
        prop_types=prop_types,
    )


@_generate_bundle_config(
    bundle_type="provider_host",
    entity_type="provider",
    prop_types=_get_default_props_list(),
)
def test_provider_configuration_save_button(bundle_content, provider_config_page):
    (selected_opts, prop_types), _ = bundle_content
    _test_save_configuration_button(
        provider_config_page,
        group_name=GROUP_NAME if CONFIG_USE_GROUP in selected_opts else None,
        use_advanced=CONFIG_USE_ADVANCED in selected_opts,
        prop_types=prop_types,
    )


@_generate_bundle_config(
    bundle_type="provider_host",
    entity_type="host",
    prop_types=_get_default_props_list(),
)
def test_host_configuration_save_button(bundle_content, host_config_page):
    (selected_opts, prop_types), _ = bundle_content
    _test_save_configuration_button(
        host_config_page,
        group_name=GROUP_NAME if CONFIG_USE_GROUP in selected_opts else None,
        use_advanced=CONFIG_USE_ADVANCED in selected_opts,
        prop_types=prop_types,
    )
