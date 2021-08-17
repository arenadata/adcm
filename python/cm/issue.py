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

from cm.adcm_config import proto_ref, obj_ref, get_prototype_config
from cm.errors import AdcmEx, raise_AdcmEx as err
from cm.hierarchy import Tree
from cm.logger import log
from cm.models import (
    ADCMEntity,
    Cluster,
    ClusterBind,
    ClusterObject,
    ConcernItem,
    ConcernType,
    ConfigLog,
    Host,
    HostComponent,
    IssueType,
    MessageTemplate as MsgTpl,
    PrototypeEnum,
    Prototype,
    PrototypeImport,
)


def check_config(obj):  # pylint: disable=too-many-branches
    spec, _, _, _ = get_prototype_config(obj.prototype)
    conf, attr = get_obj_config(obj)
    for key, value in spec.items():  # pylint: disable=too-many-nested-blocks
        if 'required' in value:
            if value['required']:
                if key in conf and conf[key] is None:
                    log.debug('required config key %s of %s is missing', key, obj_ref(obj))
                    return False
        else:
            if key in attr:
                if 'active' in attr[key] and not attr[key]['active']:
                    continue
            for subkey in value:
                if value[subkey]['required']:
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


def check_required_import(obj: [Cluster, ClusterObject]):
    if obj.prototype.type == PrototypeEnum.Cluster.value:
        cluster = obj
        service = None
    elif obj.prototype.type == PrototypeEnum.Service.value:
        service = obj
        cluster = obj.cluster
    else:
        raise TypeError('Could not check import for %s' % obj)
    res, _ = do_check_import(cluster, service)
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


_issue_check_map = {
    IssueType.Config: check_config,
    IssueType.RequiredImport: check_required_import,
    IssueType.RequiredService: check_required_services,
    IssueType.HostComponent: check_hc,
}
_prototype_issue_map = {
    PrototypeEnum.ADCM.value: tuple(),
    PrototypeEnum.Cluster.value: (
        IssueType.Config,
        IssueType.RequiredImport,
        IssueType.RequiredService,
        IssueType.HostComponent,
    ),
    PrototypeEnum.Service.value: (IssueType.Config, IssueType.RequiredImport),
    PrototypeEnum.Component.value: (IssueType.Config,),
    PrototypeEnum.Provider.value: (IssueType.Config,),
    PrototypeEnum.Host.value: (IssueType.Config,),
}
_issue_type_name_map = {
    IssueType.Config: MsgTpl.KnownNames.ConfigIssue,
    IssueType.RequiredImport: MsgTpl.KnownNames.RequiredImportIssue,
    IssueType.RequiredService: MsgTpl.KnownNames.RequiredServiceIssue,
    IssueType.HostComponent: MsgTpl.KnownNames.HostComponentIssue,
}


def create_issue(obj: ADCMEntity, issue_type: IssueType) -> None:
    """Create newly discovered issue and add it to linked objects concerns"""
    if obj.get_own_issue(issue_type):
        return

    msg_name = _issue_type_name_map[issue_type]
    reason = MsgTpl.get_message_from_template(msg_name.value, source=obj)
    issue_name = issue_type.gen_issue_name(obj)
    issue = ConcernItem.objects.create(type=ConcernType.Issue, name=issue_name, reason=reason)

    tree = Tree(obj)
    affected_nodes = tree.get_directly_affected(tree.built_from)
    for node in affected_nodes:
        node.value.add_to_concerns(issue)


def remove_issue(obj: ADCMEntity, issue_type: IssueType) -> None:
    """Remove outdated issue from other's concerns"""
    issue = obj.get_own_issue(issue_type)
    if not issue:
        return

    for entity in issue.related_objects:
        entity.remove_from_concerns(issue)

    issue.delete()


def recheck_issues(obj: ADCMEntity) -> None:
    """Re-check for object's type-specific issues"""
    issue_types = _prototype_issue_map.get(obj.prototype.type, [])
    for issue_type in issue_types:
        if not _issue_check_map[issue_type](obj):
            create_issue(obj, issue_type)
        else:
            remove_issue(obj, issue_type)


def update_hierarchy_issues(obj: ADCMEntity):
    """Update issues on all directly connected objects"""
    tree = Tree(obj)
    affected_nodes = tree.get_directly_affected(tree.built_from)
    for node in affected_nodes:
        obj = node.value
        recheck_issues(obj)
