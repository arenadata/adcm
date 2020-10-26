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

import os
import re

import json
import yaml
import toml
import hashlib
import yspec.checker

from rest_framework import status

from cm.logger import log
from cm.errors import raise_AdcmEx as err
from cm.adcm_config import proto_ref, check_config_type, type_is_complex, read_bundle_file
from cm.models import StagePrototype, StageComponent, StageAction, StagePrototypeConfig
from cm.models import ACTION_TYPE, SCRIPT_TYPE, CONFIG_FIELD_TYPE, PROTO_TYPE
from cm.models import StagePrototypeExport, StagePrototypeImport, StageUpgrade, StageSubAction


NAME_REGEX = r'[0-9a-zA-Z_\.-]+'
MAX_NAME_LENGTH = 256


def save_definition(path, fname, conf, obj_list, bundle_hash, adcm=False):
    if isinstance(conf, dict):
        save_object_definition(path, fname, conf, obj_list, bundle_hash, adcm)
    else:
        for obj_def in conf:
            save_object_definition(path, fname, obj_def, obj_list, bundle_hash, adcm)


def cook_obj_id(conf):
    return '{}.{}.{}'.format(conf['type'], conf['name'], conf['version'])


def save_object_definition(path, fname, conf, obj_list, bundle_hash, adcm=False):
    if not isinstance(conf, dict):
        msg = 'Object definition should be a map ({})'
        return err('INVALID_OBJECT_DEFINITION', msg.format(fname))

    if 'type' not in conf:
        msg = 'No type in object definition: {}'
        return err('INVALID_OBJECT_DEFINITION', msg.format(fname))

    def_type = conf['type']
    if def_type not in (proto_type for (proto_type, _) in PROTO_TYPE):
        msg = 'Unknown type "{}" in object definition: {}'
        return err('INVALID_OBJECT_DEFINITION', msg.format(def_type, fname))

    if def_type == 'adcm' and not adcm:
        msg = 'Invalid type "{}" in object definition: {}'
        return err('INVALID_OBJECT_DEFINITION', msg.format(def_type, fname))

    check_object_definition(fname, conf, def_type, obj_list)
    obj = save_prototype(path, conf, def_type, bundle_hash)
    log.info('Save definition of %s "%s" %s to stage', def_type, conf['name'], conf['version'])
    obj_list[cook_obj_id(conf)] = fname
    return obj


def check_object_definition(fname, conf, def_type, obj_list):
    if 'name' not in conf:
        msg = 'No name in {} definition: {}'
        err('INVALID_OBJECT_DEFINITION', msg.format(def_type, fname))
    if 'version' not in conf:
        msg = 'No version in {} "{}" definition: {}'
        err('INVALID_OBJECT_DEFINITION', msg.format(def_type, conf['name'], fname))
    ref = '{} "{}" {}'.format(def_type, conf['name'], conf['version'])
    if cook_obj_id(conf) in obj_list:
        msg = 'Duplicate definition of {} (file {})'
        err('INVALID_OBJECT_DEFINITION', msg.format(ref, fname))
    allow = (
        'type', 'name', 'version', 'display_name', 'description', 'actions', 'components',
        'config', 'upgrade', 'export', 'import', 'required', 'shared', 'monitoring',
        'adcm_min_version', 'edition', 'license',
    )
    check_extra_keys(conf, allow, ref)


def check_extra_keys(conf, acceptable, ref):
    if not isinstance(conf, dict):
        return
    for key in conf.keys():
        if key not in acceptable:
            msg = 'Not allowed key "{}" in {} definition'
            err('INVALID_OBJECT_DEFINITION', msg.format(key, ref))


def get_config_files(path, bundle_hash):
    conf_list = []
    conf_types = [
        ('config.yaml', 'yaml'),
        ('config.yml', 'yaml'),
        ('config.toml', 'toml'),
        ('config.json', 'json'),
    ]
    if not os.path.isdir(path):
        return err(
            'STACK_LOAD_ERROR',
            'no directory: {}'.format(path),
            status.HTTP_404_NOT_FOUND
        )
    for root, _, files in os.walk(path):
        for conf_file, conf_type in conf_types:
            if conf_file in files:
                dirs = root.split('/')
                path = os.path.join('', *dirs[dirs.index(bundle_hash) + 1:])
                conf_list.append((path, root + '/' + conf_file, conf_type))
                break
    if not conf_list:
        msg = 'no config files in stack directory "{}"'
        return err('STACK_LOAD_ERROR', msg.format(path))
    return conf_list


