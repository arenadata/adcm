# pylint: disable=W0611, W0621, R1702, R0914, R0912, R0915

import allure
import os
import pytest
import yaml

from adcm_client.objects import ADCMClient


from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.pages import Configuration, LoginPage

from adcm_pytest_plugin import utils


PAIR = (True, False)
UI_OPTIONS_PAIRS = ((True, True), (False, False), (False, True), (True, False))
TYPES = ('string', 'password', 'integer', 'text', 'boolean',
         'float', 'list', 'map', 'json', 'file', 'structure')

DEFAULT_VALUE = {"string": "default_string",
                 "text": "text",
                 "password": "password",
                 "integer": 4,
                 "float": 4.0,
                 "boolean": True,
                 "json": {},
                 "map": {"name": "Joe", "age": "24", "sex": "m"},
                 "option": 80,
                 "list": ['/dev/rdisk0s1', '/dev/rdisk0s2', '/dev/rdisk0s3'],
                 "structure": [{"country": "Greece", "code": 38},
                               {"country": "France", "code": 33},
                               {"country": "Spain", "code": 34}],
                 "file": "./file.txt"}

schema_yaml = """---
root:
  match: list
  item: country_code

country_code:
  match: dict
  items:
    country: string
    code: integer

string:
  match: string

integer:
  match: int"""


def generate_group_data():
    """Generate data set for groups
    :return: list with data
    """
    group_data = []
    for default in PAIR:
        for required in PAIR:
            for ro in PAIR:
                for activatable in PAIR:
                    for active in PAIR:
                        for ui_options in UI_OPTIONS_PAIRS:
                            for field_ui_options in UI_OPTIONS_PAIRS:
                                group_data.append({
                                    'default': default, "required": required,
                                    "activatable": activatable, 'active': active,
                                    "read_only": ro,
                                    "ui_options": {"invisible": ui_options[0],
                                                   'advanced': ui_options[1]},
                                    "field_ui_options": {"invisible": field_ui_options[0],
                                                         'advanced': field_ui_options[1]}})
    return group_data


def generate_group_expected_result(group_config):
    """Generate expected result for groups

    :param group_config:
    :return: dict with expected result
    """
    expected_result = {'group_visible': not group_config['ui_options']['invisible'],
                       'field_visible': not group_config['field_ui_options']['invisible'],
                       'editable': not group_config['read_only'],
                       "content": group_config['default']}
    if group_config['required'] and not group_config['default']:
        expected_result['save'] = False
        expected_result['alerts'] = True
    else:
        expected_result['save'] = True
        expected_result['alerts'] = False
    if group_config['read_only']:
        expected_result['save'] = False
    if group_config['ui_options']['advanced'] and not group_config['ui_options']['invisible']:
        expected_result['group_visible_advanced'] = True
    else:
        expected_result['group_visible_advanced'] = False
    field_advanced = group_config['field_ui_options']['advanced']
    if field_advanced and not group_config['field_ui_options']['invisible']:
        expected_result['field_visible_advanced'] = True
    else:
        expected_result['field_visible_advanced'] = False
    return expected_result


def generate_config_data():
    """Generate data set for configs without groups

    :return: list
    """
    data = []
    for default in PAIR:
        for required in PAIR:
            for ro in PAIR:
                for ui_options in UI_OPTIONS_PAIRS:
                    data.append({'default': default, "required": required,
                                 "read_only": ro, "ui_options": {"invisible": ui_options[0],
                                                                 'advanced': ui_options[1]}})
    return data


def generate_config_expected_result(config):
    """Generate expected result for config

    :param config:
    :return: dict with expected result
    """
    expected_result = {'visible': not config['ui_options']['invisible'],
                       'editable': not config['read_only'],
                       "content": config['default']}
    if config['required'] and not config['default']:
        expected_result['save'] = False
        expected_result['alerts'] = True
    else:
        expected_result['save'] = True
        expected_result['alerts'] = False
    if config['read_only']:
        expected_result['save'] = False
    if config['ui_options']['advanced'] and not config['ui_options']['invisible']:
        expected_result['visible_advanced'] = True
    else:
        expected_result['visible_advanced'] = False
    return expected_result


