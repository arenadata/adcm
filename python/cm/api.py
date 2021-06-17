# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.  You may obtain a
# copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

from django.db import transaction
from django.core.exceptions import MultipleObjectsReturned
from django.utils import timezone

import cm.errors
import cm.issue
import cm.config as config
import cm.status_api
import cm.lock
from cm.logger import log
from cm.upgrade import check_license, version_in
from cm.adcm_config import (
    proto_ref,
    obj_ref,
    prepare_social_auth,
    process_file_type,
    read_bundle_file,
    get_prototype_config,
    init_object_config,
    save_obj_config,
    check_json_config,
)
from cm.errors import AdcmEx
from cm.errors import raise_AdcmEx as err
from cm.status_api import Event
from cm.models import (
    Cluster,
    Prototype,
    Host,
    HostComponent,
    ADCM,
    ClusterObject,
    ServiceComponent,
    ConfigLog,
    HostProvider,
    PrototypeImport,
    PrototypeExport,
    ClusterBind,
    DummyData,
    Role,
)


def check_proto_type(proto, check_type):
    if proto.type != check_type:
        msg = 'Prototype type should be {}, not {}'
        err('OBJ_TYPE_ERROR', msg.format(check_type, proto.type))


def add_cluster(proto, name, desc=''):
    check_proto_type(proto, 'cluster')
    check_license(proto.bundle)
    spec, _, conf, attr = get_prototype_config(proto)
    with transaction.atomic():
        obj_conf = init_object_config(spec, conf, attr)
        cluster = Cluster(prototype=proto, name=name, config=obj_conf, description=desc)
        cluster.save()
        process_file_type(cluster, spec, conf)
        cm.issue.update_hierarchy_issues(cluster)
    cm.status_api.post_event('create', 'cluster', cluster.id)
    cm.status_api.load_service_map()
    return cluster


def add_host(proto, provider, fqdn, desc='', lock=False):
    check_proto_type(proto, 'host')
    check_license(proto.bundle)
    if proto.bundle != provider.prototype.bundle:
        msg = 'Host prototype bundle #{} does not match with host provider bundle #{}'
        err('FOREIGN_HOST', msg.format(proto.bundle.id, provider.prototype.bundle.id))
    spec, _, conf, attr = get_prototype_config(proto)
    event = Event()
    with transaction.atomic():
        obj_conf = init_object_config(spec, conf, attr)
        host = Host(
            prototype=proto, provider=provider, fqdn=fqdn, config=obj_conf, description=desc
        )
        host.save()
        if lock:
            host.stack = ['created']
            host.set_state(config.Job.LOCKED, event)
        process_file_type(host, spec, conf)
        cm.issue.update_hierarchy_issues(host)
    event.send_state()
    cm.status_api.post_event('create', 'host', host.id, 'provider', str(provider.id))
    cm.status_api.load_service_map()
    return host


def add_provider_host(provider_id, fqdn, desc=''):
    """
    add provider host

    This is intended for use in adcm_add_host ansible plugin only
    """
    provider = HostProvider.obj.get(id=provider_id)
    proto = Prototype.objects.get(bundle=provider.prototype.bundle, type='host')
    return add_host(proto, provider, fqdn, desc, lock=True)


def add_host_provider(proto, name, desc=''):
    check_proto_type(proto, 'provider')
    check_license(proto.bundle)
    spec, _, conf, attr = get_prototype_config(proto)
    with transaction.atomic():
        obj_conf = init_object_config(spec, conf, attr)
        provider = HostProvider(prototype=proto, name=name, config=obj_conf, description=desc)
        provider.save()
        process_file_type(provider, spec, conf)
        cm.issue.update_hierarchy_issues(provider)
    cm.status_api.post_event('create', 'provider', provider.id)
    return provider


def delete_host_provider(provider):
    hosts = Host.objects.filter(provider=provider)
    if hosts:
        msg = 'There is host #{} "{}" of host {}'
        err('PROVIDER_CONFLICT', msg.format(hosts[0].id, hosts[0].fqdn, obj_ref(provider)))
    provider_id = provider.id
    provider.delete()
    cm.status_api.post_event('delete', 'provider', provider_id)


