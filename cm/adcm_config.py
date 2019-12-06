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
import json
import collections
import yspec.checker
from django.conf import settings
from django.db.utils import OperationalError

from cm.logger import log   # pylint: disable=unused-import
import cm.config as config
from cm.models import Cluster, Prototype, Host, HostProvider, ADCM
from cm.models import ClusterObject, PrototypeConfig, ObjectConfig, ConfigLog
from cm.errors import AdcmApiEx
from cm.errors import raise_AdcmEx as err


def proto_ref(proto):
    return '{} "{}" {}'.format(proto.type, proto.name, proto.version)


def obj_ref(obj):
    if hasattr(obj, 'name'):
        name = obj.name
    if hasattr(obj, 'fqdn'):
        name = obj.fqdn
    else:
        name = obj.prototype.name
    return '{} #{} "{}"'.format(obj.prototype.type, obj.id, name)


def obj_to_dict(obj, keys):
    dictionary = {}
    for key in keys:
        if hasattr(obj, key):
            dictionary[key] = getattr(obj, key)
    return dictionary


def to_flat_dict(conf, spec):
    flat = {}
    for c1 in conf:
        if isinstance(conf[c1], dict):
            key = '{}/'.format(c1)
            if key in spec and spec[key].type != 'group':
                flat['{}/{}'.format(c1, '')] = conf[c1]
            else:
                for c2 in conf[c1]:
                    flat['{}/{}'.format(c1, c2)] = conf[c1][c2]
        else:
            flat['{}/{}'.format(c1, '')] = conf[c1]
    return flat


def get_default(c, proto=None):   # pylint: disable=too-many-branches
    value = c.default
    if c.default == '':
        value = None
    elif c.type == 'string':
        value = c.default
    elif c.type == 'text':
        value = c.default
    elif type_is_complex(c.type):
        value = json.loads(c.default)
    elif c.type == 'integer':
        value = int(c.default)
    elif c.type == 'float':
        value = float(c.default)
    elif c.type == 'boolean':
        if isinstance(c.default, bool):
            value = c.default
        else:
            value = bool(c.default.lower() in ('true', 'yes'))
    elif c.type == 'option':
        limits = json.loads(c.limits)
        if c.default in limits['option']:
            value = limits['option'][c.default]
    elif c.type == 'file':
        if proto:
            if c.default:
                value = read_file_type(
                    c.default, proto_ref(proto), proto.bundle.hash, c.name, c.subname
                )
    return value


def type_is_complex(conf_type):
    if conf_type in ('json', 'structure', 'list', 'map'):
        return True
    return False


def read_file_type(default, ref, bundle_hash, name, subname):
    msg = 'config key "{}/{}" default file'.format(name, subname)
    return read_bundle_file(default, bundle_hash, msg, ref)


def read_bundle_file(fname, bundle_hash, pattern, ref):
    path = os.path.join(config.BUNDLE_DIR, bundle_hash, fname)
    try:
        fd = open(path, 'r')
    except FileNotFoundError:
        msg = '{} "{}" is not found ({})'
        err('CONFIG_TYPE_ERROR', msg.format(pattern, path, ref))
    except PermissionError:
        msg = '{} "{}" can not be open ({})'
        err('CONFIG_TYPE_ERROR', msg.format(pattern, path, ref))
    body = fd.read()
    fd.close()
    return body


def init_object_config(proto):
    spec, _, conf, attr = get_prototype_config(proto)
    if not conf:
        return (None, spec, conf)
    obj_conf = ObjectConfig(
        current=0,
        previous=0
    )
    obj_conf.save()
    save_obj_config(obj_conf, conf, 'init', attr)
    return (obj_conf, spec, conf)


def prepare_social_auth(conf):
    if 'google_oauth' not in conf:
        return
    gconf = conf['google_oauth']
    if 'client_id' not in gconf or not gconf['client_id']:
        return
    if 'secret' not in gconf or not gconf['secret']:
        return
    settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = gconf['client_id']
    settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = gconf['secret']
    if 'whitelisted_domains' in gconf:
        settings.SOCIAL_AUTH_GOOGLE_OAUTH2_WHITELISTED_DOMAINS = gconf['whitelisted_domains']


