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
         'float', 'list', 'map', 'json', 'file')

DEFAULT_VALUE = {"string": "default_string",
                 "text": "text",
                 "password": "password",
                 "integer": 4,
                 "float": 4.0,
                 "boolean": True,
                 "json": {},
                 "map": {"name": "Joe", "age": "24", "sex": "m"},
                 "list": ['/dev/rdisk0s1', '/dev/rdisk0s2', '/dev/rdisk0s3'],
                 "file": "./file.txt"}


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
            if data['read_only']:
                sub_config['read_only'] = 'any'
            if data['activatable']:
                cluster_config['activatable'] = True
                cluster_config['active'] = data['active']
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
            if data['read_only']:
                field_config['read_only'] = 'any'
            field_config['ui_options'] = {'invisible': data['ui_options']['invisible'],
                                          'advanced': data['ui_options']['advanced']}
            config_dict['config'] = [field_config]
            config = [config_dict]
            expected_result = generate_config_expected_result(data)
            configs.append((config, expected_result))
    return configs


config_data = generate_config_data()
configs = generate_configs(config_data)

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


@pytest.fixture(scope='module', params=configs)
def data(request):
    config = request.param
    read_only = bool('read_only' in config[0][0]['config'][0].keys())
    default = bool('default' in config[0][0]['config'][0].keys())
    templ = "type_{}_required_{}_ro_{}_content_{}_invisible_{}_advanced_{}"
    config_folder_name = templ.format(
        config[0][0]['config'][0]['type'],
        config[0][0]['config'][0]['required'],
        read_only,
        default,
        config[0][0]['config'][0]['ui_options']['invisible'],
        config[0][0]['config'][0]['ui_options']['advanced'])
    d_name = "{}/configs/fields/{}/{}".format(utils.get_data_dir(__file__),
                                              config[0][0]['config'][0]['type'],
                                              config_folder_name)
    if not os.path.exists(d_name):
        try:
            os.makedirs(d_name)
        except FileExistsError:
            print("Don't create directory")
        if config[0][0]['config'][0]['name'] == 'file':
            with open("{}/file.txt".format(d_name), 'w') as f:
                f.write("test")
        with open("{}/config.yaml".format(d_name), 'w') as yaml_file:
            yaml.dump(config[0], yaml_file)
    return config[0][0], config[1], d_name


@pytest.fixture(scope='module', params=group_configs)
def data_groups(request):
    config = request.param
    if "activatable" in config[0][0]['config'][0].keys():
        activatable = True
        active = config[0][0]['config'][0]['active']
    else:
        activatable = False
        active = False
    data_type = config[0][0]['config'][0]['subs'][0]['type']
    read_only = bool('read_only' in config[0][0]['config'][0]['subs'][0].keys())
    default = bool('default' in config[0][0]['config'][0]['subs'][0].keys())
    if activatable:
        temp = "activatable_{}_active_{}_required_{}_ro_{}_content_{}_group_invisible" \
               "_{}_group_advanced_{}_field_invisible_{}_field_advanced_{}"
        config_folder_name = temp.format(
            activatable,
            active,
            config[0][0]['config'][0]['subs'][0]['required'],
            read_only,
            default,
            config[0][0]['config'][0]['ui_options']['invisible'],
            config[0][0]['config'][0]['ui_options']['advanced'],
            config[0][0]['config'][0]['subs'][0]['ui_options']['invisible'],
            config[0][0]['config'][0]['subs'][0]['ui_options']['advanced'])
        d_name = "{}/configs/activatable_groups/{}/{}".format(utils.get_data_dir(__file__),
                                                              data_type,
                                                              config_folder_name)
    else:
        temp = "required_{}_ro_{}_content_{}_group_invisible" \
               "_{}_group_advanced_{}_field_invisible_{}_field_advanced_{}"
        config_folder_name = temp.format(
            config[0][0]['config'][0]['subs'][0]['required'],
            config[1]['editable'],
            config[1]['content'],
            config[0][0]['config'][0]['ui_options']['invisible'],
            config[0][0]['config'][0]['ui_options']['advanced'],
            config[0][0]['config'][0]['subs'][0]['ui_options']['invisible'],
            config[0][0]['config'][0]['subs'][0]['ui_options']['advanced'])
        d_name = "{}/configs/groups/{}/{}".format(utils.get_data_dir(__file__),
                                                  data_type,
                                                  config_folder_name)

    if not os.path.exists(d_name):
        try:
            os.makedirs(d_name)
        except FileExistsError:
            print("Don't create directory")
        if config[0][0]['config'][0]['subs'][0]['name'] == 'file':
            with open("{}/file.txt".format(d_name), 'w') as f:
                f.write("test")
        with open("{}/config.yaml".format(d_name), 'w') as yaml_file:
            yaml.dump(config[0], yaml_file)
    return config[0][0], config[1], d_name


def test_configs_fields(sdk_client_ms: ADCMClient, data, login, app):
    """Test UI configuration page without groups
    Scenario:
    1. """
    _ = login, app
    config = data[0]
    expected = data[1]
    path = data[2]
    print(config)
    print(expected)
    allure.attach("Cluster configuration", config,
                  allure.attachment_type.TEXT)
    allure.attach('Expected result', expected,
                  allure.attachment_type.TEXT)
    allure.attach.file("/".join([path, 'config.yaml']),
                       attachment_type=allure.attachment_type.YAML)
    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    field_type = config['config'][0]['type']
    app.driver.get("{}/cluster/{}/config".format
                   (app.adcm.url, cluster.cluster_id))
    ui_config = Configuration(app.driver)
    fields = ui_config.get_app_fields()
    save_err_mess = "Correct status for save button {}".format([expected['save']])
    assert expected['save'] == ui_config.save_button_status(), save_err_mess
    if expected['visible']:
        if expected['visible_advanced']:
            assert not fields
            if not ui_config.advanced:
                ui_config.click_advanced()
            assert ui_config.advanced
        fields = ui_config.get_app_fields()
        assert fields, fields
        for field in fields:
            ui_config.assert_field_editable(field, expected['editable'])
        if expected['content']:
            ui_config.assert_field_content_equal(field_type, fields[0],
                                                 config['config'][0]['default'])
        if expected['alerts']:
            ui_config.assert_alerts_presented(field_type)
    else:
        assert not fields


def test_group_configs_field(sdk_client_ms: ADCMClient, data_groups, login, app):
    """Test for configuration fields with groups"""
    _ = login, app
    config = data_groups[0]
    expected = data_groups[1]
    path = data_groups[2]
    print(config)
    print(expected)
    allure.attach("Cluster configuration",
                  config, allure.attachment_type.TEXT)
    allure.attach('Expected result', expected,
                  allure.attachment_type.TEXT)
    allure.attach.file("/".join([path, 'config.yaml']),
                       attachment_type=allure.attachment_type.YAML)

    bundle = sdk_client_ms.upload_from_fs(path)
    cluster_name = path.split("/")[-1]
    cluster = bundle.cluster_create(name=cluster_name)
    field_type = config['config'][0]['subs'][0]['type']
    app.driver.get("{}/cluster/{}/config".format(app.adcm.url, cluster.cluster_id))
    ui_config = Configuration(app.driver)
    groups = ui_config.get_group_elements()
    fields = ui_config.get_app_fields()
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
            fields = ui_config.get_app_fields()
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
            fields = ui_config.get_app_fields()
            assert fields, fields
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