def add_host_to_cluster(cluster, host):
    if host.cluster:
        if host.cluster.id != cluster.id:
            msg = 'Host #{} belong to cluster #{}'.format(host.id, host.cluster.id)
            err('FOREIGN_HOST', msg)
        else:
            err('HOST_CONFLICT')
    with transaction.atomic():
        host.cluster = cluster
        host.save()
        cm.issue.update_hierarchy_issues(host)
    cm.status_api.post_event('add', 'host', host.id, 'cluster', str(cluster.id))
    cm.status_api.load_service_map()
    log.info('host #%s %s is added to cluster #%s %s', host.id, host.fqdn, cluster.id, cluster.name)
    return host


def get_cluster_and_host(cluster_id, fqdn, host_id):
    cluster = Cluster.obj.get(id=cluster_id)
    if fqdn:
        host = Host.obj.get(fqdn=fqdn)
    elif host_id:
        if not isinstance(host_id, int):
            err('HOST_NOT_FOUND', f'host_id must be integer (got "{host_id}")')
        host = Host.obj.get(id=host_id)
    else:
        err('HOST_NOT_FOUND', 'fqdn or host_id is mandatory args')
    return (cluster, host)


def add_host_to_cluster_by_id(cluster_id, fqdn, host_id):
    """
    add host to cluster

    This is intended for use in adcm_add_host_to_cluster ansible plugin only
    """
    cluster, host = get_cluster_and_host(cluster_id, fqdn, host_id)
    return add_host_to_cluster(cluster, host)


def remove_host_from_cluster_by_id(cluster_id, fqdn, host_id):
    """
    remove host from cluster

    This is intended for use in adcm_remove_host_from_cluster ansible plugin only
    """
    cluster, host = get_cluster_and_host(cluster_id, fqdn, host_id)
    if host.cluster != cluster:
        err('HOST_CONFLICT', 'you can remove host only from you own cluster')
    remove_host_from_cluster(host)


def delete_host(host):
    cluster = host.cluster
    if cluster:
        msg = 'Host #{} "{}" belong to {}'
        err('HOST_CONFLICT', msg.format(host.id, host.fqdn, obj_ref(cluster)))
    host_id = host.id
    host.delete()
    cm.status_api.post_event('delete', 'host', host_id)
    cm.status_api.load_service_map()


def delete_host_by_id(host_id):
    """
    Host deleting

    This is intended for use in adcm_delete_host ansible plugin only
    """
    host = Host.obj.get(id=host_id)
    delete_host(host)


def _clean_up_related_hc(service: ClusterObject) -> None:
    """Unconditional removal of HostComponents related to removing ClusterObject"""
    qs = (
        HostComponent.objects.filter(cluster=service.cluster)
        .exclude(service=service)
        .select_related('host', 'component')
    )
    new_hc_list = []
    for hc in qs.all():
        new_hc_list.append((hc.service, hc.host, hc.component))
    save_hc(service.cluster, new_hc_list)


def _clean_up_related_bind(service: ClusterObject) -> None:
    """Unconditional removal of ClusterBind related to removing ClusterObject"""
    ClusterBind.objects.filter(source_service=service).delete()


def delete_service_by_id(service_id):
    """
    Unconditional removal of service from cluster

    This is intended for use in adcm_delete_service ansible plugin only
    """
    with transaction.atomic():
        DummyData.objects.filter(id=1).update(date=timezone.now())
        service = ClusterObject.obj.get(id=service_id)
        _clean_up_related_hc(service)
        _clean_up_related_bind(service)
        delete_service(service)


def delete_service_by_name(service_name, cluster_id):
    """
    Unconditional removal of service from cluster

    This is intended for use in adcm_delete_service ansible plugin only
    """
    with transaction.atomic():
        DummyData.objects.filter(id=1).update(date=timezone.now())
        service = ClusterObject.obj.get(cluster__id=cluster_id, prototype__name=service_name)
        _clean_up_related_hc(service)
        _clean_up_related_bind(service)
        delete_service(service)


def delete_service(service):
    if HostComponent.objects.filter(cluster=service.cluster, service=service).exists():
        err('SERVICE_CONFLICT', 'Service #{} has component(s) on host(s)'.format(service.id))
    if ClusterBind.objects.filter(source_service=service).exists():
        err('SERVICE_CONFLICT', 'Service #{} has exports(s)'.format(service.id))
    service_id = service.id
    service.delete()
    cm.status_api.post_event('delete', 'service', service_id)
    cm.status_api.load_service_map()