def read_definition(conf_file, conf_type):
    parsers = {
        'toml': toml.load,
        'yaml': yaml.safe_load,
        'json': json.load
    }
    fn = parsers[conf_type]
    if os.path.isfile(conf_file):
        with open(conf_file) as fd:
            try:
                conf = fn(fd)
            except (toml.TomlDecodeError, IndexError) as e:
                err('STACK_LOAD_ERROR', 'TOML decode "{}" error: {}'.format(conf_file, e))
            except yaml.parser.ParserError as e:
                err('STACK_LOAD_ERROR', 'YAML decode "{}" error: {}'.format(conf_file, e))
            except yaml.composer.ComposerError as e:
                err('STACK_LOAD_ERROR', 'YAML decode "{}" error: {}'.format(conf_file, e))
            except yaml.constructor.ConstructorError as e:
                err('STACK_LOAD_ERROR', 'YAML decode "{}" error: {}'.format(conf_file, e))
            except yaml.scanner.ScannerError as e:
                err('STACK_LOAD_ERROR', 'YAML decode "{}" error: {}'.format(conf_file, e))
        log.info('Read config file: "%s"', conf_file)
        return conf
    log.warning('Can not open config file: "%s"', conf_file)
    return {}


def get_license_hash(proto, conf, bundle_hash):
    if 'license' not in conf:
        return None
    if not isinstance(conf['license'], str):
        err('INVALID_OBJECT_DEFINITION', 'license should be a string ({})'.format(proto_ref(proto)))
    msg = 'license file'
    body = read_bundle_file(proto, conf['license'], bundle_hash, msg)
    sha1 = hashlib.sha256()
    sha1.update(body.encode('utf-8'))
    return sha1.hexdigest()


def save_prototype(path, conf, def_type, bundle_hash):
    # validate_name(type_name, '{} type name "{}"'.format(def_type, conf['name']))
    proto = StagePrototype(name=conf['name'], type=def_type, path=path, version=conf['version'])
    dict_to_obj(conf, 'required', proto)
    dict_to_obj(conf, 'shared', proto)
    dict_to_obj(conf, 'monitoring', proto)
    dict_to_obj(conf, 'display_name', proto)
    dict_to_obj(conf, 'description', proto)
    dict_to_obj(conf, 'adcm_min_version', proto)
    dict_to_obj(conf, 'edition', proto)
    fix_display_name(conf, proto)
    license_hash = get_license_hash(proto, conf, bundle_hash)
    if license_hash:
        proto.license_path = conf['license']
        proto.license_hash = license_hash
    proto.save()
    save_actions(proto, conf, bundle_hash)
    save_upgrade(proto, conf)
    save_components(proto, conf)
    save_prototype_config(proto, conf, bundle_hash)
    save_export(proto, conf)
    save_import(proto, conf)
    return proto


def check_component_constraint_definition(proto, name, conf):
    if not isinstance(conf, dict):
        return
    if 'constraint' not in conf:
        return
    const = conf['constraint']
    ref = proto_ref(proto)

    def check_item(item):
        if isinstance(item, int):
            return
        elif item == '+':
            return
        elif item == 'odd':
            return
        else:
            msg = 'constraint item of component "{}" in {} should be only digit or "+" or "odd"'
            err('INVALID_COMPONENT_DEFINITION', msg.format(name, ref))

    if not isinstance(const, list):
        msg = 'constraint of component "{}" in {} should be array'
        err('INVALID_COMPONENT_DEFINITION', msg.format(name, ref))
    if len(const) > 2:
        msg = 'constraint of component "{}" in {} should have only 1 or 2 elements'
        err('INVALID_COMPONENT_DEFINITION', msg.format(name, ref))

    check_item(const[0])
    if len(const) > 1:
        check_item(const[1])


def check_component_requires(proto, name, conf):
    if not isinstance(conf, dict):
        return
    if 'requires' not in conf:
        return
    req = conf['requires']
    ref = proto_ref(proto)
    if not isinstance(req, list):
        msg = 'requires of component "{}" in {} should be array'
        err('INVALID_COMPONENT_DEFINITION', msg.format(name, ref))
    for item in req:
        check_extra_keys(item, ('service', 'component'), f'requires of component "{name}" of {ref}')


def save_components(proto, conf):
    ref = proto_ref(proto)
    if not in_dict(conf, 'components'):
        return
    if proto.type != 'service':
        log.warning('%s has unexpected "components" key', ref)
        return
    if not isinstance(conf['components'], dict):
        msg = 'Components definition should be a map ({})'
        err('INVALID_COMPONENT_DEFINITION', msg.format(ref))
    for comp_name in conf['components']:
        cc = conf['components'][comp_name]
        err_msg = 'Component name "{}" of {}'.format(comp_name, ref)
        validate_name(comp_name, err_msg)
        allow = ('display_name', 'description', 'params', 'constraint', 'requires', 'monitoring')
        check_extra_keys(cc, allow, 'component "{}" of {}'.format(comp_name, ref))
        component = StageComponent(prototype=proto, name=comp_name)
        dict_to_obj(cc, 'description', component)
        dict_to_obj(cc, 'display_name', component)
        dict_to_obj(cc, 'monitoring', component)
        fix_display_name(cc, component)
        check_component_constraint_definition(proto, comp_name, cc)
        check_component_requires(proto, comp_name, cc)
        dict_to_obj(cc, 'params', component)
        dict_to_obj(cc, 'constraint', component)
        dict_to_obj(cc, 'requires', component)
        component.save()


