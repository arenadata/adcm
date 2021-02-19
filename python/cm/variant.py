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

from cm.logger import log
from cm.errors import AdcmEx
from cm.errors import raise_AdcmEx as err
from cm.models import Prototype, ClusterObject, ServiceComponent, HostComponent, Host


def get_cluster(obj):
    if obj.prototype.type == 'service':
        cluster = obj.cluster
    elif obj.prototype.type == 'host':
        cluster = obj.cluster
    elif obj.prototype.type == 'cluster':
        cluster = obj
    else:
        return None
    return cluster


def variant_service_in_cluster(obj, args=None):
    out = []
    cluster = get_cluster(obj)
    if not cluster:
        return []

    for co in ClusterObject.objects.filter(cluster=cluster).order_by('prototype__name'):
        out.append(co.prototype.name)
    return out


def variant_service_to_add(obj, args=None):
    out = []
    cluster = get_cluster(obj)
    if not cluster:
        return []

    for proto in Prototype.objects \
            .filter(bundle=cluster.prototype.bundle, type='service') \
            .exclude(id__in=ClusterObject.objects.filter(cluster=cluster).values('prototype')) \
            .order_by('name'):
        out.append(proto.name)
    return out


def var_host_and(cluster, args):
    if not isinstance(args, list):
        err('CONFIG_VARIANT_ERROR', 'arguments of "and" predicate should be a list')
    if not args:
        return []
    return sorted(list(set.intersection(*[set(a) for a in args])))


def var_host_or(cluster, args):
    if not isinstance(args, list):
        err('CONFIG_VARIANT_ERROR', 'arguments of "or" predicate should be a list')
    if not args:
        return []
    return sorted(list(set.union(*[set(a) for a in args])))


def var_host_in_service(cluster, args):
    out = []
    func = 'in_service'
    if 'service' not in args:
        err('CONFIG_VARIANT_ERROR', f'no "service" tuple for predicate "{func}"')
    try:
        service = ClusterObject.objects.get(cluster=cluster, prototype__name=args['service'])
    except ClusterObject.DoesNotExist:
        err('CONFIG_VARIANT_ERROR', 'service "{}" is not found'.format(args['service']))
    for hc in HostComponent.objects \
            .filter(cluster=cluster, service=service) \
            .order_by('host__fqdn'):
        out.append(hc.host.fqdn)
    return out


def var_host_in_cluster(cluster, args):
    out = []
    for host in Host.objects.filter(cluster=cluster).order_by('fqdn'):
        out.append(host.fqdn)
    return out


def var_host_in_component(cluster, args):
    out = []
    func = 'in_component'
    if 'service' not in args:
        err('CONFIG_VARIANT_ERROR', f'no "service" tuple for predicate "{func}"')
    if 'component' not in args:
        err('CONFIG_VARIANT_ERROR', f'no "component" tuple for predicate "{func}"')
    try:
        service = ClusterObject.objects.get(cluster=cluster, prototype__name=args['service'])
    except ClusterObject.DoesNotExist:
        err('CONFIG_VARIANT_ERROR', 'service "{}" is not found'.format(args['service']))
    try:
        comp = ServiceComponent.objects.get(
            cluster=cluster, service=service, prototype__name=args['component']
        )
    except ServiceComponent.DoesNotExist:
        err('CONFIG_VARIANT_ERROR', 'component "{}" is not found'.format(args['component']))
    for hc in HostComponent.objects \
            .filter(cluster=cluster, service=service, component=comp) \
            .order_by('host__fqdn'):
        out.append(hc.host.fqdn)
    return out


def var_host_in_hc(cluster, args):
    out = []
    for hc in HostComponent.objects.filter(cluster=cluster).order_by('host__fqdn'):
        out.append(hc.host.fqdn)
    return out


def var_host_not_in_hc(cluster, args):
    out = []
    for host in Host.objects.filter(cluster=cluster).order_by('fqdn'):
        if HostComponent.objects.filter(cluster=cluster, host=host):
            continue
        out.append(host.fqdn)
    return out


def var_host_not_in_component(cluster, args):
    return []


def var_host_inline_list(cluster, args):
    return args['list']


VARIANT_HOST_FUNC = {
    'and': var_host_and,
    'or': var_host_or,
    'in_cluster': var_host_in_cluster,
    'in_service': var_host_in_service,
    'in_component': var_host_in_component,
    'not_in_component': var_host_not_in_component,
    'in_hc': var_host_in_hc,
    'not_in_hc': var_host_not_in_hc,
    'inline_list': var_host_inline_list,
}


