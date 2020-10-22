# pylint: disable=W0611, W0621, R1702, R0914, R0912, R0915

import allure
import os
import pytest
import tempfile
import yaml

from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import random_string

from .utils import prepare_cluster_and_get_config


PAIR = (True, False)
UI_OPTIONS_PAIRS = ((False, False), (False, True), (True, False))
UI_OPTIONS_PAIRS_GROUPS = [(True, False, True, False),
                           (True, False, False, True),
                           (True, False, False, False),
                           (False, True, True, False),
                           (False, True, False, True),
                           (False, True, False, False),
                           (False, False, True, False),
                           (False, False, False, True),
                           (False, False, False, False)]

FIELDS = []

for ro in True, False:
    for required in True, False:
        for default in True, False:
            if ro and required and not default:
                continue
            FIELDS.append((ro, required, default))

TYPES = ('string', 'password', 'integer', 'text', 'boolean',
         'float', 'list', 'map', 'json', 'file')


DEFAULT_VALUE = {"string": "string",
                 "text": "text",
                 "password": "password",
                 "integer": 4,
                 "float": 4.0,
                 "boolean": True,
                 "json": {},
                 "map": {"name": "Joe", "age": "24", "sex": "m"},
                 "list": ['/dev/rdisk0s1', '/dev/rdisk0s2', '/dev/rdisk0s3'],
                 "file": "./file.txt"}


class ListWithoutRepr(list):
    def __repr__(self):
        return '<%s instance at %#x>' % (self.__class__.__name__, id(self))


def generate_group_data():
    """Generate data set for groups
    :return: list with data
    """
    group_data = []
    for required, default, ro in FIELDS:
        for activatable in PAIR:
            for active in PAIR:
                for ui_options in UI_OPTIONS_PAIRS_GROUPS:
                    if (ui_options[0] or ui_options[2]) and required and not default:
                        continue
                    if activatable and not ui_options[0]:
                        data = {
                            'default': default,
                            "required": required,
                            "activatable": activatable,
                            'active': active,
                            "read_only": ro,
                            "ui_options": {"invisible": ui_options[0],
                                           'advanced': ui_options[1]},
                            "field_ui_options": {"invisible": ui_options[2],
                                                 'advanced': ui_options[3]}}
                    else:
                        data = {
                            'default': default,
                            "required": required,
                            "activatable": False,
                            'active': False,
                            "read_only": ro,
                            "ui_options": {"invisible": ui_options[0],
                                           'advanced': ui_options[1]},
                            "field_ui_options": {"invisible": ui_options[2],
                                                 'advanced': ui_options[3]}}
                    if data not in group_data:
                        group_data.append(data)
    return group_data


def generate_group_expected_result(group_config):
    """Generate expected result for groups

    :param group_config:
    :return: dict with expected result
    """
    expected_result = {'group_visible': not group_config['ui_options']['invisible'],
                       'editable': not group_config['read_only'],
                       "content": group_config['default']}
    if group_config['required'] and not group_config['default']:
        expected_result['alerts'] = True
    else:
        expected_result['alerts'] = False
    group_advanced = group_config['ui_options']['advanced']
    group_invisible = group_config['ui_options']['invisible']
    expected_result['group_visible_advanced'] = (group_advanced and not group_invisible)
    field_advanced = group_config['field_ui_options']['advanced']
    field_invisible = group_config['field_ui_options']['invisible']
    expected_result['field_visible_advanced'] = (field_advanced and not field_invisible)
    expected_result['field_visible'] = not field_invisible
    config_valid = validate_config(group_config['required'],
                                   group_config['default'],
                                   group_config['read_only'])
    expected_result['config_valid'] = config_valid
    invisible = group_invisible or field_invisible
    if group_config['activatable']:
        required = group_config['required']
        default = group_config['default']
        group_active = group_config['active']
        expected_result['field_visible'] = (group_active and not field_invisible)
        expected_result['field_visible_advanced'] = (
            field_advanced and group_active and not field_invisible)
        if group_active and (required and not default):
            expected_result['save'] = False
        else:
            expected_result['save'] = True
        return expected_result
    if invisible or not config_valid:
        expected_result['save'] = False
    else:
        expected_result['save'] = True
    return expected_result