def check_upgrade(proto, conf):
    check_key(proto.type, proto.name, '', 'upgrade', 'name', conf)
    check_versions(proto, conf, f"upgrade \"{conf['name']}\"")


def check_versions(proto, conf, label):
    ref = proto_ref(proto)
    msg = '{} has no mandatory \"versions\" key ({})'
    if not conf:
        err('INVALID_VERSION_DEFINITION', msg.format(label, ref))
    if 'versions' not in conf:
        err('INVALID_VERSION_DEFINITION', msg.format(label, ref))
    if not isinstance(conf['versions'], dict):
        err('INVALID_VERSION_DEFINITION', msg.format(label, ref))
    check_extra_keys(
        conf['versions'],
        ('min', 'max', 'min_strict', 'max_strict'),
        '{} versions of {}'.format(label, proto_ref(proto))
    )
    if 'min' in conf['versions'] and 'min_strict' in conf['versions']:
        msg = 'min and min_strict can not be used simultaneously in versions of {} ({})'
        err('INVALID_VERSION_DEFINITION', msg.format(label, ref))
    if 'min' not in conf['versions'] and 'min_strict' not in conf['versions']:
        msg = 'min or min_strict should be present in versions of {} ({})'
        err('INVALID_VERSION_DEFINITION', msg.format(label, ref))
    if 'max' in conf['versions'] and 'max_strict' in conf['versions']:
        msg = 'max and max_strict can not be used simultaneously in versions of {} ({})'
        err('INVALID_VERSION_DEFINITION', msg.format(label, ref))
    if 'max' not in conf['versions'] and 'max_strict' not in conf['versions']:
        msg = 'max and max_strict should be present in versions of {} ({})'
        err('INVALID_VERSION_DEFINITION', msg.format(label, ref))
    for name in ('min', 'min_strict', 'max', 'max_strict'):
        if name in conf['versions'] and not conf['versions'][name]:
            msg = '{} versions of {} should be not null ({})'
            err('INVALID_VERSION_DEFINITION', msg.format(name, label, ref))


def set_version(obj, conf):
    if 'min' in conf['versions']:
        obj.min_version = conf['versions']['min']
        obj.min_strict = False
    elif 'min_strict' in conf['versions']:
        obj.min_version = conf['versions']['min_strict']
        obj.min_strict = True

    if 'max' in conf['versions']:
        obj.max_version = conf['versions']['max']
        obj.max_strict = False
    elif 'max_strict' in conf['versions']:
        obj.max_version = conf['versions']['max_strict']
        obj.max_strict = True


def check_upgrade_edition(proto, conf):
    if 'from_edition' not in conf:
        return
    if isinstance(conf['from_edition'], str) and conf['from_edition'] == 'any':
        return
    if not isinstance(conf['from_edition'], list):
        msg = 'from_edition upgrade filed of {} should be array, not string'
        err('INVALID_UPGRADE_DEFINITION', msg.format(proto_ref(proto)))


def save_upgrade(proto, conf):
    ref = proto_ref(proto)
    if not in_dict(conf, 'upgrade'):
        return
    if not isinstance(conf['upgrade'], list):
        msg = 'Upgrade definition of {} should be an array'
        err('INVALID_UPGRADE_DEFINITION', msg.format(ref))
    for item in conf['upgrade']:
        allow = ('versions', 'from_edition', 'states', 'name', 'description')
        check_extra_keys(item, allow, 'upgrade of {}'.format(ref))
        check_upgrade(proto, item)
        upg = StageUpgrade(name=item['name'])
        set_version(upg, item)
        dict_to_obj(item, 'description', upg)
        if 'states' in item:
            check_upgrade_states(proto, item)
            dict_to_obj(item['states'], 'available', upg)
            if 'available' in item['states']:
                upg.state_available = item['states']['available']
            if 'on_success' in item['states']:
                upg.state_on_success = item['states']['on_success']
        check_upgrade_edition(proto, item)
        if in_dict(item, 'from_edition'):
            upg.from_edition = item['from_edition']
        upg.save()


def save_export(proto, conf):
    ref = proto_ref(proto)
    if not in_dict(conf, 'export'):
        return
    if proto.type not in ('cluster', 'service'):
        msg = 'Only cluster or service can have export section ({})'
        err('INVALID_OBJECT_DEFINITION', msg.format(ref))
    if isinstance(conf['export'], str):
        export = [conf['export']]
    elif isinstance(conf['export'], list):
        export = conf['export']
    else:
        err('INVALID_OBJECT_DEFINITION', '{} export should be string or array type'.format(ref))

    msg = '{} does not has "{}" config group'
    for key in export:
        try:
            if not StagePrototypeConfig.objects.filter(prototype=proto, name=key):
                err('INVALID_OBJECT_DEFINITION', msg.format(ref, key))
        except StagePrototypeConfig.DoesNotExist:
            err('INVALID_OBJECT_DEFINITION', msg.format(ref, key))
        se = StagePrototypeExport(prototype=proto, name=key)
        se.save()


