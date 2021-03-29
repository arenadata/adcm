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
import ruyaml
import hashlib
import warnings
import yspec.checker

from rest_framework import status

from cm.logger import log
from cm.errors import raise_AdcmEx as err
import cm.config as config
import cm.checker

from cm.adcm_config import proto_ref, check_config_type, type_is_complex, read_bundle_file
from cm.models import StagePrototype, StageAction, StagePrototypeConfig
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
    def_type = conf['type']
    if def_type == 'adcm' and not adcm:
        msg = 'Invalid type "{}" in object definition: {}'
        return err('INVALID_OBJECT_DEFINITION', msg.format(def_type, fname))
    check_object_definition(fname, conf, def_type, obj_list)
    obj = save_prototype(path, conf, def_type, bundle_hash)
    log.info('Save definition of %s "%s" %s to stage', def_type, conf['name'], conf['version'])
    obj_list[cook_obj_id(conf)] = fname
    return obj


def check_object_definition(fname, conf, def_type, obj_list):
    ref = '{} "{}" {}'.format(def_type, conf['name'], conf['version'])
    if cook_obj_id(conf) in obj_list:
        err('INVALID_OBJECT_DEFINITION', f'Duplicate definition of {ref} (file {fname})')


def get_config_files(path, bundle_hash):
    conf_list = []
    conf_types = [
        ('config.yaml', 'yaml'),
        ('config.yml', 'yaml'),
    ]
    if not os.path.isdir(path):
        return err('STACK_LOAD_ERROR', f'no directory: {path}', status.HTTP_404_NOT_FOUND)
    for root, _, files in os.walk(path):
        for conf_file, conf_type in conf_types:
            if conf_file in files:
                dirs = root.split('/')
                path = os.path.join('', *dirs[dirs.index(bundle_hash) + 1:])
                conf_list.append((path, root + '/' + conf_file, conf_type))
                break
    if not conf_list:
        return err('STACK_LOAD_ERROR', f'no config files in stack directory "{path}"')
    return conf_list


def check_adcm_config(conf_file):
    warnings.simplefilter('error', ruyaml.error.ReusedAnchorWarning)
    schema_file = os.path.join(config.CODE_DIR, 'cm', 'adcm_schema.yaml')
    with open(schema_file) as fd:
        rules = ruyaml.round_trip_load(fd)
    try:
        with open(conf_file) as fd:
            data = ruyaml.round_trip_load(fd, version="1.1")
    except (ruyaml.parser.ParserError, ruyaml.scanner.ScannerError, NotImplementedError) as e:
        err('STACK_LOAD_ERROR', f'YAML decode "{conf_file}" error: {e}')
    except ruyaml.error.ReusedAnchorWarning as e:
        err('STACK_LOAD_ERROR', f'YAML decode "{conf_file}" error: {e}')
    except ruyaml.constructor.DuplicateKeyError as e:
        msg = f'{e.context}\n{e.context_mark}\n{e.problem}\n{e.problem_mark}'
        err('STACK_LOAD_ERROR', f'Duplicate Keys error: {msg}')
    try:
        cm.checker.check(data, rules)
        return data
    except cm.checker.FormatError as e:
        args = ''
        if e.errors:
            for ee in e.errors:
                if 'Input data for' in ee.message:
                    continue
                args += f'line {ee.line}: {ee}\n'
        err('INVALID_OBJECT_DEFINITION', f'"{conf_file}" line {e.line} error: {e}', args)
        return {}


def read_definition(conf_file, conf_type):
    if os.path.isfile(conf_file):
        conf = check_adcm_config(conf_file)
        log.info('Read config file: "%s"', conf_file)
        return conf
    log.warning('Can not open config file: "%s"', conf_file)
    return {}


def get_license_hash(proto, conf, bundle_hash):
    if 'license' not in conf:
        return None
    body = read_bundle_file(proto, conf['license'], bundle_hash, 'license file')
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
    save_components(proto, conf, bundle_hash)
    save_prototype_config(proto, conf, bundle_hash)
    save_export(proto, conf)
    save_import(proto, conf)
    return proto