def validate_config(field_required, default_presented, field_ro):
    """

    :param field_required:
    :param default_presented:
    :param field_ro:
    :return:
    """
    if (field_required and not default_presented) or field_ro:
        return False
    return True


def generate_config_data():
    """Generate data set for configs without groups

    :return: list
    """
    data = []
    for default, required, ro in FIELDS:
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
    if config['ui_options']['invisible']:
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
            if data['read_only']:
                sub_config['read_only'] = 'any'
            if data['activatable']:
                cluster_config['activatable'] = True
                cluster_config['active'] = data['active']
            sub_config['ui_options'] = {'invisible': data['field_ui_options']['invisible'],
                                        'advanced': data['field_ui_options']['advanced']}
            cluster_config['subs'] = [sub_config]
            config_dict['config'] = [cluster_config]
            config_dict['name'] = random_string()
            config = ListWithoutRepr([config_dict])
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
                           "name": random_string(),
                           "version": "1",
                           "config": []}
            unsupported_options = all([data['read_only'],
                                       data['required']])
            if not data['default'] and unsupported_options:
                continue
            field_config = {'name': _type, 'type': _type, 'required': data['required']}
            if data['default']:
                field_config['default'] = DEFAULT_VALUE[_type]
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


def prepare_config(config):
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
    temdir = tempfile.mkdtemp()
    d_name = "{}/configs/fields/{}/{}".format(temdir,
                                              config[0][0]['config'][0]['type'],
                                              config_folder_name)

    os.makedirs(d_name)
    if config[0][0]['config'][0]['name'] == 'file':
        with open("{}/file.txt".format(d_name), 'w') as f:
            f.write("test")
    with open("{}/config.yaml".format(d_name), 'w') as yaml_file:
        yaml.dump(config[0], yaml_file)
    return config[0][0], config[1], d_name


def prepare_group_config(config):
    if "activatable" in config[0]['config'][0].keys():
        activatable = True
        active = config[0]['config'][0]['active']
    else:
        activatable = False
        active = False
    data_type = config[0]['config'][0]['subs'][0]['type']
    read_only = bool('read_only' in config[0]['config'][0]['subs'][0].keys())
    default = bool('default' in config[0]['config'][0]['subs'][0].keys())
    temp = "{}_activatab_{}_act_{}_req_{}_ro_{}_cont_{}_grinvis_{}_gradv_{}_fiinvis_{}_fiadv_{}"
    config_folder_name = temp.format(
        data_type,
        activatable,
        active,
        config[0]['config'][0]['subs'][0]['required'],
        read_only,
        default,
        config[0]['config'][0]['ui_options']['invisible'],
        config[0]['config'][0]['ui_options']['advanced'],
        config[0]['config'][0]['subs'][0]['ui_options']['invisible'],
        config[0]['config'][0]['subs'][0]['ui_options']['advanced'])
    temdir = tempfile.mkdtemp()
    d_name = "{}/configs/groups/{}".format(temdir, config_folder_name)
    os.makedirs(d_name)
    if config[0]['config'][0]['subs'][0]['name'] == 'file':
        with open("{}/file.txt".format(d_name), 'w') as f:
            f.write("test")
    with open("{}/config.yaml".format(d_name), 'w') as yaml_file:
        yaml.dump(list(config), yaml_file)
    return config[0], d_name