def var_host_solver(cluster, func_map, args):
    def check_key(key, args):
        if not isinstance(args, dict):
            err('CONFIG_VARIANT_ERROR', 'predicte item should be a map')
        if key not in args:
            err('CONFIG_VARIANT_ERROR', f'no "{key}" key in solver args')

    log.debug('QQ solver args: %s', args)
    if args is None:
        return None
    if isinstance(args, dict):
        if 'predicate' not in args:
            log.debug('QQ solver res1: %s', args)
            return args
        else:
            predicate = args['predicate']
            if predicate not in func_map:
                err('CONFIG_VARIANT_ERROR', f'no "{predicate}" in list of host functions')
            check_key('args', args)
            res = func_map[predicate](cluster, var_host_solver(cluster, func_map, args['args']))
            log.debug('QQ solver res2: %s', res)
            return res

    res = []
    if not isinstance(args, list):
        err('CONFIG_VARIANT_ERROR', 'arguments of solver should be a list or a map')
    for item in args:
        check_key('predicate', item)
        check_key('args', item)
        predicate = item['predicate']
        if predicate not in func_map:
            err('CONFIG_VARIANT_ERROR', f'no "{predicate}" in list of host functions')
        res.append(func_map[predicate](cluster, var_host_solver(cluster, func_map, item['args'])))

    log.debug('QQ solver res3: %s', res)
    return res


def variant_host(obj, args=None):
    cluster = get_cluster(obj)
    if not cluster:
        return []
    if not isinstance(args, dict):
        err('CONFIG_VARIANT_ERROR', 'arguments of variant host function should be a map')
    if 'predicate' not in args:
        err('CONFIG_VARIANT_ERROR', 'no "predicate" key in variant host function arguments')
    res = var_host_solver(cluster, VARIANT_HOST_FUNC, args)
    return res


def variant_host_in_cluster(obj, args=None):
    out = []
    cluster = get_cluster(obj)
    if not cluster:
        return []

    if args and 'service' in args:
        try:
            service = ClusterObject.objects.get(cluster=cluster, prototype__name=args['service'])
        except ClusterObject.DoesNotExist:
            return []
        if 'component' in args:
            try:
                comp = ServiceComponent.objects.get(
                    cluster=cluster, service=service, prototype__name=args['component']
                )
            except ServiceComponent.DoesNotExist:
                return []
            for hc in HostComponent.objects \
                    .filter(cluster=cluster, service=service, component=comp) \
                    .order_by('host__fqdn'):
                out.append(hc.host.fqdn)
            return out
        else:
            for hc in HostComponent.objects \
                    .filter(cluster=cluster, service=service) \
                    .order_by('host__fqdn'):
                out.append(hc.host.fqdn)
            return out

    for host in Host.objects.filter(cluster=cluster).order_by('fqdn'):
        out.append(host.fqdn)
    return out


def variant_host_not_in_clusters(obj, args=None):
    out = []
    for host in Host.objects.filter(cluster=None).order_by('fqdn'):
        out.append(host.fqdn)
    return out


VARIANT_FUNCTIONS = {
    'host': variant_host,
    'host_in_cluster': variant_host_in_cluster,
    'host_not_in_clusters': variant_host_not_in_clusters,
    'service_in_cluster': variant_service_in_cluster,
    'service_to_add': variant_service_to_add,
}


def get_builtin_variant(obj, func_name, args):
    if func_name not in VARIANT_FUNCTIONS:
        log.warning('unknown variant builtin function: %s', func_name)
        return None
    try:
        return VARIANT_FUNCTIONS[func_name](obj, args)
    except AdcmEx as e:
        if e.code == 'CONFIG_VARIANT_ERROR':
            return []
        raise e


def get_variant(obj, conf, limits):
    value = None
    source = limits['source']
    if source['type'] == 'config':
        skey = source['name'].split('/')
        if len(skey) == 1:
            value = conf[skey[0]]
        else:
            value = conf[skey[0]][skey[1]]
    elif source['type'] == 'builtin':
        value = get_builtin_variant(obj, source['name'], source.get('args', None))
    elif source['type'] == 'inline':
        value = source['value']
    return value


def process_variant(obj, spec, conf):
    def set_variant(spec):
        limits = spec['limits']
        limits['source']['value'] = get_variant(obj, conf, limits)
        return limits

    for key in spec:
        if 'type' in spec[key]:
            if spec[key]['type'] == 'variant':
                spec[key]['limits'] = set_variant(spec[key])
        else:
            for subkey in spec[key]:
                if spec[key][subkey]['type'] == 'variant':
                    spec[key][subkey]['limits'] = set_variant(spec[key][subkey])