def delete_cluster(cluster):
    cluster_id = cluster.id
    cluster.delete()
    cm.status_api.post_event('delete', 'cluster', cluster_id)
    cm.status_api.load_service_map()


def remove_host_from_cluster(host):
    cluster = host.cluster
    hc = HostComponent.objects.filter(cluster=cluster, host=host)
    if hc:
        return err('HOST_CONFLICT', 'Host #{} has component(s)'.format(host.id))
    with transaction.atomic():
        host.cluster = None
        host.save()
        cm.issue.update_hierarchy_issues(cluster)
    cm.status_api.post_event('remove', 'host', host.id, 'cluster', str(cluster.id))
    cm.status_api.load_service_map()
    return host


def unbind(cbind):
    import_obj = get_bind_obj(cbind.cluster, cbind.service)
    export_obj = get_bind_obj(cbind.source_cluster, cbind.source_service)
    check_import_default(import_obj, export_obj)
    cbind_id = cbind.id
    cbind_cluster_id = cbind.cluster.id
    with transaction.atomic():
        DummyData.objects.filter(id=1).update(date=timezone.now())
        cbind.delete()
        cm.issue.update_hierarchy_issues(cbind.cluster)
    cm.status_api.post_event('delete', 'bind', cbind_id, 'cluster', str(cbind_cluster_id))


def add_service_to_cluster(cluster, proto):
    check_proto_type(proto, 'service')
    check_license(proto.bundle)
    if not proto.shared:
        if cluster.prototype.bundle != proto.bundle:
            msg = '{} does not belong to bundle "{}" {}'
            err(
                'SERVICE_CONFLICT',
                msg.format(
                    proto_ref(proto), cluster.prototype.bundle.name, cluster.prototype.version
                ),
            )
    spec, _, conf, attr = get_prototype_config(proto)
    with transaction.atomic():
        obj_conf = init_object_config(spec, conf, attr)
        cs = ClusterObject(cluster=cluster, prototype=proto, config=obj_conf)
        cs.save()
        add_components_to_service(cluster, cs)
        process_file_type(cs, spec, conf)
        cm.issue.update_hierarchy_issues(cs)
    cm.status_api.post_event('add', 'service', cs.id, 'cluster', str(cluster.id))
    cm.status_api.load_service_map()
    return cs


def add_components_to_service(cluster, service):
    for comp in Prototype.objects.filter(type='component', parent=service.prototype):
        spec, _, conf, attr = get_prototype_config(comp)
        obj_conf = init_object_config(spec, conf, attr)
        sc = ServiceComponent(cluster=cluster, service=service, prototype=comp, config=obj_conf)
        sc.save()
        cm.issue.update_hierarchy_issues(sc)


def add_user_role(user, role):
    if Role.objects.filter(id=role.id, user=user):
        err('ROLE_ERROR', f'User "{user.username}" already has role "{role.name}"')
    with transaction.atomic():
        role.user.add(user)
        role.save()
        for perm in role.permissions.all():
            user.user_permissions.add(perm)
    log.info('Add role "%s" to user "%s"', role.name, user.username)
    role.role_id = role.id
    return role


def add_group_role(group, role):
    if Role.objects.filter(id=role.id, group=group):
        err('ROLE_ERROR', f'Group "{group.name}" already has role "{role.name}"')
    with transaction.atomic():
        role.group.add(group)
        role.save()
        for perm in role.permissions.all():
            group.permissions.add(perm)
    log.info('Add role "%s" to group "%s"', role.name, group.name)
    role.role_id = role.id
    return role


def cook_perm_list(role, role_list):
    perm_list = {}
    for r in role_list:
        if r == role:
            continue
        for perm in r.permissions.all():
            perm_list[perm.codename] = True
    return perm_list


def remove_user_role(user, role):
    user_roles = Role.objects.filter(user=user)
    if role not in user_roles:
        err('ROLE_ERROR', f'User "{user.username}" does not has role "{role.name}"')
    perm_list = cook_perm_list(role, user_roles)
    with transaction.atomic():
        role.user.remove(user)
        role.save()
        for perm in role.permissions.all():
            if perm.codename not in perm_list:
                user.user_permissions.remove(perm)
    log.info('Remove role "%s" from user "%s"', role.name, user.username)