def generate_group_configs(group_config_data):
    """Generate ADCM config dictionaries for groups

    :param group_config_data:
    :return:
    """
    group_configs = []
    for _type in TYPES:
        for data in group_config_data:
            config_dict = {"type": "cluster",
                           "version": "1",
                           "config": []}
            unsupported_options = all([data['read_only'],
                                       data['required']])
            if not data['default'] and unsupported_options:
                continue
            cluster_config = {"name": "group",
                              "type": "group",
                              'ui_options': {"invisible": data['ui_options']['invisible'],
                                             'advanced': data['ui_options']['advanced']}}
            sub_config = {'name': _type, 'type': _type, 'required': data['required']}
            if data['default']:
                sub_config['default'] = DEFAULT_VALUE[_type]
            if _type == 'option':
                sub_config['option'] = {"http": 80, "https": 443}
            elif _type == 'structure':
                sub_config['yspec'] = "./schema.yaml"
            if data['read_only']:
                sub_config['read_only'] = 'any'
            sub_config['ui_options'] = {'invisible': data['field_ui_options']['invisible'],
                                        'advanced': data['field_ui_options']['advanced']}
            cluster_config['subs'] = [sub_config]
            config_dict['config'] = [cluster_config]
            config_dict['name'] = utils.random_string()
            config = [config_dict]
            expected_result = generate_group_expected_result(data)
            group_configs.append((config, expected_result))
    return group_configs


def generate_configs(config_data):
    """Generate ADCM config dictionaries for fields

    :param config_data:
    :return:
    """
    configs = []
    for _type in TYPES:
        for data in config_data:
            config_dict = {"type": "cluster",
                           "name": utils.random_string(),
                           "version": "1",
                           "config": []}
            unsupported_options = all([data['read_only'],
                                       data['required']])
            if not data['default'] and unsupported_options:
                continue
            field_config = {'name': _type, 'type': _type, 'required': data['required']}
            if data['default']:
                field_config['default'] = DEFAULT_VALUE[_type]
            if _type == 'option':
                field_config['option'] = {"http": 80, "https": 443}
            elif _type == 'structure':
                field_config['yspec'] = "./schema.yaml"
            if data['read_only']:
                field_config['read_only'] = 'any'
            field_config['ui_options'] = {'invisible': data['ui_options']['invisible'],
                                          'advanced': data['ui_options']['advanced']}
            config_dict['config'] = [field_config]
            config = [config_dict]
            expected_result = generate_config_expected_result(data)
            configs.append((config, expected_result))
    print(len(configs))
    return configs


def prepare_test_config_parameters(configs):
    """Create directory for configs and dump config dict to yaml file

    :return:
    """
    parameters = []
    for config in configs:
        config_folder_name = utils.random_string()
        d_name = "{}/configs/{}".format(utils.get_data_dir(__file__), config_folder_name)
        os.makedirs(d_name)
        if config[0][0]['config'][0]['name'] == 'file':
            with open("{}/file.txt".format(d_name), 'w') as f:
                f.write("test")
        if config[0][0]['config'][0]['name'] == 'structure':
            with open("{}/schema.yaml".format(d_name), 'w') as f:
                f.write(schema_yaml)
        with open("{}/config.yaml".format(d_name), 'w') as yaml_file:
            yaml.dump(config[0], yaml_file)
        parameters.append((config[0][0], config[1], d_name))
    return pytest.mark.parametrize("config, expected, path", parameters)


def prepare_test_group_config_parameters(group_configs):
    """Create directory for group configs and dump config dict to yaml file

    :param group_configs:
    :return: pytest parametrize object
    """
    parameters = []
    for config in group_configs:
        config_folder_name = utils.random_string()
        d_name = "{}/configs/{}".format(utils.get_data_dir(__file__), config_folder_name)
        os.makedirs(d_name)
        if config[0][0]['config'][0]['subs'][0]['name'] == 'file':
            with open("{}/file.txt".format(d_name), 'w') as f:
                f.write("test")
        if config[0][0]['config'][0]['subs'][0]['name'] == 'structure':
            with open("{}/schema.yaml".format(d_name), 'w') as f:
                f.write(schema_yaml)
        with open("{}/config.yaml".format(d_name), 'w') as yaml_file:
            yaml.dump(config[0], yaml_file)
        parameters.append((config[0][0], config[1], d_name))
    return pytest.mark.parametrize("config, expected, path", parameters)


