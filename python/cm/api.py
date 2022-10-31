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

# pylint:disable=logging-fstring-interpolation,too-many-lines

import json

from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction
from django.utils import timezone
from version_utils import rpm

import cm.issue
import cm.status_api
from cm.adcm_config import (
    check_json_config,
    init_object_config,
    obj_ref,
    proto_ref,
    read_bundle_file,
    save_obj_config,
)
from cm.api_context import ctx
from cm.errors import AdcmEx
from cm.errors import raise_adcm_ex as err
from cm.logger import logger
from cm.models import (
    ADCMEntity,
    Bundle,
    Cluster,
    ClusterBind,
    ClusterObject,
    ConcernType,
    ConfigLog,
    DummyData,
    GroupConfig,
    Host,
    HostComponent,
    HostProvider,
    MaintenanceMode,
    Prototype,
    PrototypeExport,
    PrototypeImport,
    ServiceComponent,
    TaskLog,
)
from rbac.models import re_apply_object_policy


def check_license(bundle: Bundle) -> None:
    if bundle.license == "unaccepted":
        msg = 'License for bundle "{}" {} {} is not accepted'
        err("LICENSE_ERROR", msg.format(bundle.name, bundle.version, bundle.edition))


def version_in(version: str, ver: PrototypeImport) -> bool:
    if ver.min_strict:
        if rpm.compare_versions(version, ver.min_version) <= 0:
            return False
    elif ver.min_version:
        if rpm.compare_versions(version, ver.min_version) < 0:
            return False
    if ver.max_strict:
        if rpm.compare_versions(version, ver.max_version) >= 0:
            return False
    elif ver.max_version:
        if rpm.compare_versions(version, ver.max_version) > 0:
            return False

    return True


def check_proto_type(proto, check_type):
    if proto.type != check_type:
        msg = "Prototype type should be {}, not {}"
        err("OBJ_TYPE_ERROR", msg.format(check_type, proto.type))


def load_host_map():
    hosts = [
        {
            "id": host_data["id"],
            "maintenance_mode": not host_data["maintenance_mode"] == MaintenanceMode.OFF,
        }
        for host_data in Host.objects.values("id", "maintenance_mode")
    ]

    return cm.status_api.api_request("post", "/object/host/", hosts)


def load_service_map():
    comps = {}
    hosts = {}
    hc_map = {}
    services = {}
    passive = {}
    for c in ServiceComponent.objects.filter(prototype__monitoring="passive"):
        passive[c.id] = True

    for hc in HostComponent.objects.all():
        if hc.component.id in passive:
            continue

        key = f"{hc.host.id}.{hc.component.id}"
        hc_map[key] = {"cluster": hc.cluster.id, "service": hc.service.id}
        if str(hc.cluster.id) not in comps:
            comps[str(hc.cluster.id)] = {}

        if str(hc.service.id) not in comps[str(hc.cluster.id)]:
            comps[str(hc.cluster.id)][str(hc.service.id)] = []

        comps[str(hc.cluster.id)][str(hc.service.id)].append(key)

    for host in Host.objects.filter(prototype__monitoring="active"):
        if host.cluster:
            cluster_id = host.cluster.id
        else:
            cluster_id = 0

        if cluster_id not in hosts:
            hosts[cluster_id] = []

        hosts[cluster_id].append(host.id)

    for co in ClusterObject.objects.filter(prototype__monitoring="active"):
        if co.cluster.id not in services:
            services[co.cluster.id] = []

        services[co.cluster.id].append(co.id)

    m = {
        "hostservice": hc_map,
        "component": comps,
        "service": services,
        "host": hosts,
    }
    cm.status_api.api_request("post", "/servicemap/", m)
    load_host_map()


def add_cluster(proto, name, desc=""):
    check_proto_type(proto, "cluster")
    check_license(proto.bundle)
    with transaction.atomic():
        cluster = Cluster.objects.create(prototype=proto, name=name, description=desc)
        obj_conf = init_object_config(proto, cluster)
        cluster.config = obj_conf
        cluster.save()
        cm.issue.update_hierarchy_issues(cluster)

    cm.status_api.post_event("create", "cluster", cluster.id)
    load_service_map()
    logger.info(f"cluster #{cluster.id} {cluster.name} is added")
    return cluster