def remove_group_role(group, role):
    group_roles = Role.objects.filter(group=group)
    if role not in group_roles:
        err('ROLE_ERROR', f'Group "{group.name}" does not has role "{role.name}"')
    perm_list = cook_perm_list(role, group_roles)
    with transaction.atomic():
        role.group.remove(group)
        role.save()
        for perm in role.permissions.all():
            if perm.codename not in perm_list:
                group.permissions.remove(perm)
    log.info('Remove role "%s" from group "%s"', role.name, group.name)


def get_bundle_proto(bundle):
    proto = Prototype.objects.filter(bundle=bundle, name=bundle.name)
    return proto[0]


def get_license(bundle):
    if not bundle.license_path:
        return None
    ref = 'bundle "{}" {}'.format(bundle.name, bundle.version)
    proto = get_bundle_proto(bundle)
    return read_bundle_file(proto, bundle.license_path, bundle.hash, 'license file', ref)


def accept_license(bundle):
    if not bundle.license_path:
        err('LICENSE_ERROR', 'This bundle has no license')
    if bundle.license == 'absent':
        err('LICENSE_ERROR', 'This bundle has no license')
    bundle.license = 'accepted'
    bundle.save()


def update_obj_config(obj_conf, conf, attr, desc=''):
    if not isinstance(attr, dict):
        err('INVALID_CONFIG_UPDATE', 'attr should be a map')
    if hasattr(obj_conf, 'adcm'):
        obj = obj_conf.adcm
        proto = obj_conf.adcm.prototype
    elif hasattr(obj_conf, 'clusterobject'):
        obj = obj_conf.clusterobject
        proto = obj_conf.clusterobject.prototype
    elif hasattr(obj_conf, 'servicecomponent'):
        obj = obj_conf.servicecomponent
        proto = obj_conf.servicecomponent.prototype
    elif hasattr(obj_conf, 'cluster'):
        obj = obj_conf.cluster
        proto = obj_conf.cluster.prototype
    elif hasattr(obj_conf, 'host'):
        obj = obj_conf.host
        proto = obj_conf.host.prototype
    elif hasattr(obj_conf, 'hostprovider'):
        obj = obj_conf.hostprovider
        proto = obj_conf.hostprovider.prototype
    else:
        err('INVALID_CONFIG_UPDATE', 'unknown object type "{}"'.format(obj_conf))
    old_conf = ConfigLog.objects.get(obj_ref=obj_conf, id=obj_conf.current)
    if not attr:
        if old_conf.attr:
            attr = old_conf.attr
    new_conf = check_json_config(proto, obj, conf, old_conf.config, attr)
    with transaction.atomic():
        cl = save_obj_config(obj_conf, new_conf, attr, desc)
        cm.issue.update_hierarchy_issues(obj)
    if hasattr(obj_conf, 'adcm'):
        prepare_social_auth(new_conf)
    cm.status_api.post_event('change_config', proto.type, obj.id, 'version', str(cl.id))
    return cl


def has_google_oauth():
    adcm = ADCM.objects.filter()
    if not adcm:
        return False
    cl = ConfigLog.objects.get(obj_ref=adcm[0].config, id=adcm[0].config.current)
    if 'google_oauth' not in cl.config:
        return False
    gconf = cl.config['google_oauth']
    if 'client_id' not in gconf or not gconf['client_id']:
        return False
    return True


def get_hc(cluster):
    if not cluster:
        return None
    hc_map = []
    for hc in HostComponent.objects.filter(cluster=cluster):
        hc_map.append(
            {
                'host_id': hc.host.id,
                'service_id': hc.service.id,
                'component_id': hc.component.id,
            }
        )
    return hc_map


