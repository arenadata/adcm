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

import json

from cm.logger import log   # pylint: disable=unused-import
import cm.status_api
from cm.errors import AdcmApiEx
from cm.errors import raise_AdcmEx as err
from cm.adcm_config import proto_ref, obj_ref, get_prototype_config
from cm.models import ConfigLog, Host, ClusterObject, Prototype, Component, HostComponent
from cm.models import PrototypeImport, ClusterBind


def save_issue(obj):
    if obj.prototype.type == 'adcm':
        return
    obj.issue = json.dumps(check_issue(obj))
    obj.save()
    report_issue(obj)


def report_issue(obj):
    issue = get_issue(obj)
    if issue_to_bool(issue):
        cm.status_api.post_event('clear_issue', obj.prototype.type, obj.id)
    else:
        cm.status_api.post_event('raise_issue', obj.prototype.type, obj.id, 'issue', issue)


def check_issue(obj):
    disp = {
        'cluster': check_cluster_issue,
        'service': check_obj_issue,
        'provider': check_obj_issue,
        'host': check_obj_issue,
        'adcm': check_adcm_issue,
    }
    if obj.prototype.type not in disp:
        err('NOT_IMPLEMENTED', 'unknown object type')
    issue = disp[obj.prototype.type](obj)
    log.debug('%s issue: %s', obj_ref(obj), issue)
    return issue


def issue_to_bool(issue):
    if isinstance(issue, dict):
        for key in issue:
            if not issue_to_bool(issue[key]):
                return False
    elif isinstance(issue, list):
        for val in issue:
            if not issue_to_bool(val):
                return False
    elif not issue:
        return False
    return True


def get_issue(obj):   # pylint: disable=too-many-branches
    issue = json.loads(obj.issue)
    if obj.prototype.type == 'cluster':
        issue['service'] = []
        for co in ClusterObject.objects.filter(cluster=obj):
            service_iss = cook_issue(co, name_obj=co.prototype)
            if service_iss:
                issue['service'].append(service_iss)
        if not issue['service']:
            del issue['service']
        issue['host'] = []
        for host in Host.objects.filter(cluster=obj):
            host_iss = cook_issue(host, 'fqdn')
            provider_iss = cook_issue(host.provider)
            if host_iss:
                if provider_iss:
                    host_iss['issue']['provider'] = provider_iss
                issue['host'].append(host_iss)
            elif provider_iss:
                issue['host'].append(cook_issue(host, 'fqdn', iss={'provider': [provider_iss]}))
        if not issue['host']:
            del issue['host']

    elif obj.prototype.type == 'service':
        cluster_iss = cook_issue(obj.cluster)
        if cluster_iss:
            issue['cluster'] = [cluster_iss]

    elif obj.prototype.type == 'host':
        if obj.cluster:
            cluster_iss = cook_issue(obj.cluster)
            if cluster_iss:
                issue['cluster'] = [cluster_iss]
        if obj.provider:
            provider_iss = cook_issue(obj.provider)
            if provider_iss:
                issue['provider'] = [provider_iss]
    return issue


def cook_issue(obj, name='name', name_obj=None, iss=None):
    if not name_obj:
        name_obj = obj
    if not iss:
        if obj:
            iss = json.loads(obj.issue)
        else:
            iss = {}
    if iss:
        return {
            'id': obj.id,
            'name': getattr(name_obj, name),
            'issue': iss,
        }
    return None


def check_cluster_issue(cluster):
    issue = {}
    if not check_config(cluster):
        issue['config'] = False
    if not check_required_services(cluster):
        issue['required_service'] = False
    if not check_required_import(cluster):
        issue['required_import'] = False
    if not check_hc(cluster):
        issue['host_component'] = False
    return issue


def check_obj_issue(obj):
    if not check_config(obj):
        return {'config': False}
    return {}


def check_adcm_issue(obj):
    return {}