def check_component_constraint(proto, name, conf):
    if not conf:
        return
    if 'constraint' not in conf:
        return
    if len(conf['constraint']) > 2:
        msg = 'constraint of component "{}" in {} should have only 1 or 2 elements'
        err('INVALID_COMPONENT_DEFINITION', msg.format(name, proto_ref(proto)))


def save_components(proto, conf, bundle_hash):
    ref = proto_ref(proto)
    if not in_dict(conf, 'components'):
        return
    for comp_name in conf['components']:
        cc = conf['components'][comp_name]
        validate_name(comp_name, f'Component name "{comp_name}" of {ref}')
        component = StagePrototype(
            type='component',
            parent=proto,
            path=proto.path,
            name=comp_name,
            version=proto.version,
            adcm_min_version=proto.adcm_min_version,
        )
        dict_to_obj(cc, 'description', component)
        dict_to_obj(cc, 'display_name', component)
        dict_to_obj(cc, 'monitoring', component)
        fix_display_name(cc, component)
        check_component_constraint(proto, comp_name, cc)
        dict_to_obj(cc, 'params', component)
        dict_to_obj(cc, 'constraint', component)
        dict_to_obj(cc, 'requires', component)
        dict_to_obj(cc, 'bound_to', component)
        component.save()
        save_actions(component, cc, bundle_hash)
        save_prototype_config(component, cc, bundle_hash)


def check_upgrade(proto, conf):
    check_versions(proto, conf, f"upgrade \"{conf['name']}\"")


def check_versions(proto, conf, label):
    ref = proto_ref(proto)
    msg = '{} has no mandatory \"versions\" key ({})'
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


def save_upgrade(proto, conf):
    if not in_dict(conf, 'upgrade'):
        return
    for item in conf['upgrade']:
        check_versions(proto, item, f"upgrade \"{conf['name']}\"")
        upg = StageUpgrade(name=item['name'])
        set_version(upg, item)
        dict_to_obj(item, 'description', upg)
        if 'states' in item:
            dict_to_obj(item['states'], 'available', upg)
            if 'available' in item['states']:
                upg.state_available = item['states']['available']
            if 'on_success' in item['states']:
                upg.state_on_success = item['states']['on_success']
        if in_dict(item, 'from_edition'):
            upg.from_edition = item['from_edition']
        upg.save()


def save_export(proto, conf):
    ref = proto_ref(proto)
    if not in_dict(conf, 'export'):
        return
    if isinstance(conf['export'], str):
        export = [conf['export']]
    elif isinstance(conf['export'], list):
        export = conf['export']
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
    groups = get_config_groups(proto)
    for key in conf['default']:
        if key not in groups:
            msg = 'No import deafult group "{}" in config ({})'
            err('INVALID_OBJECT_DEFINITION', msg.format(key, ref))


def save_import(proto, conf):
    ref = proto_ref(proto)
    if not in_dict(conf, 'import'):
        return
    for key in conf['import']:
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
    for idx, item in enumerate(conf['hc_acl']):
        if 'service' not in item:
            if proto.type == 'service':
                item['service'] = proto.name
                conf['hc_acl'][idx]['service'] = proto.name


def save_sub_actions(proto, conf, action):
    if action.type != 'task':
        return
    for sub in conf['scripts']:
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
        dict_to_obj(ac, 'host_action', action)
        dict_to_obj(ac, 'ui_options', action)
        dict_to_obj(ac, 'params', action)
        dict_to_obj(ac, 'log_files', action)
        fix_display_name(ac, action)
        check_action_hc(proto, ac, action_name)
        dict_to_obj(ac, 'hc_acl', action, 'hostcomponentmap')
        if 'states' in ac:
            if 'on_success' in ac['states'] and ac['states']['on_success']:
                action.state_on_success = ac['states']['on_success']
            if 'on_fail' in ac['states'] and ac['states']['on_fail']:
                action.state_on_fail = ac['states']['on_fail']
            action.state_available = ac['states']['available']
        action.save()
        save_sub_actions(proto, ac, action)
        save_prototype_config(proto, ac, bundle_hash, action)


def check_action(proto, action, act_config):
    err_msg = 'Action name "{}" of {} "{}" {}'.format(action, proto.type, proto.name, proto.version)
    validate_name(action, err_msg)