def check_hc(cluster, hc_in):  # pylint: disable=too-many-branches
    def check_sub(sub_key, sub_type, item):
        if sub_key not in item:
            msg = '"{}" sub-field of hostcomponent is required'
            raise AdcmEx('INVALID_INPUT', msg.format(sub_key))
        if not isinstance(item[sub_key], sub_type):
            msg = '"{}" sub-field of hostcomponent should be "{}"'
            raise AdcmEx('INVALID_INPUT', msg.format(sub_key, sub_type))

    seen = {}
    if not isinstance(hc_in, list):
        raise AdcmEx('INVALID_INPUT', 'hostcomponent should be array')
    for item in hc_in:
        for sub_key, sub_type in (('service_id', int), ('host_id', int), ('component_id', int)):
            check_sub(sub_key, sub_type, item)
        key = (item.get('service_id', ''), item.get('host_id', ''), item.get('component_id', ''))
        if key not in seen:
            seen[key] = 1
        else:
            msg = 'duplicate ({}) in host service list'
            raise AdcmEx('INVALID_INPUT', msg.format(item))

    host_comp_list = []
    for item in hc_in:
        host = Host.obj.get(id=item['host_id'])
        service = ClusterObject.obj.get(id=item['service_id'], cluster=cluster)
        comp = ServiceComponent.obj.get(id=item['component_id'], cluster=cluster, service=service)
        if not host.cluster:
            msg = 'host #{} {} does not belong to any cluster'.format(host.id, host.fqdn)
            raise AdcmEx("FOREIGN_HOST", msg)
        if host.cluster.id != cluster.id:
            msg = 'host {} (cluster #{}) does not belong to cluster #{}'
            raise AdcmEx("FOREIGN_HOST", msg.format(host.fqdn, host.cluster.id, cluster.id))
        host_comp_list.append((service, host, comp))

    for service in ClusterObject.objects.filter(cluster=cluster):
        cm.issue.check_component_constraint(service, [i for i in host_comp_list if i[0] == service])

    cm.issue.check_component_requires(host_comp_list)
    cm.issue.check_bound_components(host_comp_list)
    return host_comp_list


def save_hc(cluster, host_comp_list):
    event = Event()
    hc_queryset = HostComponent.objects.filter(cluster=cluster)

    # TODO: double purpose code need to be refactored
    # HC mapping could be edited with OR without hierarchy locking
    old_hosts = {i.host for i in hc_queryset.select_related('host').all()}
    new_hosts = {i[1] for i in host_comp_list}
    for removed_host in old_hosts.difference(new_hosts):
        if removed_host.state == config.Job.LOCKED:
            cm.lock._unlock_obj(removed_host, event)  # pylint: disable=protected-access
    for added_host in new_hosts.difference(old_hosts):
        if added_host.cluster.state == config.Job.LOCKED:
            cm.lock._lock_obj(added_host, event)  # pylint: disable=protected-access

    hc_queryset.delete()
    result = []
    for (proto, host, comp) in host_comp_list:
        hc = HostComponent(
            cluster=cluster,
            service=proto,
            host=host,
            component=comp,
        )
        hc.save()
        result.append(hc)
    event.send_state()
    cm.status_api.post_event('change_hostcomponentmap', 'cluster', cluster.id)
    cm.issue.update_hierarchy_issues(cluster)
    cm.status_api.load_service_map()
    return result


def add_hc(cluster, hc_in):
    host_comp_list = check_hc(cluster, hc_in)
    with transaction.atomic():
        DummyData.objects.filter(id=1).update(date=timezone.now())
        new_hc = save_hc(cluster, host_comp_list)
    return new_hc


def get_bind(cluster, service, source_cluster, source_service):
    try:
        return ClusterBind.objects.get(
            cluster=cluster,
            service=service,
            source_cluster=source_cluster,
            source_service=source_service,
        )
    except ClusterBind.DoesNotExist:
        return None


def get_import(cluster, service=None):
    def get_export(cluster, service, pi):
        exports = []
        export_proto = {}
        for pe in PrototypeExport.objects.filter(prototype__name=pi.name):
            # Merge all export groups of prototype to one export
            if pe.prototype.id in export_proto:
                continue
            export_proto[pe.prototype.id] = True
            if not version_in(pe.prototype.version, pi):
                continue
            if pe.prototype.type == 'cluster':
                for cls in Cluster.objects.filter(prototype=pe.prototype):
                    binded = get_bind(cluster, service, cls, None)
                    exports.append(
                        {
                            'obj_name': cls.name,
                            'bundle_name': cls.prototype.display_name,
                            'bundle_version': cls.prototype.version,
                            'id': {'cluster_id': cls.id},
                            'binded': bool(binded),
                            'bind_id': getattr(binded, 'id', None),
                        }
                    )
            elif pe.prototype.type == 'service':
                for co in ClusterObject.objects.filter(prototype=pe.prototype):
                    binded = get_bind(cluster, service, co.cluster, co)
                    exports.append(
                        {
                            'obj_name': co.cluster.name + '/' + co.prototype.display_name,
                            'bundle_name': co.prototype.display_name,
                            'bundle_version': co.prototype.version,
                            'id': {'cluster_id': co.cluster.id, 'service_id': co.id},
                            'binded': bool(binded),
                            'bind_id': getattr(binded, 'id', None),
                        }
                    )
            else:
                err('BIND_ERROR', 'unexpected export type: {}'.format(pe.prototype.type))
        return exports

    imports = []
    proto = cluster.prototype
    if service:
        proto = service.prototype
    for pi in PrototypeImport.objects.filter(prototype=proto):
        imports.append(
            {
                'id': pi.id,
                'name': pi.name,
                'required': pi.required,
                'multibind': pi.multibind,
                'exports': get_export(cluster, service, pi),
            }
        )
    return imports