def get_config_groups(proto, action=None):
    groups = {}
    for c in StagePrototypeConfig.objects.filter(prototype=proto, action=action):
        if c.subname != '':
            groups[c.name] = c.name
    return groups


def check_default_import(proto, conf):
    ref = proto_ref(proto)
    if 'default' not in conf:
        return
    if not isinstance(conf['default'], list):
        msg = 'Import deafult section should be an array ({})'
        err('INVALID_OBJECT_DEFINITION', msg.format(ref))
    groups = get_config_groups(proto)
    for key in conf['default']:
        if key not in groups:
            msg = 'No import deafult group "{}" in config ({})'
            err('INVALID_OBJECT_DEFINITION', msg.format(key, ref))


def save_import(proto, conf):
    ref = proto_ref(proto)
    if not in_dict(conf, 'import'):
        return
    if proto.type not in ('cluster', 'service'):
        err('INVALID_OBJECT_DEFINITION', 'Only cluster or service can has an import section')
    if not isinstance(conf['import'], dict):
        err('INVALID_OBJECT_DEFINITION', '{} import should be object type'.format(ref))
    allowed_keys = ('versions', 'default', 'required', 'multibind')
    for key in conf['import']:
        check_extra_keys(conf['import'][key], allowed_keys, ref + ' import')
        check_versions(proto, conf['import'][key], f'import "{key}"')
        if 'default' in conf['import'][key] and 'required' in conf['import'][key]:
            msg = 'Import can\'t have default and be required in the same time ({})'
            err('INVALID_OBJECT_DEFINITION', msg.format(ref))
        check_default_import(proto, conf['import'][key])
        si = StagePrototypeImport(prototype=proto, name=key)
        set_version(si, conf['import'][key])
        dict_to_obj(conf['import'][key], 'required', si)
        dict_to_obj(conf['import'][key], 'multibind', si)
        dict_to_obj(conf['import'][key], 'default', si)
        si.save()


def check_action_hc(proto, conf, name):
    if 'hc_acl' not in conf:
        return
    ref = proto_ref(proto)
    if not isinstance(conf['hc_acl'], list):
        msg = 'hc_acl of action "{}" in {} should be array'
        err('INVALID_ACTION_DEFINITION', msg.format(name, ref))
    allow = ('service', 'component', 'action')
    for idx, item in enumerate(conf['hc_acl']):
        if not isinstance(item, dict):
            msg = 'hc_acl entry of action "{}" in {} should be a map'
            err('INVALID_ACTION_DEFINITION', msg.format(name, ref))
        check_extra_keys(item, allow, 'hc_acl of action "{}" in {}'.format(name, ref))
        if 'service' not in item:
            if proto.type == 'service':
                item['service'] = proto.name
                conf['hc_acl'][idx]['service'] = proto.name
        for key in allow:
            if key not in item:
                msg = 'hc_acl of action "{}" in {} doesn\'t has required key "{}"'
                err('INVALID_ACTION_DEFINITION', msg.format(name, ref, key))
        if item['action'] not in ('add', 'remove'):
            msg = 'hc_acl of action "{}" in {} action value "{}" is not "add" or "remove"'
            err('INVALID_ACTION_DEFINITION', msg.format(name, ref, item['action']))


def check_sub_action(proto, sub_config, action):
    label = 'sub action of action'
    ref = '{} "{}" in {}'.format(label, action.name, proto_ref(proto))
    check_key(proto.type, proto.name, label, action.name, 'name', sub_config)
    check_key(proto.type, proto.name, label, action.name, 'script', sub_config)
    check_key(proto.type, proto.name, label, action.name, 'script_type', sub_config)
    allow = ('name', 'display_name', 'script', 'script_type', 'on_fail', 'params')
    check_extra_keys(sub_config, allow, ref)


def save_sub_actions(proto, conf, action):
    ref = proto_ref(proto)
    if action.type != 'task':
        return
    if not isinstance(conf['scripts'], list):
        msg = 'scripts entry of action "{}" in {} should be a list'
        err('INVALID_ACTION_DEFINITION', msg.format(action.name, ref))
    for sub in conf['scripts']:
        check_sub_action(proto, sub, action)
        sub_action = StageSubAction(
            action=action,
            script=sub['script'],
            script_type=sub['script_type'],
            name=sub['name']
        )
        sub_action.display_name = sub['name']
        if 'display_name' in sub:
            sub_action.display_name = sub['display_name']
        dict_to_obj(sub, 'params', sub_action)
        if 'on_fail' in sub:
            sub_action.state_on_fail = sub['on_fail']
        sub_action.save()