def load_social_auth():
    try:
        adcm = ADCM.objects.filter()
        if not adcm:
            return
    except OperationalError:
        return
    try:
        cl = ConfigLog.objects.get(obj_ref=adcm[0].config, id=adcm[0].config.current)
        prepare_social_auth(json.loads(cl.config))
    except OperationalError as e:
        log.error('load_social_auth error: %s', e)


def get_prototype_config(proto, action=None):
    spec = {}
    flat_spec = collections.OrderedDict()
    conf = {}
    attr = {}
    flist = ('default', 'required', 'type', 'limits')
    for c in PrototypeConfig.objects.filter(
            prototype=proto, action=action, type='group').order_by('id'):
        spec[c.name] = {}
        conf[c.name] = {}
        if c.limits:
            limits = json.loads(c.limits)
            if 'activatable' in limits:
                attr[c.name] = {'active': limits['active']}

    for c in PrototypeConfig.objects.filter(prototype=proto, action=action).order_by('id'):
        flat_spec['{}/{}'.format(c.name, c.subname)] = c
        if c.subname == '':
            if c.type != 'group':
                spec[c.name] = obj_to_dict(c, flist)
                conf[c.name] = get_default(c, proto)
        else:
            spec[c.name][c.subname] = obj_to_dict(c, flist)
            conf[c.name][c.subname] = get_default(c, proto)
    return (spec, flat_spec, conf, attr)


def switch_config(obj, new_proto):
    if not obj.config:
        obj_conf, _, _ = init_object_config(new_proto)
        if obj_conf:
            obj.config = obj_conf
            obj.save()
        return

    cl = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
    _, old_spec, _, _ = get_prototype_config(obj.prototype)
    new_unflat_spec, new_spec, _, _ = get_prototype_config(new_proto)
    old_conf = to_flat_dict(json.loads(cl.config), old_spec)

    def is_new_default(key):
        if not new_spec[key].default:
            return False
        if old_spec[key].default:
            if key in old_conf:
                return bool(get_default(old_spec[key], obj.prototype) == old_conf[key])
            else:
                return True
        return False

    new_conf = {}
    for key in new_spec:
        if new_spec[key].type == 'group':
            continue
        if key in old_spec:
            if is_new_default(key):
                new_conf[key] = get_default(new_spec[key], new_proto)
            else:
                new_conf[key] = old_conf.get(key, get_default(new_spec[key], new_proto))
        else:
            new_conf[key] = get_default(new_spec[key], new_proto)

    unflat_conf = {}
    for key in new_conf:
        k1, k2 = key.split('/')
        if k2 == '':
            unflat_conf[k1] = new_conf[key]
        else:
            if k1 not in unflat_conf:
                unflat_conf[k1] = {}
            unflat_conf[k1][k2] = new_conf[key]

    save_obj_config(obj.config, unflat_conf, 'upgrade', cl.attr)
    process_file_type(obj, new_unflat_spec, unflat_conf)


def restore_cluster_config(obj_conf, version, desc=''):
    try:
        cl = ConfigLog.objects.get(obj_ref=obj_conf, id=version)
    except ConfigLog.DoesNotExist:
        raise AdcmApiEx('CONFIG_NOT_FOUND', "config version doesn't exist")
    obj_conf.previous = obj_conf.current
    obj_conf.current = version
    obj_conf.save()
    if desc != '':
        cl.description = desc
    cl.save()
    return cl


def save_obj_config(obj_conf, conf, desc='', attr=None):
    cl = ConfigLog(
        obj_ref=obj_conf,
        config=json.dumps(conf),
        description=desc
    )
    if isinstance(attr, dict):
        cl.attr = json.dumps(attr)
    else:
        cl.attr = attr
    cl.save()
    obj_conf.previous = obj_conf.current
    obj_conf.current = cl.id
    obj_conf.save()
    return cl


def cook_file_type_name(obj, key, subkey):
    return '{}/{}.{}.{}.{}'.format(config.FILE_DIR, obj.prototype.type, obj.id, key, subkey)