def check_bind_post(bind_list):
    if not isinstance(bind_list, list):
        err('BIND_ERROR', 'bind should be an array')
    for b in bind_list:
        if not isinstance(b, dict):
            err('BIND_ERROR', 'bind item should be a map')
        if 'import_id' not in b:
            err('BIND_ERROR', 'bind item does not have required "import_id" key')
        if not isinstance(b['import_id'], int):
            err('BIND_ERROR', 'bind item "import_id" value should be integer')
        if 'export_id' not in b:
            err('BIND_ERROR', 'bind item does not have required "export_id" key')
        if not isinstance(b['export_id'], dict):
            err('BIND_ERROR', 'bind item "export_id" value should be a map')
        if 'cluster_id' not in b['export_id']:
            err('BIND_ERROR', 'bind item export_id does not have required "cluster_id" key')
        if not isinstance(b['export_id']['cluster_id'], int):
            err('BIND_ERROR', 'bind item export_id "cluster_id" value should be integer')


def check_import_default(import_obj, export_obj):
    pi = PrototypeImport.objects.get(prototype=import_obj.prototype, name=export_obj.prototype.name)
    if not pi.default:
        return
    cl = ConfigLog.objects.get(obj_ref=import_obj.config, id=import_obj.config.current)
    if not cl.attr:
        return
    for name in json.loads(pi.default):
        if name in cl.attr:
            if 'active' in cl.attr[name] and not cl.attr[name]['active']:
                msg = 'Default import "{}" for {} is inactive'
                err('BIND_ERROR', msg.format(name, obj_ref(import_obj)))


def get_bind_obj(cluster, service):
    obj = cluster
    if service:
        obj = service
    return obj


def multi_bind(cluster, service, bind_list):  # pylint: disable=too-many-locals,too-many-statements
    def get_pi(import_id, import_obj):
        pi = PrototypeImport.obj.get(id=import_id)
        if pi.prototype != import_obj.prototype:
            msg = 'Import #{} does not belong to {}'
            err('BIND_ERROR', msg.format(import_id, obj_ref(import_obj)))
        return pi

    def get_export_service(b, export_cluster):
        export_co = None
        if 'service_id' in b['export_id']:
            export_co = ClusterObject.obj.get(id=b['export_id']['service_id'])
            if export_co.cluster != export_cluster:
                msg = 'export {} is not belong to {}'
                err('BIND_ERROR', msg.format(obj_ref(export_co), obj_ref(export_cluster)))
        return export_co

    def cook_key(cluster, service):
        if service:
            return f'{cluster.id}.{service.id}'
        return str(cluster.id)

    check_bind_post(bind_list)
    import_obj = get_bind_obj(cluster, service)
    old_bind = {}
    cb_list = ClusterBind.objects.filter(cluster=cluster, service=service)
    for cb in cb_list:
        old_bind[cook_key(cb.source_cluster, cb.source_service)] = cb

    new_bind = {}
    for b in bind_list:
        pi = get_pi(b['import_id'], import_obj)
        export_cluster = Cluster.obj.get(id=b['export_id']['cluster_id'])
        export_obj = export_cluster
        export_co = get_export_service(b, export_cluster)
        if export_co:
            export_obj = export_co

        if cook_key(export_cluster, export_co) in new_bind:
            err('BIND_ERROR', 'Bind list has duplicates')

        if pi.name != export_obj.prototype.name:
            msg = 'Export {} does not match import name "{}"'
            err('BIND_ERROR', msg.format(obj_ref(export_obj), pi.name))
        if not version_in(export_obj.prototype.version, pi):
            msg = 'Import "{}" of {} versions ({}, {}) does not match export version: {} ({})'
            err(
                'BIND_ERROR',
                msg.format(
                    export_obj.prototype.name,
                    proto_ref(pi.prototype),
                    pi.min_version,
                    pi.max_version,
                    export_obj.prototype.version,
                    obj_ref(export_obj),
                ),
            )
        cbind = ClusterBind(
            cluster=cluster,
            service=service,
            source_cluster=export_cluster,
            source_service=export_co,
        )
        new_bind[cook_key(export_cluster, export_co)] = (pi, cbind, export_obj)

    with transaction.atomic():
        for key in new_bind:
            if key in old_bind:
                continue
            (pi, cb, export_obj) = new_bind[key]
            check_multi_bind(pi, cluster, service, cb.source_cluster, cb.source_service, cb_list)
            cb.save()
            log.info('bind %s to %s', obj_ref(export_obj), obj_ref(import_obj))

        for key in old_bind:
            if key in new_bind:
                continue
            export_obj = get_bind_obj(old_bind[key].source_cluster, old_bind[key].source_service)
            check_import_default(import_obj, export_obj)
            old_bind[key].delete()
            log.info('unbind %s from %s', obj_ref(export_obj), obj_ref(import_obj))

        cm.issue.update_hierarchy_issues(cluster)

    return get_import(cluster, service)


