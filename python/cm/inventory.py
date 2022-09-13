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
import os
from itertools import chain

from django.contrib.contenttypes.models import ContentType

from cm import config
from cm.adcm_config import get_prototype_config, process_config
from cm.logger import logger
from cm.models import (
    Cluster,
    ClusterBind,
    ClusterObject,
    ConfigLog,
    GroupConfig,
    Host,
    HostComponent,
    HostProvider,
    MaintenanceModeType,
    Prototype,
    PrototypeExport,
    PrototypeImport,
    ServiceComponent,
    get_object_cluster,
)


def process_config_and_attr(obj, conf, attr=None, spec=None):
    if not spec:
        if isinstance(obj, GroupConfig):
            prototype = obj.object.prototype
        else:
            prototype = obj.prototype
        spec, _, _, _ = get_prototype_config(prototype)
    new_conf = process_config(obj, spec, conf)
    if attr:
        for key, val in attr.items():
            if 'active' in val and not val['active']:
                new_conf[key] = None
    return new_conf


def get_import(cluster):  # pylint: disable=too-many-branches
    def get_actual_import(bind, obj):
        if bind.service:
            proto = bind.service.prototype
        else:
            proto = bind.cluster.prototype
        return PrototypeImport.objects.get(prototype=proto, name=obj.prototype.name)

    imports = {}
    for obj in chain([cluster], ClusterObject.objects.filter(cluster=cluster)):
        for imp in PrototypeImport.objects.filter(prototype=obj.prototype):
            if imp.default:
                if imp.multibind:
                    imports[imp.name] = []
                else:
                    imports[imp.name] = {}
                for group in imp.default:
                    cl = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
                    conf = process_config_and_attr(obj, cl.config, cl.attr)
                    if imp.multibind:
                        imports[imp.name].append({group: conf[group]})
                    else:
                        imports[imp.name][group] = conf[group]

    first = True
    for bind in ClusterBind.objects.filter(cluster=cluster):
        if bind.source_service:
            obj = bind.source_service
        else:
            obj = bind.source_cluster
        conf_ref = obj.config
        export_proto = obj.prototype
        cl = ConfigLog.objects.get(obj_ref=conf_ref, id=conf_ref.current)
        conf = process_config_and_attr(obj, cl.config, cl.attr)
        actual_import = get_actual_import(bind, obj)
        if actual_import.multibind:
            if export_proto.name not in imports:
                imports[export_proto.name] = []
            elif actual_import.default and first:
                imports[export_proto.name] = []
                first = False
        else:
            imports[export_proto.name] = {}
        for export in PrototypeExport.objects.filter(prototype=export_proto):
            if actual_import.multibind:
                imports[export_proto.name].append({export.name: conf[export.name]})
            else:
                imports[export_proto.name][export.name] = conf[export.name]
    return imports


def get_obj_config(obj):
    if obj.config is None:
        return {}
    cl = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
    return process_config_and_attr(obj, cl.config, cl.attr)


def get_cluster_variables(cluster: Cluster, cluster_config: dict = None):
    return {
        'config': cluster_config or get_obj_config(cluster),
        'name': cluster.name,
        'id': cluster.id,
        'version': cluster.prototype.version,
        'edition': cluster.prototype.bundle.edition,
        'state': cluster.state,
        'multi_state': cluster.multi_state,
        'before_upgrade': cluster.before_upgrade,
    }


def get_service_variables(service: ClusterObject, service_config: dict = None):
    return {
        'id': service.id,
        'version': service.prototype.version,
        'state': service.state,
        'multi_state': service.multi_state,
        'config': service_config or get_obj_config(service),
    }


def get_component_variables(component: ServiceComponent, component_config: dict = None):
    return {
        'component_id': component.id,
        'config': component_config or get_obj_config(component),
        'state': component.state,
        'multi_state': component.multi_state,
    }


def get_provider_variables(provider: HostProvider, provider_config: dict = None):
    host_proto = Prototype.objects.get(bundle=provider.prototype.bundle, type='host')
    return {
        'config': provider_config or get_obj_config(provider),
        'name': provider.name,
        'id': provider.id,
        'host_prototype_id': host_proto.id,
        'state': provider.state,
        'multi_state': provider.multi_state,
        'before_upgrade': provider.before_upgrade,
    }


def get_host_vars(host: Host, obj):
    # TODO: add test for this function
    groups = host.group_config.filter(
        object_id=obj.id, object_type=ContentType.objects.get_for_model(obj)
    )
    variables = {}
    for group in groups:
        # TODO: What to do with activatable group in attr ???
        conf, attr = group.get_config_and_attr()
        group_config = process_config_and_attr(group, conf, attr)
        if isinstance(group.object, Cluster):
            variables.update(
                {'cluster': get_cluster_variables(group.object, cluster_config=group_config)}
            )
        elif isinstance(group.object, ClusterObject):
            variables.update(
                {
                    'services': {
                        group.object.prototype.name: get_service_variables(
                            group.object, service_config=group_config
                        )
                    }
                }
            )
            for service in ClusterObject.objects.filter(cluster=group.object.cluster).exclude(
                pk=group.object.id
            ):
                variables['services'][service.prototype.name] = get_service_variables(service)
                for component in ServiceComponent.objects.filter(
                    cluster=group.object.cluster, service=service
                ):
                    variables['services'][service.prototype.name][
                        component.prototype.name
                    ] = get_component_variables(component)
            for component in ServiceComponent.objects.filter(
                cluster=group.object.cluster, service=group.object
            ):
                variables['services'][group.object.prototype.name][
                    component.prototype.name
                ] = get_component_variables(component)
        elif isinstance(group.object, ServiceComponent):
            variables.update(
                {
                    'services': {
                        group.object.service.prototype.name: get_service_variables(
                            group.object.service
                        )
                    }
                }
            )
            variables['services'][group.object.service.prototype.name][
                group.object.prototype.name
            ] = get_component_variables(group.object, component_config=group_config)

            for component in ServiceComponent.objects.filter(
                cluster=group.object.cluster, service=group.object.service
            ).exclude(pk=group.object.id):
                variables['services'][component.service.prototype.name][
                    component.prototype.name
                ] = get_component_variables(component)

        else:  # HostProvider
            variables.update(
                {'provider': get_provider_variables(group.object, provider_config=group_config)}
            )
    return variables