def add_host(proto, provider, fqdn, desc=""):
    check_proto_type(proto, "host")
    check_license(proto.bundle)
    if proto.bundle != provider.prototype.bundle:
        msg = "Host prototype bundle #{} does not match with host provider bundle #{}"
        err("FOREIGN_HOST", msg.format(proto.bundle.id, provider.prototype.bundle.id))

    with transaction.atomic():
        host = Host.objects.create(prototype=proto, provider=provider, fqdn=fqdn, description=desc)
        obj_conf = init_object_config(proto, host)
        host.config = obj_conf
        host.save()
        host.add_to_concerns(ctx.lock)
        cm.issue.update_hierarchy_issues(host.provider)
        re_apply_object_policy(provider)

    ctx.event.send_state()
    cm.status_api.post_event("create", "host", host.id, "provider", str(provider.id))
    load_service_map()
    logger.info(f"host #{host.id} {host.fqdn} is added")
    return host


def add_provider_host(provider_id, fqdn, desc=""):
    """
    add provider host

    This is intended for use in adcm_add_host ansible plugin only
    """
    provider = HostProvider.obj.get(id=provider_id)
    proto = Prototype.objects.get(bundle=provider.prototype.bundle, type="host")

    return add_host(proto, provider, fqdn, desc)


def add_host_provider(proto, name, desc=""):
    check_proto_type(proto, "provider")
    check_license(proto.bundle)
    with transaction.atomic():
        provider = HostProvider.objects.create(prototype=proto, name=name, description=desc)
        obj_conf = init_object_config(proto, provider)
        provider.config = obj_conf
        provider.save()
        provider.add_to_concerns(ctx.lock)
        cm.issue.update_hierarchy_issues(provider)

    ctx.event.send_state()
    cm.status_api.post_event("create", "provider", provider.id)
    logger.info(f"host provider #{provider.id} {provider.name} is added")
    return provider


def _cancel_locking_tasks(obj: ADCMEntity, obj_deletion=False):
    """Cancel all tasks that have locks on object"""
    for lock in obj.concerns.filter(type=ConcernType.Lock):
        for task in TaskLog.objects.filter(lock=lock):
            task.cancel(obj_deletion=obj_deletion)


def delete_host_provider(provider, cancel_tasks=True):
    hosts = Host.objects.filter(provider=provider)
    if hosts:
        msg = 'There is host #{} "{}" of host {}'
        err("PROVIDER_CONFLICT", msg.format(hosts[0].id, hosts[0].fqdn, obj_ref(provider)))
    if cancel_tasks:
        _cancel_locking_tasks(provider, obj_deletion=True)

    provider_id = provider.id
    provider.delete()
    cm.status_api.post_event("delete", "provider", provider_id)
    logger.info(f"host provider #{provider_id} is deleted")


def add_host_to_cluster(cluster, host):
    if host.cluster:
        if host.cluster.id != cluster.id:
            msg = f"Host #{host.id} belong to cluster #{host.cluster.id}"
            err("FOREIGN_HOST", msg)
        else:
            err("HOST_CONFLICT")

    with transaction.atomic():
        DummyData.objects.filter(id=1).update(date=timezone.now())

        host.cluster = cluster
        host.save()
        host.add_to_concerns(ctx.lock)
        cm.issue.update_hierarchy_issues(host)
        re_apply_object_policy(cluster)

    cm.status_api.post_event("add", "host", host.id, "cluster", str(cluster.id))
    load_service_map()
    logger.info(
        "host #%s %s is added to cluster #%s %s", host.id, host.fqdn, cluster.id, cluster.name
    )
    return host


def get_cluster_and_host(cluster_id, fqdn, host_id):
    cluster = Cluster.obj.get(id=cluster_id)
    host = None
    if fqdn:
        host = Host.obj.get(fqdn=fqdn)
    elif host_id:
        if not isinstance(host_id, int):
            err("HOST_NOT_FOUND", f'host_id must be integer (got "{host_id}")')
        host = Host.obj.get(id=host_id)
    else:
        err("HOST_NOT_FOUND", "fqdn or host_id is mandatory args")

    return cluster, host


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
        err("HOST_CONFLICT", "you can remove host only from you own cluster")

    remove_host_from_cluster(host)