@pytest.mark.parametrize("config_dict", configs)
def test_configs_fields(sdk_client_fs: ADCMClient, config_dict, app_fs, login_to_adcm):
    """Test UI configuration page without groups. Before start test actions
    we always create configuration and expected result. All logic for test
    expected result in functions before this test function.
    Scenario:
    1. Generate configuration and expected result for test
    2. Upload bundle
    3. Create cluster
    4. Open configuration page
    5. Check save button status
    6. Check field configuration (depends on expected result dict and bundle configuration"""

    data = prepare_config(config_dict)
    config = data[0]
    expected = data[1]
    path = data[2]
    allure.attach.file("/".join([path, 'config.yaml']),
                       attachment_type=allure.attachment_type.YAML,
                       name='config.yaml')
    field_type = config['config'][0]['type']

    _, ui_config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    fields = ui_config.get_app_fields()
    save_err_mess = "Correct status for save button {}".format([expected['save']])
    assert expected['save'] == ui_config.save_button_status(), save_err_mess
    if expected['visible']:
        if expected['visible_advanced']:
            assert not fields, "Config fields presented, expected no"
            if not ui_config.advanced:
                ui_config.click_advanced()
            assert ui_config.advanced, 'Advanced button not clicked'
        fields = ui_config.get_app_fields()
        assert fields, 'No config fields, expected yes'
        for field in fields:
            ui_config.assert_field_editable(field, expected['editable'])
        if expected['content']:
            ui_config.assert_field_content_equal(field_type, fields[0],
                                                 config['config'][0]['default'])
        if expected['alerts']:
            ui_config.assert_alerts_presented(field_type)
    else:
        assert not fields, "Config fields presented, expected no"


@pytest.mark.parametrize("config_dict,expected_results", group_configs)
def test_group_configs_field(sdk_client_fs: ADCMClient, config_dict, expected_results,
                             app_fs, login_to_adcm):
    """Test for configuration fields with groups. Before start test actions
    we always create configuration and expected result. All logic for test
    expected result in functions before this test function. If we have
    advanced fields inside configuration and group visible we check
    field and group status after clicking advanced button. For activatable
    groups we don't change group status. We have two types of tests for activatable
    groups: the first one when group is active and the second when group not active.
    Scenario:
    1. Generate configuration and expected result for test
    2. Upload bundle
    3. Create cluster
    4. Open configuration page
    5. Check save button status
    6. Check field configuration (depends on expected result dict and bundle configuration)"""

    data = prepare_group_config(config_dict)
    config = data[0]
    expected = expected_results
    path = data[1]
    allure.attach.file("/".join([path, 'config.yaml']),
                       attachment_type=allure.attachment_type.YAML,
                       name='config.yaml')

    field_type = config['config'][0]['subs'][0]['type']

    _, ui_config = prepare_cluster_and_get_config(sdk_client_fs, path, app_fs)

    groups = ui_config.get_group_elements()
    fields = ui_config.get_app_fields()
    save_err_mess = "Correct status for save button {}".format([expected['save']])
    assert expected['save'] == ui_config.save_button_status(), save_err_mess
    if expected['group_visible'] and not expected['field_visible']:
        if expected['group_visible_advanced']:
            assert not groups, 'Groups presented, expected no'
            assert not fields, 'Fields presented, expected no'
            if not ui_config.advanced:
                ui_config.click_advanced()
            assert ui_config.advanced, 'Advanced button not clicked'
        groups = ui_config.get_group_elements()
        fields = ui_config.get_app_fields()
        assert groups, "Groups not presented, expected yes"
        for field in fields:
            assert not field.is_displayed()
        if "activatable" in config['config'][0].keys():
            ui_config.assert_group_status(groups[0], config['config'][0]['active'])

    if expected['group_visible'] and expected['field_visible']:
        if expected['field_visible_advanced'] or expected['group_visible_advanced']:
            assert not fields, 'Fields presented, expected no'
            if not ui_config.advanced:
                ui_config.click_advanced()
            assert ui_config.advanced, 'Advanced button not clicked'
        groups = ui_config.get_group_elements()
        fields = ui_config.get_app_fields()
        assert groups, "Groups not presented, expected yes"
        assert fields, "Fields not presented, expected yes"
        for field in fields:
            ui_config.assert_field_editable(field, expected['editable'])
        if expected['content']:
            default_value = config['config'][0]['subs'][0]['default']
            ui_config.assert_field_content_equal(field_type, fields[0], default_value)
        if expected['alerts']:
            ui_config.assert_alerts_presented(field_type)
        if "activatable" in config['config'][0].keys():
            ui_config.assert_group_status(groups[0], config['config'][0]['active'])
    if not expected['group_visible']:
        assert not groups, 'Groups presented, expected no'
        if not ui_config.advanced:
            ui_config.click_advanced()
        assert ui_config.advanced, 'Advanced button not clicked'
        groups = ui_config.get_group_elements()
        assert not groups, "Groups presented, expected no"