def bind(cluster, service, export_cluster, export_service_id):  # pylint: disable=too-many-branches
    '''
    Adapter between old and new bind interface
    /api/.../bind/ -> /api/.../import/
    bind() -> multi_bind()
    '''
    export_service = None
    if export_service_id:
        export_service = ClusterObject.obj.get(cluster=export_cluster, id=export_service_id)
        if not PrototypeExport.objects.filter(prototype=export_service.prototype):
            err('BIND_ERROR', '{} do not have exports'.format(obj_ref(export_service)))
        name = export_service.prototype.name
    else:
        if not PrototypeExport.objects.filter(prototype=export_cluster.prototype):
            err('BIND_ERROR', '{} does not have exports'.format(obj_ref(export_cluster)))
        name = export_cluster.prototype.name

    import_obj = cluster
    if service:
        import_obj = service

    try:
        pi = PrototypeImport.obj.get(prototype=import_obj.prototype, name=name)
    except MultipleObjectsReturned:
        err('BIND_ERROR', 'Old api does not support multi bind. Go to /api/v1/.../import/')

    bind_list = []
    for imp in get_import(cluster, service):
        for exp in imp['exports']:
            if exp['binded']:
                bind_list.append({'import_id': imp['id'], 'export_id': exp['id']})

    item = {'import_id': pi.id, 'export_id': {'cluster_id': export_cluster.id}}
    if export_service:
        item['export_id']['service_id'] = export_service.id
    bind_list.append(item)

    multi_bind(cluster, service, bind_list)
    res = {
        'export_cluster_id': export_cluster.id,
        'export_cluster_name': export_cluster.name,
        'export_cluster_prototype_name': export_cluster.prototype.name,
    }
    if export_service:
        res['export_service_id'] = export_service.id
    return res


def check_multi_bind(actual_import, cluster, service, export_cluster, export_service, cb_list=None):
    if actual_import.multibind:
        return
    if cb_list is None:
        cb_list = ClusterBind.objects.filter(cluster=cluster, service=service)
    for cb in cb_list:
        if cb.source_service:
            source_proto = cb.source_service.prototype
        else:
            source_proto = cb.source_cluster.prototype
        if export_service:
            if source_proto == export_service.prototype:
                msg = 'can not multi bind {} to {}'
                err('BIND_ERROR', msg.format(proto_ref(source_proto), obj_ref(cluster)))
        else:
            if source_proto == export_cluster.prototype:
                msg = 'can not multi bind {} to {}'
                err('BIND_ERROR', msg.format(proto_ref(source_proto), obj_ref(cluster)))


def push_obj(obj, state):
    stack = obj.stack
    if not stack:
        stack = [state]
    else:
        stack[0] = state
    obj.stack = stack
    obj.save()
    return obj