def is_group(conf):
    if conf['type'] == 'group':
        return True
    return False


def get_yspec(proto, ref, bundle_hash, conf, name, subname):
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


def save_prototype_config(proto, proto_conf, bundle_hash, action=None):   # pylint: disable=too-many-statements,too-many-locals
    if not in_dict(proto_conf, 'config'):
        return
    conf_dict = proto_conf['config']
    ref = proto_ref(proto)

    def check_variant(conf, name, subname):
        vtype = conf['source']['type']
        source = {'type': vtype, 'args': None}
        if 'strict' in conf['source']:
            source['strict'] = conf['source']['strict']
        else:
            source['strict'] = True
        if vtype == 'inline':
            source['value'] = conf['source']['value']
        elif vtype in ('config', 'builtin'):
            source['name'] = conf['source']['name']
        if vtype == 'builtin':
            if 'args' in conf['source']:
                source['args'] = conf['source']['args']
        return source

    def process_limits(conf, name, subname):
        opt = {}
        if conf['type'] == 'option':
            opt = {'option': conf['option']}
        elif conf['type'] == 'variant':
            opt['source'] = check_variant(conf, name, subname)
        elif conf['type'] == 'integer' or conf['type'] == 'float':
            if 'min' in conf:
                opt['min'] = conf['min']
            if 'max' in conf:
                opt['max'] = conf['max']
        elif conf['type'] == 'structure':
            opt['yspec'] = get_yspec(proto, ref, bundle_hash, conf, name, subname)
        elif is_group(conf):
            if 'activatable' in conf:
                opt['activatable'] = conf['activatable']
                opt['active'] = False
                if 'active' in conf:
                    opt['active'] = conf['active']

        if 'read_only' in conf and 'writable' in conf:
            key_ref = '(config key "{}/{}" of {})'.format(name, subname, ref)
            msg = 'can not have "read_only" and "writable" simultaneously {}'
            err('INVALID_CONFIG_DEFINITION', msg.format(key_ref))

        for label in ('read_only', 'writable'):
            if label in conf:
                opt[label] = conf[label]

        return opt

    def cook_conf(obj, conf, name, subname):
        sc = StagePrototypeConfig(
            prototype=obj,
            action=action,
            name=name,
            type=conf['type']
        )
        dict_to_obj(conf, 'description', sc)
        dict_to_obj(conf, 'display_name', sc)
        dict_to_obj(conf, 'required', sc)
        dict_to_obj(conf, 'ui_options', sc)
        conf['limits'] = process_limits(conf, name, subname)
        dict_to_obj(conf, 'limits', sc)
        if 'display_name' not in conf:
            if subname:
                sc.display_name = subname
            else:
                sc.display_name = name
        if 'default' in conf:
            check_config_type(proto, name, subname, conf, conf['default'], bundle_hash)
        if type_is_complex(conf['type']):
            dict_json_to_obj(conf, 'default', sc)
        else:
            dict_to_obj(conf, 'default', sc)
        return sc

    if isinstance(conf_dict, dict):
        for (name, conf) in conf_dict.items():
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
            name = conf['name']
            validate_name(name, 'Config key "{}" of {}'.format(name, ref))
            sc = cook_conf(proto, conf, name, '')
            sc.save()
            if is_group(conf):
                for subconf in conf['subs']:
                    subname = subconf['name']
                    err_msg = 'Config key "{}/{}" of {}'.format(name, subname, ref)
                    validate_name(name, err_msg)
                    validate_name(subname, err_msg)
                    sc = cook_conf(proto, subconf, name, subname)
                    sc.subname = subname
                    sc.save()


def validate_name(value, name):
    if not isinstance(value, str):
        err("WRONG_NAME", '{} should be string'.format(name))
    p = re.compile(NAME_REGEX)
    msg1 = '{} is incorrect. Only latin characters, digits,' \
        ' dots (.), dashes (-), and underscores (_) are allowed.'
    if p.fullmatch(value) is None:
        err("WRONG_NAME", msg1.format(name))
    if len(value) > MAX_NAME_LENGTH:
        raise err("LONG_NAME", f'{name} is too long. Max length is {MAX_NAME_LENGTH}')
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