def save_file_type(obj, key, subkey, value):
    filename = cook_file_type_name(obj, key, subkey)
    if value is None:
        if os.path.exists(filename):
            os.remove(filename)
        return None

    # There is a trouble between openssh 7.9 and register function of Ansible.
    # Register function does rstrip of string, while openssh 7.9 not working
    # with private key files without \n at the end.
    # So when we create that key from playbook and save it in ADCM we get
    # 'Load key : invalid format' on next connect to host.
    # TODO: That should be fixed some way in bundles or in openssh.
    if key == 'ansible_ssh_private_key_file':
        if value != '':
            if value[-1] == '-':
                value += '\n'
    fd = open(filename, 'w')
    fd.write(value)
    fd.close()
    os.chmod(filename, 0o0600)
    return filename


def process_file_type(obj, spec, conf):
    for key in conf:
        if 'type' in spec[key]:
            if spec[key]['type'] == 'file':
                save_file_type(obj, key, '', conf[key])
        else:
            for subkey in conf[key]:
                if spec[key][subkey]['type'] == 'file':
                    save_file_type(obj, key, subkey, conf[key][subkey])
    return conf


def group_is_activatable(spec):
    if spec.type != 'group':
        return False
    if spec.limits:
        limits = json.loads(spec.limits)
        if 'activatable' in limits:
            return limits['activatable']
    return False


def ui_config(obj, cl):
    conf = []
    _, spec, _, _ = get_prototype_config(obj.prototype)
    flat_conf = to_flat_dict(json.loads(cl.config), spec)
    slist = ('name', 'subname', 'type', 'description', 'display_name', 'required')
    for key in spec:
        item = obj_to_dict(spec[key], slist)
        item['limits'] = json.loads(spec[key].limits)
        if spec[key].ui_options:
            item['ui_options'] = json.loads(spec[key].ui_options)
        else:
            item['ui_options'] = None
        item['read_only'] = bool(config_is_ro(obj, key, spec[key].limits))
        item['activatable'] = bool(group_is_activatable(spec[key]))
        item['default'] = get_default(spec[key])
        if key in flat_conf:
            item['value'] = flat_conf[key]
        else:
            item['value'] = get_default(spec[key])
        conf.append(item)
    return conf


def config_is_ro(obj, key, limits):
    if not limits:
        return False
    if not hasattr(obj, 'state'):
        return False
    jslimits = json.loads(limits)
    ro = jslimits.get('read_only', [])
    wr = jslimits.get('writable', [])
    if ro and wr:
        msg = 'can not have "read_only" and "writable" simultaneously (config key "{}" of {})'
        err('INVALID_CONFIG_DEFINITION', msg.format(key, proto_ref(obj.prototype)))
    if ro == 'any':
        return True
    if obj.state in ro:
        return True
    if wr == 'any':
        return False
    if wr and obj.state not in wr:
        return True
    return False


def check_read_only(obj, spec, conf, old_conf):
    flat_conf = to_flat_dict(conf, spec)
    flat_old_conf = to_flat_dict(old_conf, spec)
    for s in spec:
        if config_is_ro(obj, s, spec[s].limits) and s in flat_conf:
            if flat_conf[s] != flat_old_conf[s]:
                msg = 'config key {} of {} is read only'
                err('CONFIG_VALUE_ERROR', msg.format(s, proto_ref(obj.prototype)))


def restore_read_only(obj, spec, conf, old_conf):
    for key in spec:   # pylint: disable=too-many-nested-blocks
        if 'type' in spec[key]:
            if config_is_ro(obj, key, spec[key]['limits']) and key not in conf:
                if key in old_conf:
                    conf[key] = old_conf[key]
        else:
            for subkey in spec[key]:
                if config_is_ro(obj, key + "/" + subkey, spec[key][subkey]['limits']):
                    if key in conf:
                        if subkey not in conf:
                            if key in old_conf and subkey in old_conf[key]:
                                conf[key][subkey] = old_conf[key][subkey]
                    elif key in old_conf and subkey in old_conf[key]:
                        conf[key] = {subkey: old_conf[key][subkey]}
    return conf