def check_config(obj):   # pylint: disable=too-many-branches
    spec, _, _, _ = get_prototype_config(obj.prototype)
    conf, attr = get_obj_config(obj)
    for key in spec:   # pylint: disable=too-many-nested-blocks
        if 'required' in spec[key]:
            if spec[key]['required']:
                if key in conf and conf[key] is None:
                    log.debug('required config key %s of %s is missing', key, obj_ref(obj))
                    return False
        else:
            if key in attr:
                if 'active' in attr[key] and not attr[key]['active']:
                    continue
            for subkey in spec[key]:
                if spec[key][subkey]['required']:
                    if key not in conf:
                        log.debug('required config group %s of %s is missing', key, obj_ref(obj))
                        return False
                    if subkey in conf[key]:
                        if conf[key][subkey] is None:
                            msg = 'required config value for key %s/%s of %s is missing'
                            log.debug(msg, key, subkey, obj_ref(obj))
                            return False
                    else:
                        msg = 'required config key %s/%s of %s is missing'
                        log.debug(msg, key, subkey, obj_ref(obj))
                        return False
    return True


def check_required_services(cluster):
    bundle = cluster.prototype.bundle
    for proto in Prototype.objects.filter(bundle=bundle, type='service', required=True):
        try:
            ClusterObject.objects.get(cluster=cluster, prototype=proto)
        except ClusterObject.DoesNotExist:
            log.debug('required service %s of %s is missing', proto_ref(proto), obj_ref(cluster))
            return False
    return True


def check_required_import(cluster):
    def check_import(pi):
        if not pi.required:
            return True
        import_exist = False
        for cb in ClusterBind.objects.filter(cluster=cluster):
            if cb.source_cluster and cb.source_cluster.prototype.name == pi.name:
                import_exist = True
            if cb.source_service and cb.source_service.prototype.name == pi.name:
                import_exist = True
        return import_exist

    for pi in PrototypeImport.objects.filter(prototype=cluster.prototype):
        if not check_import(pi):
            return False

    for co in ClusterObject.objects.filter(cluster=cluster):
        for pi in PrototypeImport.objects.filter(prototype=co.prototype):
            if not check_import(pi):
                return False

    return True


def check_hc(cluster):
    hc_list = []
    for hc in HostComponent.objects.filter(cluster=cluster):
        hc_list.append((hc.service, hc.host, hc.component))

    if not hc_list:
        for co in ClusterObject.objects.filter(cluster=cluster):
            for comp in Component.objects.filter(prototype=co.prototype):
                if not comp.constraint:
                    continue
                const = json.loads(comp.constraint)
                if not const:
                    continue
                if len(const) == 2 and const[0] == 0 and const[1] == '+':
                    continue
                log.debug('void host components for %s', proto_ref(co.prototype))
                return False

    for service in ClusterObject.objects.filter(cluster=cluster):
        try:
            check_component_constraint(service, [i for i in hc_list if i[0] == service])
        except AdcmApiEx:
            return False
    return True


def get_obj_config(obj):
    if obj.config is None:
        return ({}, {})
    cl = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
    attr = {}
    if cl.attr:
        attr = json.loads(cl.attr)
    return (json.loads(cl.config), attr)


def check_component_constraint(service, hc_in):
    ref = 'in host component list for {}'.format(obj_ref(service))
    all_host = Host.objects.filter(cluster=service.cluster)

    def cc_err(msg):
        raise AdcmApiEx('COMPONENT_CONSTRAINT_ERROR', msg)

    def check_min(count, const, comp):
        if count < const:
            msg = 'less then {} required component "{}" ({}) {}'
            cc_err(msg.format(const, comp.name, count, ref))

    def check_max(count, const, comp):
        if count > const:
            msg = 'amount ({}) of component "{}" more then maximum ({}) {}'
            cc_err(msg.format(count, comp.name, const, ref))

    def check_odd(count, const, comp):
        if count % 2 == 0:
            msg = 'amount ({}) of component "{}" should be odd ({}) {}'
            cc_err(msg.format(count, comp.name, const, ref))

    def check(comp, const):
        count = 0
        for (_, _, c) in hc_in:
            if comp.name == c.component.name:
                count += 1

        if isinstance(const[0], int):
            check_min(count, const[0], comp)
            if len(const) < 2:
                check_max(count, const[0], comp)

        if len(const) > 1:
            if isinstance(const[1], int):
                check_max(count, const[1], comp)
            elif const[1] == 'odd' and count:
                check_odd(count, const[1], comp)

        if const[0] == '+':
            check_min(count, len(all_host), comp)
        elif const[0] == 'odd':
            check_odd(count, const[0], comp)

    for c in Component.objects.filter(prototype=service.prototype):
        if not c.constraint:
            continue
        const = json.loads(c.constraint)
        check(c, const)
