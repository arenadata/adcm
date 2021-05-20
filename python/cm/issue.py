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

from collections import defaultdict

import cm.status_api
from cm.adcm_config import proto_ref, obj_ref, get_prototype_config
from cm.errors import AdcmEx, raise_AdcmEx as err
from cm.hierarchy import Tree
from cm.logger import log
from cm.models import (
    ADCMModel,
    ClusterBind,
    ClusterObject,
    ConfigLog,
    Host,
    HostComponent,
    Prototype,
    PrototypeImport,
)


class IssueReporter:
    """Cache, compare, and report updated issues"""

    def __init__(self, obj: ADCMModel):
        self.tree = Tree(obj)
        self._cache = {}

    def update_issues(self):
        for node in self.tree.get_directly_affected(self.tree.built_from):
            self._cache[node.key] = aggregate_issues(node.value, self.tree)

            obj = node.value
            issue = check_for_issue(obj)
            if obj.issue != issue:
                obj.issue = issue
                obj.save()

    def report_changed(self):
        for node in self.tree.get_directly_affected(self.tree.built_from):
            new_issue = aggregate_issues(node.value, self.tree)
            old_issue = self._cache[node.key]
            if new_issue != old_issue:
                if issue_to_bool(new_issue):
                    cm.status_api.post_event('clear_issue', node.type, node.id)
                else:
                    cm.status_api.post_event('raise_issue', node.type, node.id, 'issue', new_issue)


def update_hierarchy_issues(obj: ADCMModel):
    """Update issues on all directly connected objects"""
    reporter = IssueReporter(obj)
    reporter.update_issues()
    reporter.report_changed()


def check_for_issue(obj: ADCMModel):
    type_check_map = {
        'cluster': check_cluster_issue,
        'service': check_service_issue,
        'component': check_config_issue,
        'provider': check_config_issue,
        'host': check_config_issue,
        'adcm': lambda x: {},
    }
    if obj.prototype.type not in type_check_map:
        err('NOT_IMPLEMENTED', 'unknown object type')
    issue = {k: v for k, v in type_check_map[obj.prototype.type](obj).items() if v is False}
    log.debug('%s issue: %s', obj_ref(obj), issue)
    return issue


def issue_to_bool(issue):
    if isinstance(issue, dict):
        return all(map(issue_to_bool, issue.values()))
    elif isinstance(issue, list):
        return all(map(issue_to_bool, issue))
    else:
        return bool(issue)


def aggregate_issues(obj: ADCMModel, tree: Tree = None) -> dict:
    """
    Get own issue extended with issues of all nested objects
    TODO: unify behavior for hosts (in `Host.serialized_issue`) and providers
    """
    issue = defaultdict(list)
    issue.update(obj.issue)

    if obj.prototype.type == 'provider':
        return issue

    tree = tree or Tree(obj)
    node = tree.get_node(obj)
    for child in tree.get_directly_affected(node):
        if child.key == node.key:  # skip itself
            continue

        if obj.prototype.type == 'provider':
            continue

        child_issue = child.value.serialized_issue
        if child_issue:
            issue[child.type].append(child_issue)

    return issue


def check_cluster_issue(cluster):
    return {
        'config': check_config(cluster),
        'required_service': check_required_services(cluster),
        'required_import': check_required_import(cluster),
        'host_component': check_hc(cluster),
    }


def check_service_issue(service):
    return {
        'config': check_config(service),
        'required_import': check_required_import(service.cluster, service)
    }


def check_config_issue(obj):
    return {'config': check_config(obj)}


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


def check_required_import(cluster, service=None):
    res, code = do_check_import(cluster, service)
    log.debug('do_check_import result: %s, code: %s', res, code)
    return res


def do_check_import(cluster, service=None):
    def check_import(pi):
        if not pi.required:
            return (True, 'NOT_REQIURED')
        import_exist = (False, None)
        for cb in ClusterBind.objects.filter(cluster=cluster):
            if cb.source_cluster and cb.source_cluster.prototype.name == pi.name:
                import_exist = (True, 'CLUSTER_IMPORTED')
            if cb.source_service and cb.source_service.prototype.name == pi.name:
                import_exist = (True, 'SERVICE_IMPORTED')
        return import_exist

    res = (True, None)
    proto = cluster.prototype
    if service:
        proto = service.prototype
    for pi in PrototypeImport.objects.filter(prototype=proto):
        res = check_import(pi)
        if not res[0]:
            return res

    return res


def check_hc(cluster):
    shc_list = []
    for hc in HostComponent.objects.filter(cluster=cluster):
        shc_list.append((hc.service, hc.host, hc.component))

    if not shc_list:
        for co in ClusterObject.objects.filter(cluster=cluster):
            for comp in Prototype.objects.filter(parent=co.prototype, type='component'):
                const = comp.constraint
                if len(const) == 2 and const[0] == 0 and const[1] == '+':
                    continue
                log.debug('void host components for %s', proto_ref(co.prototype))
                return False

    for service in ClusterObject.objects.filter(cluster=cluster):
        try:
            check_component_constraint(service, [i for i in shc_list if i[0] == service])
        except AdcmEx:
            return False
    try:
        check_component_requires(shc_list)
        check_bound_components(shc_list)
    except AdcmEx:
        return False
    return True


def check_component_requires(shc_list):
    def get_components_with_requires():
        return [i for i in shc_list if i[2].prototype.requires]

    def check_component_req(service, component):
        for shc in shc_list:
            if shc[0].prototype.name == service and shc[2].prototype.name == component:
                return True
        return False

    for shc in get_components_with_requires():
        for r in shc[2].prototype.requires:
            if not check_component_req(r['service'], r['component']):
                ref = f'component "{shc[2].prototype.name}" of service "{shc[0].prototype.name}"'
                msg = 'no required component "{}" of service "{}" for {}'
                err('COMPONENT_CONSTRAINT_ERROR', msg.format(r['component'], r['service'], ref))


def check_bound_components(shc_list):
    def get_components_bound_to():
        return [i for i in shc_list if i[2].prototype.bound_to]

    def component_on_host(component, host):
        return [i for i in shc_list if i[1] == host and i[2].prototype == component]

    def bound_host_components(service, comp):
        return [
            i for i in shc_list if i[0].prototype.name == service and i[2].prototype.name == comp
        ]

    def check_bound_component(component):
        service = component.bound_to['service']
        comp_name = component.bound_to['component']
        ref = f'component "{comp_name}" of service "{service}"'
        bound_hc = bound_host_components(service, comp_name)
        if not bound_hc:
            msg = f'bound service "{service}", component "{comp_name}" not in hc for {ref}'
            err('COMPONENT_CONSTRAINT_ERROR', msg)
        for shc in bound_hc:
            if not component_on_host(component, shc[1]):
                msg = 'No bound component "{}" on host "{}" for {}'
                err('COMPONENT_CONSTRAINT_ERROR', msg.format(component.name, shc[1].fqdn, ref))

    for shc in get_components_bound_to():
        check_bound_component(shc[2].prototype)


def get_obj_config(obj):
    if obj.config is None:
        return ({}, {})
    cl = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
    attr = cl.attr
    if not attr:
        attr = {}
    return (cl.config, attr)


def check_component_constraint(service, hc_in):
    ref = 'in host component list for {}'.format(obj_ref(service))
    all_host = Host.objects.filter(cluster=service.cluster)

    def cc_err(msg):
        raise AdcmEx('COMPONENT_CONSTRAINT_ERROR', msg)

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
            if comp.name == c.prototype.name:
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

    for c in Prototype.objects.filter(parent=service.prototype, type='component'):
        check(c, c.constraint)