def check_json_config(proto, obj, new_conf, old_conf=None, attr=None):
    spec, flat_spec, _, _ = get_prototype_config(proto)
    check_attr(proto, attr, flat_spec)
    return check_config_spec(proto, obj, spec, flat_spec, new_conf, old_conf, attr)


def check_attr(proto, attr, spec):
    if not attr:
        return
    ref = proto_ref(proto)
    allowed_key = ('active', )
    if not isinstance(attr, dict):
        err('ATTRIBUTE_ERROR', 'Attr should be a map')
    for key in attr:
        if key + '/' not in spec:
            msg = 'There isn\'t group "{}" in config ({})'
            err('ATTRIBUTE_ERROR', msg.format(key, ref))
        if spec[key + '/'].type != 'group':
            msg = 'Config key "{}" is not a group ({})'
            err('ATTRIBUTE_ERROR', msg.format(key, ref))
        if not isinstance(attr[key], dict):
            msg = 'Value of attribute "{}" should be a map ({})'
            err('ATTRIBUTE_ERROR', msg.format(key, ref))
        for attr_key in attr[key]:
            if attr_key not in allowed_key:
                msg = 'Not allowed key "{}" of attribute "{}" ({})'
                err('ATTRIBUTE_ERROR', msg.format(attr_key, key, ref))
        if 'active' in attr[key]:
            if not isinstance(attr[key]['active'], bool):
                msg = 'Value of key "{}" of attribute "{}" should be boolean ({})'
                err('ATTRIBUTE_ERROR', msg.format('active', key, ref))


def check_config_spec(proto, obj, spec, flat_spec, conf, old_conf=None, attr=None):   # pylint: disable=too-many-branches,too-many-statements
    ref = proto_ref(proto)
    if isinstance(conf, (float, int)):
        err('JSON_ERROR', 'config should not be just one int or float')

    if isinstance(conf, str):
        err('JSON_ERROR', 'config should not be just one string')

    def key_is_required(key, subkey, spec):
        if config_is_ro(obj, '{}/{}'.format(key, subkey), spec.get('limits', '')):
            return False
        if spec['required']:
            return True
        return False

    def is_inactive(key):
        if attr and flat_spec[key + '/'].type == 'group':
            if key in attr and 'active' in attr[key]:
                return not bool(attr[key]['active'])
        return False

    def check_sub(key):
        if not isinstance(conf[key], dict):
            msg = 'There are not any subkeys for key "{}" ({})'
            err('CONFIG_KEY_ERROR', msg.format(key, ref))
        if not conf[key]:
            msg = 'Key "{}" should contains some subkeys ({})'
            err('CONFIG_KEY_ERROR', msg.format(key, ref))
        for subkey in conf[key]:
            if subkey not in spec[key]:
                msg = 'There is unknown subkey "{}" for key "{}" in input config ({})'
                err('CONFIG_KEY_ERROR', msg.format(subkey, key, ref))
        for subkey in spec[key]:
            if subkey in conf[key]:
                check_config_type(
                    ref, key, subkey, spec[key][subkey], conf[key][subkey], False, is_inactive(key)
                )
            elif key_is_required(key, subkey, spec[key][subkey]):
                msg = 'There is no required subkey "{}" for key "{}" ({})'
                err('CONFIG_KEY_ERROR', msg.format(subkey, key, ref))

    def sub_key_is_required(key):
        if is_inactive(key):
            return False
        for subkey in spec[key]:
            if key_is_required(key, subkey, spec[key][subkey]):
                return True
        return False

    for key in conf:
        if key not in spec:
            msg = 'There is unknown key "{}" in input config ({})'
            err('CONFIG_KEY_ERROR', msg.format(key, ref))
        if 'type' in spec[key] and spec[key]['type'] != 'group':
            if isinstance(conf[key], dict) and not type_is_complex(spec[key]['type']):
                msg = 'Key "{}" in input config should not have any subkeys ({})'
                err('CONFIG_KEY_ERROR', msg.format(key, ref))

    for key in spec:
        if 'type' in spec[key] and spec[key]['type'] != 'group':
            if key in conf:
                check_config_type(ref, key, '', spec[key], conf[key])
            elif key_is_required(key, '', spec[key]):
                msg = 'There is no required key "{}" in input config ({})'
                err('CONFIG_KEY_ERROR', msg.format(key, ref))
        else:
            if key not in conf:
                if sub_key_is_required(key):
                    msg = 'There are no required key "{}" in input config'
                    err('CONFIG_KEY_ERROR', msg.format(key))
            else:
                check_sub(key)

    if old_conf:
        check_read_only(obj, flat_spec, conf, json.loads(old_conf))
        restore_read_only(obj, spec, conf, json.loads(old_conf))
        process_file_type(obj, spec, conf)
    return conf