config_data = generate_config_data()
configs = generate_configs(config_data)
print(len(configs))

group_configs_data = generate_group_data()
group_configs = generate_group_configs(group_configs_data)


@pytest.fixture(scope='module')
def app(adcm_ms):
    return ADCMTest(adcm_ms)


@pytest.fixture(scope='module')
def login(app):
    app.driver.get(app.adcm.url)
    login = LoginPage(app.driver)
    login.login("admin", "admin")


@prepare_test_config_parameters(configs)
def test_configs_fields(sdk_client_ms: ADCMClient, config,
                        expected, path, login, app):
    """Test UI configuration page without groups
    Scenario:
    1. """
    print(config)
    print(expected)
    _ = login, app
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    field_type = config['config'][0]['type']
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    ui_config = Configuration(app.driver)
    fields = ui_config.get_fields_by_type(field_type)
    save_err_mess = "Correct status for save button {}".format([expected['save']])
    assert expected['save'] == ui_config.save_button_status(), save_err_mess
    if expected['visible']:
        if expected['visible_advanced']:
            assert not fields
            if not ui_config.advanced:
                ui_config.click_advanced()
            assert ui_config.advanced
        fields = ui_config.get_fields_by_type(field_type)
        assert len(fields) == 1, fields
        for field in fields:
            ui_config.assert_field_editable(field, expected['editable'])
        if expected['content']:
            ui_config.assert_field_content_equal(field_type, fields[0],
                                                 config['config'][0]['default'])
        if expected['alerts']:
            ui_config.assert_alerts_presented(field_type)
    else:
        assert not fields
    allure.attach("Cluster configuration", config,
                  allure.attachment_type.TEXT)
    allure.attach('Expected result', expected,
                  allure.attachment_type.TEXT)
    allure.attach.file("/".join([path, 'config.yaml']),
                       attachment_type=allure.attachment_type.YAML)


@prepare_test_group_config_parameters(group_configs)
def test_group_configs_field(sdk_client_ms: ADCMClient, config, expected, path, login, app):
    """Test for configuration fields with groups"""
    _ = login, app
    print(config)
    print(expected)
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    field_type = config['config'][0]['subs'][0]['type']
    app.driver.get("{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
    ui_config = Configuration(app.driver)
    groups = ui_config.get_group_elements()
    fields = ui_config.get_fields_by_type(field_type)
    save_err_mess = "Correct status for save button {}".format([expected['save']])
    assert expected['save'] == ui_config.save_button_status(), save_err_mess
    if expected['group_visible']:
        if expected['group_visible_advanced']:
            assert not groups
            assert not fields
            if not ui_config.advanced:
                ui_config.click_advanced()
                assert ui_config.advanced
            groups = ui_config.get_group_elements()
            assert groups, groups
            fields = ui_config.get_fields_by_type(field_type)
            if expected['field_visible_advanced']:
                assert fields, fields
            else:
                assert not fields, fields
        if expected['field_visible']:
            if expected['field_visible_advanced']:
                if not ui_config.advanced:
                    assert not fields
                    ui_config.click_advanced()
                else:
                    ui_config.click_advanced()
                    fields = ui_config.get_field_groups()
                    assert not fields
                    ui_config.click_advanced()
                assert ui_config.advanced
            fields = ui_config.get_fields_by_type(field_type)
            assert len(fields) == 1, fields
            for field in fields:
                ui_config.assert_field_editable(field, expected['editable'])
            if expected['content']:
                default_value = config['config'][0]['subs'][0]['default']
                ui_config.assert_field_content_equal(field_type, fields[0], default_value)
            if expected['alerts']:
                ui_config.assert_alerts_presented(field_type)
        if not expected['field_visible']:
            assert not fields, fields
    elif expected['group_visible'] and not expected['field_visible']:
        assert groups
        assert not fields
    elif not expected['group_visible']:
        assert not groups
        assert not fields
    allure.attach("Cluster configuration",
                  config, allure.attachment_type.TEXT)
    allure.attach('Expected result', expected,
                  allure.attachment_type.TEXT)
    allure.attach.file("/".join([path, 'config.yaml']),
                       attachment_type=allure.attachment_type.YAML)