def save_actions(proto, conf, bundle_hash):
    if not in_dict(conf, 'actions'):
        return
    for action_name in sorted(conf['actions']):
        ac = conf['actions'][action_name]
        check_action(proto, action_name, ac)
        action = StageAction(prototype=proto, name=action_name)
        action.type = ac['type']
        if ac['type'] == 'job':
            action.script = ac['script']
            action.script_type = ac['script_type']
        dict_to_obj(ac, 'button', action)
        dict_to_obj(ac, 'display_name', action)
        dict_to_obj(ac, 'description', action)
        dict_to_obj(ac, 'allow_to_terminate', action)
        dict_to_obj(ac, 'partial_execution', action)
        dict_to_obj(ac, 'ui_options', action)
        dict_to_obj(ac, 'params', action)
        dict_to_obj(ac, 'log_files', action)
        fix_display_name(ac, action)

        check_action_hc(proto, ac, action_name)
        dict_to_obj(ac, 'hc_acl', action, 'hostcomponentmap')

        if check_action_states(proto, action_name, ac):
            if 'on_success' in ac['states'] and ac['states']['on_success']:
                action.state_on_success = ac['states']['on_success']
            if 'on_fail' in ac['states'] and ac['states']['on_fail']:
                action.state_on_fail = ac['states']['on_fail']
            action.state_available = ac['states']['available']
        action.save()
        save_sub_actions(proto, ac, action)
        save_prototype_config(proto, ac, bundle_hash, action)


def check_action_states(proto, action, ac):
    if 'states' not in ac:
        return False
    ref = 'action "{}" of {}'.format(action, proto_ref(proto))
    check_extra_keys(ac['states'], ('available', 'on_success', 'on_fail'), ref)
    check_key(proto.type, proto, 'states of action', action, 'available', ac['states'])

    if 'on_success' in ac['states']:
        if not isinstance(ac['states']['on_success'], str):
            msg = 'states:on_success of {} should be string'
            err('INVALID_ACTION_DEFINITION', msg.format(ref))

    if 'on_fail' in ac['states']:
        if not isinstance(ac['states']['on_fail'], str):
            msg = 'states:on_fail of {} should be string'
            err('INVALID_ACTION_DEFINITION', msg.format(ref))

    if isinstance(ac['states']['available'], str) and ac['states']['available'] == 'any':
        return True
    if not isinstance(ac['states']['available'], list):
        msg = 'states:available of {} should be array, not string'
        err('INVALID_ACTION_DEFINITION', msg.format(ref))
    return True


def check_upgrade_states(proto, ac):
    if 'states' not in ac:
        return False
    ref = 'upgrade states of {}'.format(proto_ref(proto))
    check_extra_keys(ac['states'], ('available', 'on_success'), ref)

    if 'on_success' in ac['states']:
        if not isinstance(ac['states']['on_success'], str):
            msg = 'states:on_success of {} should be string'
            err('INVALID_ACTION_DEFINITION', msg.format(ref))

    if 'available' not in ac['states']:
        return True
    if isinstance(ac['states']['available'], str) and ac['states']['available'] == 'any':
        return True
    if not isinstance(ac['states']['available'], list):
        msg = 'states:available of upgrade in {} "{}" should be array, not string'
        err('INVALID_UPGRADE_DEFINITION', msg.format(proto.type, proto.name))
    return True


def check_action(proto, action, act_config):
    ref = 'action "{}" in {} "{}" {}'.format(action, proto.type, proto.name, proto.version)
    err_msg = 'Action name "{}" of {} "{}" {}'.format(action, proto.type, proto.name, proto.version)
    validate_name(action, err_msg)

    check_key(proto.type, proto.name, 'action', action, 'type', act_config)
    action_type = act_config['type']
    if action_type == 'job':
        check_key(proto.type, proto.name, 'action', action, 'script', act_config)
        check_key(proto.type, proto.name, 'action', action, 'script_type', act_config)
    elif action_type == 'task':
        check_key(proto.type, proto.name, 'action', action, 'scripts', act_config)
    else:
        err('WRONG_ACTION_TYPE', '{} has unknown type "{}"'.format(ref, action_type))

    if 'button' in act_config:
        if not isinstance(act_config['button'], str):
            err('INVALID_ACTION_DEFINITION', 'button of {} should be string'.format(ref))

    if (action_type, action_type) not in ACTION_TYPE:
        err('WRONG_ACTION_TYPE', '{} has unknown type "{}"'.format(ref, action_type))
    if 'script_type' in act_config:
        script_type = act_config['script_type']
        if (script_type, script_type) not in SCRIPT_TYPE:
            err('WRONG_ACTION_TYPE', '{} has unknown script_type "{}"'.format(ref, script_type))
    allow = (
        'type', 'script', 'script_type', 'scripts', 'states', 'params', 'config',
        'log_files', 'hc_acl', 'button', 'display_name', 'description', 'ui_options',
        'allow_to_terminate', 'partial_execution'
    )
    check_extra_keys(act_config, allow, ref)


def is_group(conf):
    if conf['type'] == 'group':
        return True
    return False