def get_cluster_config(cluster):
    res = {
        'cluster': get_cluster_variables(cluster),
        'services': {},
    }
    imports = get_import(cluster)
    if imports:
        res['cluster']['imports'] = imports
    for service in ClusterObject.objects.filter(cluster=cluster):
        res['services'][service.prototype.name] = get_service_variables(service)
        for component in ServiceComponent.objects.filter(cluster=cluster, service=service):
            res['services'][service.prototype.name][
                component.prototype.name
            ] = get_component_variables(component)
    return res


def get_provider_config(provider_id):
    provider = HostProvider.objects.get(id=provider_id)
    return {'provider': get_provider_variables(provider)}


def get_host_groups(cluster, delta, action_host=None):
    def in_mm(hc: HostComponent) -> bool:
        return hc.host.maintenance_mode == MaintenanceModeType.On.value

    groups = {}
    all_hosts = HostComponent.objects.filter(cluster=cluster)
    for hc in all_hosts:
        if in_mm(hc) or (action_host and hc.host.id not in action_host):
            continue

        key1 = f'{hc.service.prototype.name}.{hc.component.prototype.name}'
        if key1 not in groups:
            groups[key1] = {'hosts': {}}
        groups[key1]['hosts'][hc.host.fqdn] = get_obj_config(hc.host)
        groups[key1]['hosts'][hc.host.fqdn].update(get_host_vars(hc.host, hc.component))

        key2 = f'{hc.service.prototype.name}'
        if key2 not in groups:
            groups[key2] = {'hosts': {}}
        groups[key2]['hosts'][hc.host.fqdn] = get_obj_config(hc.host)
        groups[key2]['hosts'][hc.host.fqdn].update(get_host_vars(hc.host, hc.service))

    for htype in delta:
        for key in delta[htype]:
            lkey = f'{key}.{htype}'
            if lkey not in groups:
                groups[lkey] = {'hosts': {}}
            for fqdn in delta[htype][key]:
                host = delta[htype][key][fqdn]
                # TODO: What is `delta`? Need calculate delta for group_config?
                if not host.maintenance_mode == MaintenanceModeType.On.value:
                    groups[lkey]['hosts'][host.fqdn] = get_obj_config(host)

    return groups


def get_hosts(host_list, obj, action_host=None):
    group = {}
    for host in host_list:
        if host.maintenance_mode == MaintenanceModeType.On.value or (
            action_host and host.id not in action_host
        ):
            continue
        group[host.fqdn] = get_obj_config(host)
        group[host.fqdn]['adcm_hostid'] = host.id
        group[host.fqdn]['state'] = host.state
        group[host.fqdn]['multi_state'] = host.multi_state
        if not isinstance(obj, Host):
            group[host.fqdn].update(get_host_vars(host, obj))
    return group


def get_cluster_hosts(cluster, action_host=None):
    return {
        'CLUSTER': {
            'hosts': get_hosts(Host.objects.filter(cluster=cluster), cluster, action_host),
            'vars': get_cluster_config(cluster),
        }
    }


def get_provider_hosts(provider, action_host=None):
    return {
        'PROVIDER': {
            'hosts': get_hosts(Host.objects.filter(provider=provider), provider, action_host),
        }
    }


def get_host(host_id):
    host = Host.objects.get(id=host_id)
    groups = {
        'HOST': {'hosts': get_hosts([host], host), 'vars': get_provider_config(host.provider.id)}
    }
    return groups


def get_target_host(host_id):
    host = Host.objects.get(id=host_id)
    groups = {
        'target': {'hosts': get_hosts([host], host), 'vars': get_cluster_config(host.cluster)}
    }
    return groups


def prepare_job_inventory(obj, job_id, action, delta, action_host=None):
    logger.info('prepare inventory for job #%s, object: %s', job_id, obj)
    fd = open(os.path.join(config.RUN_DIR, f'{job_id}/inventory.json'), 'w', encoding='utf_8')
    inv = {'all': {'children': {}}}
    cluster = get_object_cluster(obj)
    if cluster:
        inv['all']['children'].update(get_cluster_hosts(cluster, action_host))
        inv['all']['children'].update(get_host_groups(cluster, delta, action_host))
    if obj.prototype.type == 'host':
        inv['all']['children'].update(get_host(obj.id))
        if action.host_action:
            inv['all']['children'].update(get_target_host(obj.id))
    if obj.prototype.type == 'provider':
        inv['all']['children'].update(get_provider_hosts(obj, action_host))
        inv['all']['vars'] = get_provider_config(obj.id)
    json.dump(inv, fd, indent=3)
    fd.close()