def check_config_type(ref, key, subkey, spec, value, default=False, inactive=False):   # pylint: disable=too-many-branches,too-many-statements,too-many-locals
    if default:
        label = 'Default value'
    else:
        label = 'Value'
    tmpl1 = f'{label} of config key "{key}/{subkey}" {{}} ({ref})'
    tmpl2 = f'{label} ("{value}") of config key "{key}/{subkey}" {{}} ({ref})'

    def check_str(idx, v):
        if not isinstance(v, str):
            msg = (
                f'{label} ("{v}") of element "{idx}" of config key "{key}/{subkey}"'
                f' should be string ({ref})'
            )
            err('CONFIG_VALUE_ERROR', msg)

    def get_limits():
        if default:
            return spec['limits']
        else:
            return json.loads(spec['limits'])

    if value is None:
        if inactive:
            return
        if 'required' in spec and spec['required']:
            err('CONFIG_VALUE_ERROR', tmpl1.format("is required"))
        else:
            return

    if isinstance(value, (list, dict)) and not type_is_complex(spec['type']):
        if spec['type'] != 'group':
            err('CONFIG_VALUE_ERROR', tmpl1.format("should be flat"))

    if spec['type'] == 'list':
        if not isinstance(value, list):
            err('CONFIG_VALUE_ERROR', tmpl1.format("should be an array"))
        for idx, v in enumerate(value):
            check_str(idx, v)

    if spec['type'] == 'map':
        if not isinstance(value, dict):
            err('CONFIG_VALUE_ERROR', tmpl1.format("should be a map"))
        for k, v in value.items():
            check_str(k, v)

    if spec['type'] in ('string', 'password', 'text'):
        if not isinstance(value, str):
            err('CONFIG_VALUE_ERROR', tmpl2.format("should be string"))
        if value == '':
            err('CONFIG_VALUE_ERROR', tmpl1.format("should be not empty"))

    if spec['type'] == 'file':
        if not isinstance(value, str):
            err('CONFIG_VALUE_ERROR', tmpl2.format("should be string"))
        if value == '':
            err('CONFIG_VALUE_ERROR', tmpl1.format("should be not empty"))
        if default:
            if len(value) > 2048:
                err('CONFIG_VALUE_ERROR', tmpl1.format("is too long"))
            read_file_type(value, ref, default, key, subkey)

    if spec['type'] == 'structure':
        schema = get_limits()['yspec']
        try:
            yspec.checker.process_rule(value, schema, 'root')
        except yspec.checker.FormatError as e:
            msg = tmpl1.format("yspec error: {} at block {}".format(str(e), e.data))
            err('CONFIG_VALUE_ERROR', msg)

    if spec['type'] == 'boolean':
        if not isinstance(value, bool):
            err('CONFIG_VALUE_ERROR', tmpl2.format("should be boolean"))

    if spec['type'] == 'integer':
        if not isinstance(value, int):
            err('CONFIG_VALUE_ERROR', tmpl2.format("should be integer"))

    if spec['type'] == 'float':
        if not isinstance(value, (int, float)):
            err('CONFIG_VALUE_ERROR', tmpl2.format("should be float"))

    if spec['type'] == 'integer' or spec['type'] == 'float':
        if 'limits' in spec:
            limits = get_limits()
            if 'min' in limits:
                if value < limits['min']:
                    msg = 'should be more than {}'.format(limits['min'])
                    err('CONFIG_VALUE_ERROR', tmpl2.format(msg))
            if 'max' in limits:
                if value > limits['max']:
                    msg = 'should be less than {}'.format(limits['max'])
                    err('CONFIG_VALUE_ERROR', tmpl2.format(msg))

    if spec['type'] == 'option':
        option = get_limits()['option']
        check = False
        for _, v in option.items():
            if v == value:
                check = True
                break
        if not check:
            msg = 'not in option list: "{}"'.format(option)
            err('CONFIG_VALUE_ERROR', tmpl2.format(msg))