def get_yspec(proto, ref, bundle_hash, conf, name, subname):
    if 'yspec' not in conf:
        msg = 'Config key "{}/{}" of {} has no mandatory yspec key'
        err('CONFIG_TYPE_ERROR', msg.format(name, subname, ref))
    if not isinstance(conf['yspec'], str):
        msg = 'Config key "{}/{}" of {} yspec field should be string'
        err('CONFIG_TYPE_ERROR', msg.format(name, subname, ref))
    msg = 'yspec file of config key "{}/{}":'.format(name, subname)
    yspec_body = read_bundle_file(proto, conf['yspec'], bundle_hash, msg)
    try:
        schema = yaml.safe_load(yspec_body)
    except (yaml.parser.ParserError, yaml.scanner.ScannerError) as e:
        msg = 'yspec file of config key "{}/{}" yaml decode error: {}'
        err('CONFIG_TYPE_ERROR', msg.format(name, subname, e))
    ok, error = yspec.checker.check_rule(schema)
    if not ok:
        msg = 'yspec file of config key "{}/{}" error: {}'
        err('CONFIG_TYPE_ERROR', msg.format(name, subname, error))
    return schema


def save_prototype_config(proto, proto_conf, bundle_hash, action=None):   # pylint: disable=too-many-locals,too-many-statements,too-many-branches
    if not in_dict(proto_conf, 'config'):
        return
    conf_dict = proto_conf['config']
    ref = proto_ref(proto)

    def check_type(param_type, name, subname):
        if (param_type, param_type) in CONFIG_FIELD_TYPE:
            return 1
        else:
            msg = 'Unknown config type: "{}" for config key "{}/{}" of {}'
            return err('CONFIG_TYPE_ERROR', msg.format(param_type, name, subname, ref))

    def check_options(conf, name, subname):
        if not in_dict(conf, 'option'):
            msg = 'Config key "{}/{}" of {} has no mandatory option key'
            err('CONFIG_TYPE_ERROR', msg.format(name, subname, ref))
        if not isinstance(conf['option'], dict):
            msg = 'Config key "{}/{}" of {} option field should be map'
            err('CONFIG_TYPE_ERROR', msg.format(name, subname, ref))
        for (label, value) in conf['option'].items():
            if value is None:
                msg = 'Option "{}" value should not be empty (config key "{}/{}" of {})'
                err('CONFIG_TYPE_ERROR', msg.format(label, name, subname, ref))
            if isinstance(value, list):
                msg = 'Option "{}" value "{}" should be flat (config key "{}/{}" of {})'
                err('CONFIG_TYPE_ERROR', msg.format(label, value, name, subname, ref))
            if isinstance(value, dict):
                msg = 'Option "{}" value "{}" should be flat (config key "{}/{}" of {})'
                err('CONFIG_TYPE_ERROR', msg.format(label, value, name, subname, ref))
        return True

    def check_variant(conf, name, subname):   # pylint: disable=too-many-branches
        if not in_dict(conf, 'source'):
            msg = 'Config key "{}/{}" of {} has no mandatory "source" key'
            err('CONFIG_TYPE_ERROR', msg.format(name, subname, ref))
        if not isinstance(conf['source'], dict):
            msg = 'Config key "{}/{}" of {} "source" field should be map'
            err('CONFIG_TYPE_ERROR', msg.format(name, subname, ref))
        if not in_dict(conf['source'], 'type'):
            msg = 'Config key "{}/{}" of {} has no mandatory source: type statment'
            err('CONFIG_TYPE_ERROR', msg.format(name, subname, ref))
        allowed_keys = ('type', 'name', 'value', 'strict')
        check_extra_keys(conf['source'], allowed_keys, f'{ref} config key "{name}/{subname}"')
        vtype = conf['source']['type']
        if vtype not in ('inline', 'config', 'builtin'):
            msg = 'Config key "{}/{}" of {} has unknown source type "{}"'
            err('CONFIG_TYPE_ERROR', msg.format(name, subname, ref, vtype))
        source = {'type': vtype}
        if 'strict' in conf['source']:
            if not isinstance(conf['source']['strict'], bool):
                msg = 'Config key "{}/{}" of {} "source: strict" field should be boolean'
                err('CONFIG_TYPE_ERROR', msg.format(name, subname, ref))
            source['strict'] = conf['source']['strict']
        else:
            source['strict'] = True
        if vtype == 'inline':
            if not in_dict(conf['source'], 'value'):
                msg = 'Config key "{}/{}" of {} has no mandatory source:value statment'
                err('CONFIG_TYPE_ERROR', msg.format(name, subname, ref))
            source['value'] = conf['source']['value']
            if not isinstance(source['value'], list):
                msg = 'Config key "{}/{}" of {} source value should be an array'
                err('CONFIG_TYPE_ERROR', msg.format(name, subname, ref))
        elif vtype in ('config', 'builtin'):
            if not in_dict(conf['source'], 'name'):
                msg = 'Config key "{}/{}" of {} has no mandatory source:name statment'
                err('CONFIG_TYPE_ERROR', msg.format(name, subname, ref))
            source['name'] = conf['source']['name']
        if vtype == 'builtin':
            if conf['source']['name'] not in ('free_hosts', 'cluster_hosts'):
                msg = 'Config key "{}/{}" of {} has unknown builtin function "{}"'
                err('CONFIG_TYPE_ERROR', msg.format(name, subname, ref, conf['source']['name']))
        return source

    def check_limit(conf_type, value, name, subname, label):
        if conf_type == 'integer':
            if not isinstance(value, int):
                msg = '{} ("{}") should be integer (config key "{}/{}" of {})'
                err('CONFIG_TYPE_ERROR', msg.format(label, value, name, subname, ref))
        if conf_type == 'float':
            if not isinstance(value, (int, float)):
                msg = '{} ("{}") should be float (config key "{}/{}" of {})'
                err('CONFIG_TYPE_ERROR', msg.format(label, value, name, subname, ref))

    def check_wr(label, conf, name, subname):
        if label not in conf:
            return False
        if isinstance(conf[label], str) and conf[label] == 'any':
            return True
        if not isinstance(conf[label], list):
            msg = '"{}" should be array, not string (config key "{}/{}" of {})'
            err('INVALID_CONFIG_DEFINITION', msg.format(label, name, subname, ref))
        return True

    def process_limits(conf, name, subname):   # pylint: disable=too-many-branches
        def valudate_bool(value, label, name):
            if not isinstance(value, bool):
                msg = 'config group "{}" {} field ("{}") is not boolean ({})'
                err('CONFIG_TYPE_ERROR', msg.format(name, label, value, ref))

        opt = {}
        if conf['type'] == 'option':
            if check_options(conf, name, subname):
                opt = {'option': conf['option']}
        if conf['type'] == 'variant':
            opt['source'] = check_variant(conf, name, subname)
        elif conf['type'] == 'integer' or conf['type'] == 'float':
            if 'min' in conf:
                check_limit(conf['type'], conf['min'], name, subname, 'min')
                opt['min'] = conf['min']
            if 'max' in conf:
                check_limit(conf['type'], conf['max'], name, subname, 'max')
                opt['max'] = conf['max']
        elif conf['type'] == 'structure':
            opt['yspec'] = get_yspec(proto, ref, bundle_hash, conf, name, subname)
        elif is_group(conf):
            if 'activatable' in conf:
                valudate_bool(conf['activatable'], 'activatable', name)
                opt['activatable'] = conf['activatable']
                if 'active' in conf:
                    valudate_bool(conf['active'], 'active', name)
                    opt['active'] = conf['active']
                else:
                    opt['active'] = False

        if 'read_only' in conf and 'writable' in conf:
            key_ref = '(config key "{}/{}" of {})'.format(name, subname, ref)
            msg = 'can not have "read_only" and "writable" simultaneously {}'
            err('INVALID_CONFIG_DEFINITION', msg.format(key_ref))

        for label in ('read_only', 'writable'):
            if label in conf:
                if check_wr(label, conf, name, subname):
                    opt[label] = conf[label]

        return opt

    def valudate_boolean(value, name, subname):
        if not isinstance(value, bool):
            msg = 'config key "{}/{}" required parameter ("{}") is not boolean ({})'
            return err('CONFIG_TYPE_ERROR', msg.format(name, subname, value, ref))
        return value

    def cook_conf(obj, conf, name, subname):   # pylint: disable=too-many-branches
        if not in_dict(conf, 'type'):
            msg = 'No type in config key "{}/{}" of {}'
            err('INVALID_CONFIG_DEFINITION', msg.format(name, subname, ref))
        check_type(conf['type'], name, subname)
        if subname:
            if is_group(conf):
                msg = 'Only group can have type "group" (config key "{}/{}" of {})'
                err('INVALID_CONFIG_DEFINITION', msg.format(name, subname, ref))
        else:
            if 'subs' in conf and conf['type'] != 'group':
                msg = 'Group "{}" shoud have type "group" of {})'
                err('INVALID_CONFIG_DEFINITION', msg.format(name, ref))
        if is_group(conf):
            allow = (
                'type', 'description', 'display_name', 'required', 'ui_options',
                'name', 'subs', 'activatable', 'active'
            )
        else:
            allow = (
                'type', 'description', 'display_name', 'default', 'required', 'name', 'yspec',
                'option', 'source', 'limits', 'max', 'min', 'read_only', 'writable', 'ui_options'
            )
        check_extra_keys(conf, allow, 'config key "{}/{}" of {}'.format(name, subname, ref))
        sc = StagePrototypeConfig(
            prototype=obj,
            action=action,
            name=name,
            type=conf['type']
        )
        dict_to_obj(conf, 'description', sc)
        dict_to_obj(conf, 'display_name', sc)
        if 'display_name' not in conf:
            if subname:
                sc.display_name = subname
            else:
                sc.display_name = name
        conf['limits'] = process_limits(conf, name, subname)
        dict_to_obj(conf, 'limits', sc)
        if 'ui_options' in conf:
            if not isinstance(conf['ui_options'], dict):
                msg = 'ui_options of config key "{}/{}" of {} should be a map'
                err('INVALID_CONFIG_DEFINITION', msg.format(name, subname, ref))
        dict_to_obj(conf, 'ui_options', sc)
        if 'default' in conf:
            check_config_type(proto, name, subname, conf, conf['default'], bundle_hash)
        if type_is_complex(conf['type']):
            dict_json_to_obj(conf, 'default', sc)
        else:
            dict_to_obj(conf, 'default', sc)
        if 'required' in conf:
            sc.required = valudate_boolean(conf['required'], name, subname)
        return sc

    if isinstance(conf_dict, dict):
        for (name, conf) in conf_dict.items():
            if not isinstance(conf, dict):
                msg = 'Config definition of {}, key "{}" should be a map'
                err('INVALID_CONFIG_DEFINITION', msg.format(ref, name))
            if 'type' in conf:
                validate_name(name, 'Config key "{}" of {}'.format(name, ref))
                sc = cook_conf(proto, conf, name, '')
                sc.save()
            else:
                validate_name(name, 'Config group "{}" of {}'.format(name, ref))
                group_conf = {'type': 'group', 'required': False}
                sc = cook_conf(proto, group_conf, name, '')
                sc.save()
                for (subname, subconf) in conf.items():
                    err_msg = 'Config key "{}/{}" of {}'.format(name, subname, ref)
                    validate_name(name, err_msg)
                    validate_name(subname, err_msg)
                    sc = cook_conf(proto, subconf, name, subname)
                    sc.subname = subname
                    sc.save()
    elif isinstance(conf_dict, list):
        for conf in conf_dict:
            if not isinstance(conf, dict):
                msg = 'Config definition of {} items should be a map'
                err('INVALID_CONFIG_DEFINITION', msg.format(ref))
            if 'name' not in conf:
                msg = 'Config definition of {} should have a name required parameter'
                err('INVALID_CONFIG_DEFINITION', msg.format(ref))
            name = conf['name']
            validate_name(name, 'Config key "{}" of {}'.format(name, ref))
            sc = cook_conf(proto, conf, name, '')
            sc.save()
            if is_group(conf):
                if 'subs' not in conf:
                    msg = 'Config definition of {}, group "{}" shoud have "subs" required section)'
                    err('INVALID_CONFIG_DEFINITION', msg.format(ref, name))
                if not isinstance(conf['subs'], list):
                    msg = 'Config definition of {}, group "{}" subs section should be an array'
                    err('INVALID_CONFIG_DEFINITION', msg.format(ref, name))
                for subconf in conf['subs']:
                    if not isinstance(subconf, dict):
                        msg = 'Config definition of {} sub items of item "{}" should be a map'
                        err('INVALID_CONFIG_DEFINITION', msg.format(ref, name))
                    if 'name' not in subconf:
                        msg = 'Config definition of {}, group "{}" subs items should have a name'
                        err('INVALID_CONFIG_DEFINITION', msg.format(ref, name))
                    subname = subconf['name']
                    err_msg = 'Config key "{}/{}" of {}'.format(name, subname, ref)
                    validate_name(name, err_msg)
                    validate_name(subname, err_msg)
                    sc = cook_conf(proto, subconf, name, subname)
                    sc.subname = subname
                    sc.save()
    else:
        msg = 'Config definition of {} should be a map or an array'
        err('INVALID_CONFIG_DEFINITION', msg.format(ref))