def delete_host(host, cancel_tasks=True):
    cluster = host.cluster
    if cluster:
        msg = 'Host #{} "{}" belong to {}'
        err("HOST_CONFLICT", msg.format(host.id, host.fqdn, obj_ref(cluster)))

    if cancel_tasks:
        _cancel_locking_tasks(host, obj_deletion=True)

    host_id = host.id
    host.delete()
    cm.status_api.post_event("delete", "host", host_id)
    load_service_map()
    cm.issue.update_issue_after_deleting()
    logger.info(f"host #{host_id} is deleted")


def delete_host_by_id(host_id):
    """
    Host deleting

    This is intended for use in adcm_delete_host ansible plugin only
    """
    host = Host.obj.get(id=host_id)
    delete_host(host, cancel_tasks=False)


def _clean_up_related_hc(service: ClusterObject) -> None:
    """Unconditional removal of HostComponents related to removing ClusterObject"""
    qs = (
        HostComponent.objects.filter(cluster=service.cluster)
        .exclude(service=service)
        .select_related("host", "component")
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
        delete_service(service, cancel_tasks=False)


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
        delete_service(service, cancel_tasks=False)


def delete_service(service: ClusterObject, cancel_tasks=True) -> None:
    if HostComponent.objects.filter(cluster=service.cluster, service=service).exists():
        err("SERVICE_CONFLICT", f"Service #{service.id} has component(s) on host(s)")

    if ClusterBind.objects.filter(source_service=service).exists():
        err("SERVICE_CONFLICT", f"Service #{service.id} has exports(s)")

    if cancel_tasks:
        _cancel_locking_tasks(service, obj_deletion=True)

    service_id = service.id
    cluster = service.cluster
    service.delete()
    cm.issue.update_issue_after_deleting()
    cm.issue.update_hierarchy_issues(cluster)
    re_apply_object_policy(cluster)
    cm.status_api.post_event("delete", "service", service_id)
    load_service_map()
    logger.info(f"service #{service_id} is deleted")


def delete_cluster(cluster, cancel_tasks=True):
    if cancel_tasks:
        _cancel_locking_tasks(cluster, obj_deletion=True)

    cluster_id = cluster.id
    hosts = cluster.host_set.all()
    host_ids = [str(host.id) for host in hosts]
    hosts.update(maintenance_mode=MaintenanceMode.OFF)
    logger.debug(
        "Deleting cluster #%s. Set `%s` maintenance mode value for `%s` hosts.",
        cluster_id,
        MaintenanceMode.OFF,
        ", ".join(host_ids),
    )
    cluster.delete()
    cm.issue.update_issue_after_deleting()
    cm.status_api.post_event("delete", "cluster", cluster_id)
    load_service_map()


def remove_host_from_cluster(host):
    cluster = host.cluster
    hc = HostComponent.objects.filter(cluster=cluster, host=host)
    if hc:
        return err("HOST_CONFLICT", f"Host #{host.id} has component(s)")

    with transaction.atomic():
        host.maintenance_mode = MaintenanceMode.OFF
        host.cluster = None
        host.save()
        for group in cluster.group_config.all():
            group.hosts.remove(host)
            cm.issue.update_hierarchy_issues(host)

        host.remove_from_concerns(ctx.lock)
        cm.issue.update_hierarchy_issues(cluster)
        re_apply_object_policy(cluster)

    ctx.event.send_state()
    cm.status_api.post_event("remove", "host", host.id, "cluster", str(cluster.id))
    load_service_map()

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

    cm.status_api.post_event("delete", "bind", cbind_id, "cluster", str(cbind_cluster_id))


def add_service_to_cluster(cluster, proto):
    check_proto_type(proto, "service")
    check_license(proto.bundle)
    if not proto.shared:
        if cluster.prototype.bundle != proto.bundle:
            msg = '{} does not belong to bundle "{}" {}'
            err(
                "SERVICE_CONFLICT",
                msg.format(
                    proto_ref(proto), cluster.prototype.bundle.name, cluster.prototype.version
                ),
            )

    with transaction.atomic():
        cs = ClusterObject.objects.create(cluster=cluster, prototype=proto)
        obj_conf = init_object_config(proto, cs)
        cs.config = obj_conf
        cs.save()
        add_components_to_service(cluster, cs)
        cm.issue.update_hierarchy_issues(cs)
        re_apply_object_policy(cluster)

    cm.status_api.post_event("add", "service", cs.id, "cluster", str(cluster.id))
    load_service_map()
    logger.info(
        f"service #{cs.id} {cs.prototype.name} is added to cluster #{cluster.id} {cluster.name}"
    )

    return cs


def add_components_to_service(cluster, service):
    for comp in Prototype.objects.filter(type="component", parent=service.prototype):
        sc = ServiceComponent.objects.create(cluster=cluster, service=service, prototype=comp)
        obj_conf = init_object_config(comp, sc)
        sc.config = obj_conf
        sc.save()
        cm.issue.update_hierarchy_issues(sc)


def get_bundle_proto(bundle):
    proto = Prototype.objects.filter(bundle=bundle, name=bundle.name)

    return proto[0]


def get_license(bundle):
    if not bundle.license_path:
        return None

    ref = f'bundle "{bundle.name}" {bundle.version}'
    proto = get_bundle_proto(bundle)

    return read_bundle_file(proto, bundle.license_path, bundle.hash, "license file", ref)


def accept_license(bundle):
    if not bundle.license_path:
        err("LICENSE_ERROR", "This bundle has no license")

    if bundle.license == "absent":
        err("LICENSE_ERROR", "This bundle has no license")

    bundle.license = "accepted"
    bundle.save()


def update_obj_config(obj_conf, conf, attr, desc=""):
    if not isinstance(attr, dict):
        err("INVALID_CONFIG_UPDATE", "attr should be a map")

    obj = obj_conf.object
    if obj is None:
        err("INVALID_CONFIG_UPDATE", f'unknown object type "{obj_conf}"')

    group = None
    if isinstance(obj, GroupConfig):
        group = obj
        obj = group.object
        proto = obj.prototype
    else:
        proto = obj.prototype

    old_conf = ConfigLog.objects.get(obj_ref=obj_conf, id=obj_conf.current)
    new_conf = check_json_config(proto, group or obj, conf, old_conf.config, attr, old_conf.attr)
    with transaction.atomic():
        cl = save_obj_config(obj_conf, new_conf, attr, desc)
        cm.issue.update_hierarchy_issues(obj)
        re_apply_object_policy(obj)

    if group is not None:
        cm.status_api.post_event("change_config", "group-config", group.id, "version", str(cl.id))
    else:
        cm.status_api.post_event("change_config", proto.type, obj.id, "version", str(cl.id))

    return cl


def get_hc(cluster):
    if not cluster:
        return None

    hc_map = []
    for hc in HostComponent.objects.filter(cluster=cluster):
        hc_map.append(
            {
                "host_id": hc.host.id,
                "service_id": hc.service.id,
                "component_id": hc.component.id,
            }
        )

    return hc_map


def check_sub_key(hc_in):
    def check_sub(_sub_key, _sub_type, _item):
        if _sub_key not in _item:
            _msg = '"{}" sub-field of hostcomponent is required'
            raise AdcmEx("INVALID_INPUT", _msg.format(_sub_key))
        if not isinstance(_item[_sub_key], _sub_type):
            _msg = '"{}" sub-field of hostcomponent should be "{}"'
            raise AdcmEx("INVALID_INPUT", _msg.format(_sub_key, _sub_type))

    seen = {}
    if not isinstance(hc_in, list):
        raise AdcmEx("INVALID_INPUT", "hostcomponent should be array")

    for item in hc_in:
        for sub_key, sub_type in (("service_id", int), ("host_id", int), ("component_id", int)):
            check_sub(sub_key, sub_type, item)

        key = (item.get("service_id", ""), item.get("host_id", ""), item.get("component_id", ""))
        if key not in seen:
            seen[key] = 1
        else:
            msg = "duplicate ({}) in host service list"

            raise AdcmEx("INVALID_INPUT", msg.format(item))


def make_host_comp_list(cluster, hc_in):
    host_comp_list = []
    for item in hc_in:
        host = Host.obj.get(id=item["host_id"])
        service = ClusterObject.obj.get(id=item["service_id"], cluster=cluster)
        comp = ServiceComponent.obj.get(id=item["component_id"], cluster=cluster, service=service)
        if not host.cluster:
            msg = f"host #{host.id} {host.fqdn} does not belong to any cluster"

            raise AdcmEx("FOREIGN_HOST", msg)

        if host.cluster.id != cluster.id:
            msg = "host {} (cluster #{}) does not belong to cluster #{}"

            raise AdcmEx("FOREIGN_HOST", msg.format(host.fqdn, host.cluster.id, cluster.id))

        host_comp_list.append((service, host, comp))

    return host_comp_list


def check_hc(cluster, hc_in):
    check_sub_key(hc_in)
    host_comp_list = make_host_comp_list(cluster, hc_in)
    for service in ClusterObject.objects.filter(cluster=cluster):
        cm.issue.check_component_constraint(
            cluster, service.prototype, [i for i in host_comp_list if i[0] == service]
        )

    cm.issue.check_component_requires(host_comp_list)
    cm.issue.check_bound_components(host_comp_list)
    check_maintenance_mode(cluster, host_comp_list)

    return host_comp_list


def check_maintenance_mode(cluster, host_comp_list):
    for (service, host, comp) in host_comp_list:
        try:
            HostComponent.objects.get(cluster=cluster, service=service, host=host, component=comp)
        except HostComponent.DoesNotExist:
            if host.maintenance_mode == MaintenanceMode.ON:
                raise AdcmEx("INVALID_HC_HOST_IN_MM")  # pylint: disable=raise-missing-from


def still_existed_hc(cluster, host_comp_list):
    result = []
    for (service, host, comp) in host_comp_list:
        try:
            existed_hc = HostComponent.objects.get(
                cluster=cluster, service=service, host=host, component=comp
            )
            result.append(existed_hc)
        except HostComponent.DoesNotExist:
            continue

    return result


def save_hc(cluster, host_comp_list):  # pylint: disable=too-many-locals
    hc_queryset = HostComponent.objects.filter(cluster=cluster)
    service_map = {hc.service for hc in hc_queryset}
    old_hosts = {i.host for i in hc_queryset.select_related("host").all()}
    new_hosts = {i[1] for i in host_comp_list}
    for removed_host in old_hosts.difference(new_hosts):
        removed_host.remove_from_concerns(ctx.lock)

    for added_host in new_hosts.difference(old_hosts):
        added_host.add_to_concerns(ctx.lock)

    still_hc = still_existed_hc(cluster, host_comp_list)
    host_service_of_still_hc = {(hc.host, hc.service) for hc in still_hc}
    for removed_hc in set(hc_queryset) - set(still_hc):
        groupconfigs = GroupConfig.objects.filter(
            object_type__model__in=["clusterobject", "servicecomponent"], hosts=removed_hc.host
        )
        for gc in groupconfigs:
            if (gc.object_type.model == "clusterobject") and (
                (removed_hc.host, removed_hc.service) in host_service_of_still_hc
            ):
                continue

            gc.hosts.remove(removed_hc.host)

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

    ctx.event.send_state()
    cm.status_api.post_event("change_hostcomponentmap", "cluster", cluster.id)
    cm.issue.update_hierarchy_issues(cluster)
    for provider in [host.provider for host in Host.objects.filter(cluster=cluster)]:
        cm.issue.update_hierarchy_issues(provider)

    cm.issue.update_issue_after_deleting()
    load_service_map()
    for service in service_map:
        re_apply_object_policy(service)

    for hc in result:
        re_apply_object_policy(hc.service)

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
    def get_export(_cluster, _service, _pi):
        exports = []
        export_proto = {}
        for pe in PrototypeExport.objects.filter(prototype__name=_pi.name):
            # Merge all export groups of prototype to one export
            if pe.prototype.id in export_proto:
                continue

            export_proto[pe.prototype.id] = True
            if not version_in(pe.prototype.version, _pi):
                continue

            if pe.prototype.type == "cluster":
                for cls in Cluster.objects.filter(prototype=pe.prototype):
                    binded = get_bind(_cluster, _service, cls, None)
                    exports.append(
                        {
                            "obj_name": cls.name,
                            "bundle_name": cls.prototype.display_name,
                            "bundle_version": cls.prototype.version,
                            "id": {"cluster_id": cls.id},
                            "binded": bool(binded),
                            "bind_id": getattr(binded, "id", None),
                        }
                    )
            elif pe.prototype.type == "service":
                for co in ClusterObject.objects.filter(prototype=pe.prototype):
                    binded = get_bind(_cluster, _service, co.cluster, co)
                    exports.append(
                        {
                            "obj_name": co.cluster.name + "/" + co.prototype.display_name,
                            "bundle_name": co.prototype.display_name,
                            "bundle_version": co.prototype.version,
                            "id": {"cluster_id": co.cluster.id, "service_id": co.id},
                            "binded": bool(binded),
                            "bind_id": getattr(binded, "id", None),
                        }
                    )
            else:
                err("BIND_ERROR", f"unexpected export type: {pe.prototype.type}")

        return exports

    imports = []
    proto = cluster.prototype
    if service:
        proto = service.prototype

    for pi in PrototypeImport.objects.filter(prototype=proto):
        imports.append(
            {
                "id": pi.id,
                "name": pi.name,
                "required": pi.required,
                "multibind": pi.multibind,
                "exports": get_export(cluster, service, pi),
            }
        )

    return imports


def check_bind_post(bind_list):
    if not isinstance(bind_list, list):
        err("BIND_ERROR", "bind should be an array")

    for b in bind_list:
        if not isinstance(b, dict):
            err("BIND_ERROR", "bind item should be a map")

        if "import_id" not in b:
            err("BIND_ERROR", 'bind item does not have required "import_id" key')

        if not isinstance(b["import_id"], int):
            err("BIND_ERROR", 'bind item "import_id" value should be integer')

        if "export_id" not in b:
            err("BIND_ERROR", 'bind item does not have required "export_id" key')

        if not isinstance(b["export_id"], dict):
            err("BIND_ERROR", 'bind item "export_id" value should be a map')

        if "cluster_id" not in b["export_id"]:
            err("BIND_ERROR", 'bind item export_id does not have required "cluster_id" key')

        if not isinstance(b["export_id"]["cluster_id"], int):
            err("BIND_ERROR", 'bind item export_id "cluster_id" value should be integer')


def check_import_default(import_obj, export_obj):
    pi = PrototypeImport.objects.get(prototype=import_obj.prototype, name=export_obj.prototype.name)
    if not pi.default:
        return

    cl = ConfigLog.objects.get(obj_ref=import_obj.config, id=import_obj.config.current)
    if not cl.attr:
        return

    for name in json.loads(pi.default):
        if name in cl.attr:
            if "active" in cl.attr[name] and not cl.attr[name]["active"]:
                msg = 'Default import "{}" for {} is inactive'
                err("BIND_ERROR", msg.format(name, obj_ref(import_obj)))


def get_bind_obj(cluster, service):
    obj = cluster
    if service:
        obj = service

    return obj


def multi_bind(cluster, service, bind_list):  # pylint: disable=too-many-locals,too-many-statements
    def get_pi(import_id, _import_obj):
        _pi = PrototypeImport.obj.get(id=import_id)
        if _pi.prototype != _import_obj.prototype:
            _msg = "Import #{} does not belong to {}"
            err("BIND_ERROR", _msg.format(import_id, obj_ref(_import_obj)))

        return _pi

    def get_export_service(_b, _export_cluster):
        _export_co = None
        if "service_id" in _b["export_id"]:
            _export_co = ClusterObject.obj.get(id=_b["export_id"]["service_id"])
            if _export_co.cluster != _export_cluster:
                _msg = "export {} is not belong to {}"
                err("BIND_ERROR", _msg.format(obj_ref(_export_co), obj_ref(_export_cluster)))

        return _export_co

    def cook_key(_cluster, _service):
        if _service:
            return f"{_cluster.id}.{_service.id}"

        return str(_cluster.id)

    check_bind_post(bind_list)
    import_obj = get_bind_obj(cluster, service)
    old_bind = {}
    cb_list = ClusterBind.objects.filter(cluster=cluster, service=service)
    for cb in cb_list:
        old_bind[cook_key(cb.source_cluster, cb.source_service)] = cb

    new_bind = {}
    for b in bind_list:
        pi = get_pi(b["import_id"], import_obj)
        export_cluster = Cluster.obj.get(id=b["export_id"]["cluster_id"])
        export_obj = export_cluster
        export_co = get_export_service(b, export_cluster)
        if export_co:
            export_obj = export_co

        if cook_key(export_cluster, export_co) in new_bind:
            err("BIND_ERROR", "Bind list has duplicates")

        if pi.name != export_obj.prototype.name:
            msg = 'Export {} does not match import name "{}"'
            err("BIND_ERROR", msg.format(obj_ref(export_obj), pi.name))

        if not version_in(export_obj.prototype.version, pi):
            msg = 'Import "{}" of {} versions ({}, {}) does not match export version: {} ({})'
            err(
                "BIND_ERROR",
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
        for key, value in old_bind.items():
            if key in new_bind:
                continue

            export_obj = get_bind_obj(value.source_cluster, value.source_service)
            check_import_default(import_obj, export_obj)
            value.delete()
            logger.info("unbind %s from %s", obj_ref(export_obj), obj_ref(import_obj))

        for key, value in new_bind.items():
            if key in old_bind:
                continue

            (pi, cb, export_obj) = value
            check_multi_bind(pi, cluster, service, cb.source_cluster, cb.source_service)
            cb.save()
            logger.info("bind %s to %s", obj_ref(export_obj), obj_ref(import_obj))

        cm.issue.update_hierarchy_issues(cluster)

    return get_import(cluster, service)


def bind(cluster, service, export_cluster, export_service_id):  # pylint: disable=too-many-branches
    """
    Adapter between old and new bind interface
    /api/.../bind/ -> /api/.../import/
    bind() -> multi_bind()
    """
    export_service = None
    if export_service_id:
        export_service = ClusterObject.obj.get(cluster=export_cluster, id=export_service_id)
        if not PrototypeExport.objects.filter(prototype=export_service.prototype):
            err("BIND_ERROR", f"{obj_ref(export_service)} do not have exports")

        name = export_service.prototype.name
    else:
        if not PrototypeExport.objects.filter(prototype=export_cluster.prototype):
            err("BIND_ERROR", f"{obj_ref(export_cluster)} does not have exports")

        name = export_cluster.prototype.name

    import_obj = cluster
    if service:
        import_obj = service

    pi = None
    try:
        pi = PrototypeImport.obj.get(prototype=import_obj.prototype, name=name)
    except MultipleObjectsReturned:
        err("BIND_ERROR", "Old api does not support multi bind. Go to /api/v1/.../import/")

    bind_list = []
    for imp in get_import(cluster, service):
        for exp in imp["exports"]:
            if exp["binded"]:
                bind_list.append({"import_id": imp["id"], "export_id": exp["id"]})

    item = {"import_id": pi.id, "export_id": {"cluster_id": export_cluster.id}}
    if export_service:
        item["export_id"]["service_id"] = export_service.id

    bind_list.append(item)

    multi_bind(cluster, service, bind_list)
    res = {
        "export_cluster_id": export_cluster.id,
        "export_cluster_name": export_cluster.name,
        "export_cluster_prototype_name": export_cluster.prototype.name,
    }
    if export_service:
        res["export_service_id"] = export_service.id

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
                msg = "can not multi bind {} to {}"
                err("BIND_ERROR", msg.format(proto_ref(source_proto), obj_ref(cluster)))
        else:
            if source_proto == export_cluster.prototype:
                msg = "can not multi bind {} to {}"
                err("BIND_ERROR", msg.format(proto_ref(source_proto), obj_ref(cluster)))