def replace_object_config(obj, key, subkey, value):
    cl = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
    conf = json.loads(cl.config)
    if subkey:
        conf[key][subkey] = value
    else:
        conf[key] = value
    save_obj_config(obj.config, conf, 'ansible update', cl.attr)


def set_cluster_config(cluster_id, keys, value):
    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        msg = 'Cluster # {} does not exist'
        err('CLUSTER_NOT_FOUND', msg.format(cluster_id))
    return set_object_config(cluster, keys, value)


def set_host_config(host_id, keys, value):
    try:
        host = Host.objects.get(id=host_id)
    except Host.DoesNotExist:
        msg = 'Host # {} does not exist'
        err('HOST_NOT_FOUND', msg.format(host_id))
    return set_object_config(host, keys, value)


def set_provider_config(provider_id, keys, value):
    try:
        provider = HostProvider.objects.get(id=provider_id)
    except HostProvider.DoesNotExist:
        msg = 'Host # {} does not exist'
        err('PROVIDER_NOT_FOUND', msg.format(provider_id))
    return set_object_config(provider, keys, value)


def set_service_config(cluster_id, service_name, keys, value):
    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        msg = 'Cluster # {} does not exist'
        err('CLUSTER_NOT_FOUND', msg.format(cluster_id))
    try:
        proto = Prototype.objects.get(
            type='service', name=service_name, bundle=cluster.prototype.bundle
        )
    except Prototype.DoesNotExist:
        msg = 'Service "{}" does not exist'
        err('SERVICE_NOT_FOUND', msg.format(service_name))
    try:
        obj = ClusterObject.objects.get(cluster=cluster, prototype=proto)
    except ClusterObject.DoesNotExist:
        msg = '{} does not exist in cluster # {}'
        err('OBJECT_NOT_FOUND', msg.format(proto_ref(proto), cluster.id))
    return set_object_config(obj, keys, value)


def set_service_config_by_id(cluster_id, service_id, keys, value):
    try:
        obj = ClusterObject.objects.get(
            id=service_id, cluster__id=cluster_id, prototype__type='service'
        )
    except ClusterObject.DoesNotExist:
        msg = 'service # {} does not exist in cluster # {}'
        err('OBJECT_NOT_FOUND', msg.format(service_id, cluster_id))
    return set_object_config(obj, keys, value)


def set_object_config(obj, keys, value):
    proto = obj.prototype
    try:
        spl = keys.split('/')
        key = spl[0]
        if len(spl) == 1:
            subkey = ''
        else:
            subkey = spl[1]
        pconf = PrototypeConfig.objects.get(prototype=proto, action=None, name=key, subname=subkey)
    except PrototypeConfig.DoesNotExist:
        msg = '{} does not has config key "{}/{}"'
        err('CONFIG_NOT_FOUND', msg.format(proto_ref(proto), key, subkey))

    ref = proto_ref(obj.prototype)
    check_config_type(ref, key, subkey, obj_to_dict(pconf, ('type', 'limits', 'option')), value)
    # if config_is_ro(obj, keys, pconf.limits):
    #    msg = 'config key {} of {} is read only'
    #    err('CONFIG_VALUE_ERROR', msg.format(key, ref))
    replace_object_config(obj, key, subkey, value)
    if pconf.type == 'file':
        save_file_type(obj, key, subkey, value)
    log.info('update %s config %s/%s to "%s"', obj_ref(obj), key, subkey, value)
    return value