def check_key(context, context_name, param, param_name, key, conf):
    msg = '{} "{}" in {} "{}" has no mandatory "{}" key'.format(
        param, param_name, context, context_name, key
    )
    if not conf:
        err('DEFINITION_KEY_ERROR', msg)
    if key not in conf:
        err('DEFINITION_KEY_ERROR', msg)
    if not conf[key]:
        err('DEFINITION_KEY_ERROR', msg)


def validate_name(value, name):
    if not isinstance(value, str):
        err("WRONG_NAME", '{} should be string'.format(name))
    p = re.compile(NAME_REGEX)
    msg1 = '{} is incorrect. Only latin characters, digits,' \
        ' dots (.), dashes (-), and underscores (_) are allowed.'
    if p.fullmatch(value) is None:
        err("WRONG_NAME", msg1.format(name))
    msg2 = "{} is too long. Max length is {}"
    if len(value) > MAX_NAME_LENGTH:
        raise err("LONG_NAME", msg2.format(name, MAX_NAME_LENGTH))
    return value


def fix_display_name(conf, obj):
    if isinstance(conf, dict) and 'display_name' in conf:
        return
    obj.display_name = obj.name


def in_dict(dictionary, key):
    if not isinstance(dictionary, dict):
        return False
    if key in dictionary:
        if dictionary[key] is None:
            return False
        else:
            return True
    else:
        return False


def dict_to_obj(dictionary, key, obj, obj_key=None):
    if not obj_key:
        obj_key = key
    if not isinstance(dictionary, dict):
        return
    if key in dictionary:
        if dictionary[key] is not None:
            setattr(obj, obj_key, dictionary[key])


def dict_json_to_obj(dictionary, key, obj, obj_key=''):
    if obj_key == '':
        obj_key = key
    if isinstance(dictionary, dict):
        if key in dictionary:
            setattr(obj, obj_key, json.dumps(dictionary[key]))
