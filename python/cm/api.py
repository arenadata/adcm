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

# pylint: disable=too-many-lines

import json
from functools import wraps

from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction
from django.utils import timezone
from version_utils import rpm

from cm.adcm_config import (
    check_json_config,
    init_object_config,
    obj_ref,
    proto_ref,
    read_bundle_file,
    save_obj_config,
)
from cm.api_context import ctx
from cm.errors import raise_adcm_ex
from cm.issue import (
    check_bound_components,
    check_component_constraint,
    check_component_requires,
    update_hierarchy_issues,
    update_issue_after_deleting,
)
from cm.logger import logger
from cm.models import (
    ADCMEntity,
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
    ObjectType,
    Prototype,
    PrototypeExport,
    PrototypeImport,
    ServiceComponent,
    TaskLog,
)
from cm.status_api import api_request, post_event
from rbac.models import re_apply_object_policy


def check_license(proto: Prototype) -> None:
    if proto.license == "unaccepted":
        raise_adcm_ex(
            "LICENSE_ERROR", f'License for prototype "{proto.name}" {proto.type} {proto.version} is not accepted'
        )


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


def load_host_map():
    hosts = [
        {
            "id": host_data["id"],
            "maintenance_mode": not host_data["maintenance_mode"] == MaintenanceMode.OFF,
        }
        for host_data in Host.objects.values("id", "maintenance_mode")
    ]

    return api_request("post", "/object/host/", hosts)


def load_service_map():
    comps = {}
    hosts = {}
    hc_map = {}
    services = {}
    passive = {}
    for c in ServiceComponent.objects.filter(prototype__monitoring="passive"):
        passive[c.pk] = True

    for hc in HostComponent.objects.all():
        if hc.component.pk in passive:
            continue

        key = f"{hc.host.pk}.{hc.component.pk}"
        hc_map[key] = {"cluster": hc.cluster.pk, "service": hc.service.pk}
        if str(hc.cluster.pk) not in comps:
            comps[str(hc.cluster.pk)] = {}

        if str(hc.service.pk) not in comps[str(hc.cluster.pk)]:
            comps[str(hc.cluster.pk)][str(hc.service.pk)] = []

        comps[str(hc.cluster.pk)][str(hc.service.pk)].append(key)

    for host in Host.objects.filter(prototype__monitoring="active"):
        if host.cluster:
            cluster_pk = host.cluster.pk
        else:
            cluster_pk = 0

        if cluster_pk not in hosts:
            hosts[cluster_pk] = []

        hosts[cluster_pk].append(host.pk)

    for co in ClusterObject.objects.filter(prototype__monitoring="active"):
        if co.cluster.pk not in services:
            services[co.cluster.pk] = []

        services[co.cluster.pk].append(co.pk)

    m = {
        "hostservice": hc_map,
        "component": comps,
        "service": services,
        "host": hosts,
    }
    api_request("post", "/servicemap/", m)
    load_host_map()
    load_mm_objects()


def load_mm_objects():
    """send ids of all objects in mm to status server"""
    clusters = Cluster.objects.filter(prototype__type=ObjectType.Cluster, prototype__allow_maintenance_mode=True)

    service_ids = set()
    component_ids = set()
    host_ids = []

    for service in ClusterObject.objects.filter(cluster__in=clusters).prefetch_related("servicecomponent_set"):
        if service.maintenance_mode == MaintenanceMode.ON:
            service_ids.add(service.pk)
        for component in service.servicecomponent_set.all():
            if component.maintenance_mode == MaintenanceMode.ON:
                component_ids.add(component.pk)

    for host in Host.objects.filter(cluster__in=clusters):
        if host.maintenance_mode == MaintenanceMode.ON:
            host_ids.append(host.pk)

    data = {
        "services": list(service_ids),
        "components": list(component_ids),
        "hosts": host_ids,
    }
    return api_request("post", "/object/mm/", data)


def update_mm_objects(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        load_mm_objects()
        return res

    return wrapper


def add_cluster(proto, name, desc=""):
    if proto.type != "cluster":
        raise_adcm_ex("OBJ_TYPE_ERROR", f"Prototype type should be cluster, not {proto.type}")

    check_license(proto)
    with transaction.atomic():
        cluster = Cluster.objects.create(prototype=proto, name=name, description=desc)
        obj_conf = init_object_config(proto, cluster)
        cluster.config = obj_conf
        cluster.save()
        update_hierarchy_issues(cluster)

    post_event("create", "cluster", cluster.pk)
    load_service_map()
    logger.info("cluster #%s %s is added", cluster.pk, cluster.name)

    return cluster


def add_host(proto, provider, fqdn, desc=""):
    if proto.type != "host":
        raise_adcm_ex("OBJ_TYPE_ERROR", f"Prototype type should be host, not {proto.type}")

    check_license(proto)
    if proto.bundle != provider.prototype.bundle:
        raise_adcm_ex(
            "FOREIGN_HOST",
            f"Host prototype bundle #{proto.bundle.pk} does not match with "
            f"host provider bundle #{provider.prototype.bundle.pk}",
        )

    with transaction.atomic():
        host = Host.objects.create(prototype=proto, provider=provider, fqdn=fqdn, description=desc)
        obj_conf = init_object_config(proto, host)
        host.config = obj_conf
        host.save()
        host.add_to_concerns(ctx.lock)
        update_hierarchy_issues(host.provider)
        re_apply_object_policy(provider)

    ctx.event.send_state()
    post_event("create", "host", host.pk, "provider", str(provider.pk))
    load_service_map()
    logger.info("host #%s %s is added", host.pk, host.fqdn)

    return host


def add_host_provider(proto, name, desc=""):
    if proto.type != "provider":
        raise_adcm_ex("OBJ_TYPE_ERROR", f"Prototype type should be provider, not {proto.type}")

    check_license(proto)
    with transaction.atomic():
        provider = HostProvider.objects.create(prototype=proto, name=name, description=desc)
        obj_conf = init_object_config(proto, provider)
        provider.config = obj_conf
        provider.save()
        provider.add_to_concerns(ctx.lock)
        update_hierarchy_issues(provider)

    ctx.event.send_state()
    post_event("create", "provider", provider.pk)
    logger.info("host provider #%s %s is added", provider.pk, provider.name)

    return provider


def cancel_locking_tasks(obj: ADCMEntity, obj_deletion=False):
    for lock in obj.concerns.filter(type=ConcernType.Lock):
        for task in TaskLog.objects.filter(lock=lock):
            task.cancel(obj_deletion=obj_deletion)


def delete_host_provider(provider, cancel_tasks=True):
    hosts = Host.objects.filter(provider=provider)
    if hosts:
        raise_adcm_ex(
            "PROVIDER_CONFLICT", f'There is host #{hosts[0].pk} "{hosts[0].fqdn}" of host {obj_ref(provider)}'
        )

    if cancel_tasks:
        cancel_locking_tasks(provider, obj_deletion=True)

    provider_pk = provider.pk
    provider.delete()
    post_event("delete", "provider", provider_pk)
    logger.info("host provider #%s is deleted", provider_pk)


def add_host_to_cluster(cluster, host):
    if host.cluster:
        if host.cluster.pk != cluster.pk:
            raise_adcm_ex("FOREIGN_HOST", f"Host #{host.pk} belong to cluster #{host.cluster.pk}")
        else:
            raise_adcm_ex("HOST_CONFLICT")

    with transaction.atomic():
        DummyData.objects.filter(pk=1).update(date=timezone.now())

        host.cluster = cluster
        host.save()
        host.add_to_concerns(ctx.lock)
        update_hierarchy_issues(host)
        re_apply_object_policy(cluster)

    post_event("add", "host", host.pk, "cluster", str(cluster.pk))
    load_service_map()
    logger.info("host #%s %s is added to cluster #%s %s", host.pk, host.fqdn, cluster.pk, cluster.name)

    return host


def get_cluster_and_host(cluster_pk, fqdn, host_pk):
    cluster = Cluster.obj.get(pk=cluster_pk)
    host = None
    if fqdn:
        host = Host.obj.get(fqdn=fqdn)
    elif host_pk:
        if not isinstance(host_pk, int):
            raise_adcm_ex("HOST_NOT_FOUND", f'host_id must be integer (got "{host_pk}")')

        host = Host.obj.get(pk=host_pk)
    else:
        raise_adcm_ex("HOST_NOT_FOUND", "fqdn or host_id is mandatory args")

    return cluster, host


def add_host_to_cluster_by_pk(cluster_pk, fqdn, host_pk):
    """
    add host to cluster

    This is intended for use in adcm_add_host_to_cluster ansible plugin only
    """

    return add_host_to_cluster(*get_cluster_and_host(cluster_pk=cluster_pk, fqdn=fqdn, host_pk=host_pk))


def remove_host_from_cluster_by_pk(cluster_pk, fqdn, host_pk):
    """
    remove host from cluster

    This is intended for use in adcm_remove_host_from_cluster ansible plugin only
    """

    cluster, host = get_cluster_and_host(cluster_pk, fqdn, host_pk)
    if host.cluster != cluster:
        raise_adcm_ex("HOST_CONFLICT", "you can remove host only from you own cluster")

    remove_host_from_cluster(host)


def delete_host(host, cancel_tasks=True):
    cluster = host.cluster
    if cluster:
        raise_adcm_ex("HOST_CONFLICT", f'Host #{host.pk} "{host.fqdn}" belong to {obj_ref(cluster)}')

    if cancel_tasks:
        cancel_locking_tasks(host, obj_deletion=True)

    host_pk = host.pk
    host.delete()
    post_event("delete", "host", host_pk)
    load_service_map()
    update_issue_after_deleting()
    logger.info("host #%s is deleted", host_pk)


def delete_host_by_pk(host_pk):
    """
    Host deleting

    This is intended for use in adcm_delete_host ansible plugin only
    """

    host = Host.obj.get(pk=host_pk)
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


def delete_service_by_pk(service_pk):
    """
    Unconditional removal of service from cluster

    This is intended for use in adcm_delete_service ansible plugin only
    """

    with transaction.atomic():
        DummyData.objects.filter(pk=1).update(date=timezone.now())
        service = ClusterObject.obj.get(pk=service_pk)
        _clean_up_related_hc(service)
        ClusterBind.objects.filter(source_service=service).delete()
        delete_service(service=service)


def delete_service_by_name(service_name, cluster_pk):
    """
    Unconditional removal of service from cluster

    This is intended for use in adcm_delete_service ansible plugin only
    """

    with transaction.atomic():
        DummyData.objects.filter(pk=1).update(date=timezone.now())
        service = ClusterObject.obj.get(cluster__pk=cluster_pk, prototype__name=service_name)
        _clean_up_related_hc(service)
        ClusterBind.objects.filter(source_service=service).delete()
        delete_service(service=service)


def delete_service(service: ClusterObject) -> None:
    service_pk = service.pk
    service.delete()
    update_issue_after_deleting()
    update_hierarchy_issues(service.cluster)
    re_apply_object_policy(service.cluster)
    post_event("delete", "service", service_pk)
    load_service_map()
    logger.info("service #%s is deleted", service_pk)


def delete_cluster(cluster, cancel_tasks=True):
    if cancel_tasks:
        cancel_locking_tasks(cluster, obj_deletion=True)

    cluster_pk = cluster.pk
    hosts = cluster.host_set.all()
    host_pks = [str(host.pk) for host in hosts]
    hosts.update(maintenance_mode=MaintenanceMode.OFF)
    logger.debug(
        "Deleting cluster #%s. Set `%s` maintenance mode value for `%s` hosts.",
        cluster_pk,
        MaintenanceMode.OFF,
        ", ".join(host_pks),
    )
    cluster.delete()
    update_issue_after_deleting()
    post_event("delete", "cluster", cluster_pk)
    load_service_map()


def remove_host_from_cluster(host):
    cluster = host.cluster
    hc = HostComponent.objects.filter(cluster=cluster, host=host)
    if hc:
        return raise_adcm_ex("HOST_CONFLICT", f"Host #{host.pk} has component(s)")

    with transaction.atomic():
        host.maintenance_mode = MaintenanceMode.OFF
        host.cluster = None
        host.save()
        for group in cluster.group_config.all():
            group.hosts.remove(host)
            update_hierarchy_issues(host)

        host.remove_from_concerns(ctx.lock)
        update_hierarchy_issues(cluster)
        re_apply_object_policy(cluster)

    ctx.event.send_state()
    post_event("remove", "host", host.pk, "cluster", str(cluster.pk))
    load_service_map()

    return host


def unbind(cbind):
    import_obj = get_bind_obj(cbind.cluster, cbind.service)
    export_obj = get_bind_obj(cbind.source_cluster, cbind.source_service)
    check_import_default(import_obj, export_obj)
    cbind_pk = cbind.pk
    cbind_cluster_pk = cbind.cluster.pk
    with transaction.atomic():
        DummyData.objects.filter(id=1).update(date=timezone.now())
        cbind.delete()
        update_hierarchy_issues(cbind.cluster)

    post_event("delete", "bind", cbind_pk, "cluster", str(cbind_cluster_pk))


def add_service_to_cluster(cluster, proto):
    if proto.type != "service":
        raise_adcm_ex("OBJ_TYPE_ERROR", f"Prototype type should be service, not {proto.type}")

    check_license(proto)
    if not proto.shared:
        if cluster.prototype.bundle != proto.bundle:
            raise_adcm_ex(
                "SERVICE_CONFLICT",
                f'{proto_ref(proto)} does not belong to bundle '
                f'"{cluster.prototype.bundle.name}" {cluster.prototype.version}',
            )

    with transaction.atomic():
        cs = ClusterObject.objects.create(cluster=cluster, prototype=proto)
        obj_conf = init_object_config(proto, cs)
        cs.config = obj_conf
        cs.save()
        add_components_to_service(cluster, cs)
        update_hierarchy_issues(cs)
        re_apply_object_policy(cluster)

    post_event("add", "service", cs.pk, "cluster", str(cluster.pk))
    load_service_map()
    logger.info("service #%s %s is added to cluster #%s %s", cs.pk, cs.prototype.name, cluster.pk, cluster.name)

    return cs


def add_components_to_service(cluster, service):
    for comp in Prototype.objects.filter(type="component", parent=service.prototype):
        sc = ServiceComponent.objects.create(cluster=cluster, service=service, prototype=comp)
        obj_conf = init_object_config(comp, sc)
        sc.config = obj_conf
        sc.save()
        update_hierarchy_issues(sc)


def get_license(proto: Prototype) -> str | None:
    if not proto.license_path:
        return None
    if not isinstance(proto, Prototype):
        raise_adcm_ex("LICENSE_ERROR")
    return read_bundle_file(proto, proto.license_path, proto.bundle.hash, "license file")


def accept_license(proto: Prototype) -> None:
    if not proto.license_path:
        raise_adcm_ex("LICENSE_ERROR", "This bundle has no license")

    if proto.license == "absent":
        raise_adcm_ex("LICENSE_ERROR", "This bundle has no license")

    proto.license = "accepted"
    proto.save()


def update_obj_config(obj_conf, conf, attr, desc="") -> ConfigLog:
    if not isinstance(attr, dict):
        raise_adcm_ex("INVALID_CONFIG_UPDATE", "attr should be a map")

    obj = obj_conf.object
    if obj is None:
        raise_adcm_ex("INVALID_CONFIG_UPDATE", f'unknown object type "{obj_conf}"')

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
        update_hierarchy_issues(obj)
        re_apply_object_policy(obj)

    if group is not None:
        post_event("change_config", "group-config", group.pk, "version", str(cl.pk))
    else:
        post_event("change_config", proto.type, obj.pk, "version", str(cl.pk))

    return cl


def get_hc(cluster):
    if not cluster:
        return None

    hc_map = []
    for hc in HostComponent.objects.filter(cluster=cluster):
        hc_map.append(
            {
                "host_id": hc.host.pk,
                "service_id": hc.service.pk,
                "component_id": hc.component.pk,
            }
        )

    return hc_map


def check_sub_key(hc_in):
    def check_sub(_sub_key, _sub_type, _item):
        if _sub_key not in _item:
            raise_adcm_ex("INVALID_INPUT", f'"{_sub_key}" sub-field of hostcomponent is required')

        if not isinstance(_item[_sub_key], _sub_type):
            raise_adcm_ex("INVALID_INPUT", f'"{_sub_key}" sub-field of hostcomponent should be "{_sub_type}"')

    seen = {}
    if not isinstance(hc_in, list):
        raise_adcm_ex("INVALID_INPUT", "hostcomponent should be array")

    for item in hc_in:
        for sub_key, sub_type in (("service_id", int), ("host_id", int), ("component_id", int)):
            check_sub(sub_key, sub_type, item)

        key = (item.get("service_id", ""), item.get("host_id", ""), item.get("component_id", ""))
        if key not in seen:
            seen[key] = 1
        else:
            raise_adcm_ex("INVALID_INPUT", f"duplicate ({item}) in host service list")


def make_host_comp_list(cluster, hc_in):
    host_comp_list = []
    for item in hc_in:
        host = Host.obj.get(pk=item["host_id"])
        service = ClusterObject.obj.get(pk=item["service_id"], cluster=cluster)
        comp = ServiceComponent.obj.get(pk=item["component_id"], cluster=cluster, service=service)
        if not host.cluster:
            raise_adcm_ex("FOREIGN_HOST", f"host #{host.pk} {host.fqdn} does not belong to any cluster")

        if host.cluster.pk != cluster.pk:
            raise_adcm_ex(
                "FOREIGN_HOST",
                f"host {host.fqdn} (cluster #{host.cluster.pk}) does not belong to cluster #{cluster.pk}",
            )

        host_comp_list.append((service, host, comp))

    return host_comp_list


def check_hc(cluster, hc_in):
    check_sub_key(hc_in)
    host_comp_list = make_host_comp_list(cluster, hc_in)
    for service in ClusterObject.objects.filter(cluster=cluster):
        check_component_constraint(cluster, service.prototype, [i for i in host_comp_list if i[0] == service])

    check_component_requires(host_comp_list)
    check_bound_components(host_comp_list)
    check_maintenance_mode(cluster, host_comp_list)

    return host_comp_list


def check_maintenance_mode(cluster, host_comp_list):
    for (service, host, comp) in host_comp_list:
        try:
            HostComponent.objects.get(cluster=cluster, service=service, host=host, component=comp)
        except HostComponent.DoesNotExist:
            if host.maintenance_mode == MaintenanceMode.ON:
                raise_adcm_ex("INVALID_HC_HOST_IN_MM")


def still_existed_hc(cluster, host_comp_list):
    result = []
    for (service, host, comp) in host_comp_list:
        try:
            existed_hc = HostComponent.objects.get(cluster=cluster, service=service, host=host, component=comp)
            result.append(existed_hc)
        except HostComponent.DoesNotExist:
            continue

    return result


def save_hc(cluster, host_comp_list):
    # pylint: disable=too-many-locals

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
    for proto, host, comp in host_comp_list:
        hc = HostComponent(
            cluster=cluster,
            service=proto,
            host=host,
            component=comp,
        )
        hc.save()
        result.append(hc)

    ctx.event.send_state()
    post_event("change_hostcomponentmap", "cluster", cluster.pk)
    update_hierarchy_issues(cluster)
    for provider in [host.provider for host in Host.objects.filter(cluster=cluster)]:
        update_hierarchy_issues(provider)

    update_issue_after_deleting()
    load_service_map()
    for service in service_map:
        re_apply_object_policy(service)

    for hc in result:
        re_apply_object_policy(hc.service)

    return result


def add_hc(cluster, hc_in):
    host_comp_list = check_hc(cluster, hc_in)
    with transaction.atomic():
        DummyData.objects.filter(pk=1).update(date=timezone.now())
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
            if pe.prototype.pk in export_proto:
                continue

            export_proto[pe.prototype.pk] = True
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
                            "id": {"cluster_id": cls.pk},
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
                            "id": {"cluster_id": co.cluster.pk, "service_id": co.pk},
                            "binded": bool(binded),
                            "bind_id": getattr(binded, "id", None),
                        }
                    )
            else:
                raise_adcm_ex("BIND_ERROR", f"unexpected export type: {pe.prototype.type}")

        return exports

    imports = []
    proto = cluster.prototype
    if service:
        proto = service.prototype

    for pi in PrototypeImport.objects.filter(prototype=proto):
        imports.append(
            {
                "id": pi.pk,
                "name": pi.name,
                "required": pi.required,
                "multibind": pi.multibind,
                "exports": get_export(cluster, service, pi),
            }
        )

    return imports


def check_bind_post(bind_list):
    if not isinstance(bind_list, list):
        raise_adcm_ex("BIND_ERROR", "bind should be an array")

    for b in bind_list:
        if not isinstance(b, dict):
            raise_adcm_ex("BIND_ERROR", "bind item should be a map")

        if "import_id" not in b:
            raise_adcm_ex("BIND_ERROR", 'bind item does not have required "import_id" key')

        if not isinstance(b["import_id"], int):
            raise_adcm_ex("BIND_ERROR", 'bind item "import_id" value should be integer')

        if "export_id" not in b:
            raise_adcm_ex("BIND_ERROR", 'bind item does not have required "export_id" key')

        if not isinstance(b["export_id"], dict):
            raise_adcm_ex("BIND_ERROR", 'bind item "export_id" value should be a map')

        if "cluster_id" not in b["export_id"]:
            raise_adcm_ex("BIND_ERROR", 'bind item export_id does not have required "cluster_id" key')

        if not isinstance(b["export_id"]["cluster_id"], int):
            raise_adcm_ex("BIND_ERROR", 'bind item export_id "cluster_id" value should be integer')


def check_import_default(import_obj, export_obj):
    pi = PrototypeImport.objects.get(prototype=import_obj.prototype, name=export_obj.prototype.name)
    if not pi.default:
        return

    cl = ConfigLog.objects.get(obj_ref=import_obj.config, pk=import_obj.config.current)
    if not cl.attr:
        return

    for name in json.loads(pi.default):
        if name in cl.attr:
            if "active" in cl.attr[name] and not cl.attr[name]["active"]:
                raise_adcm_ex("BIND_ERROR", f'Default import "{name}" for {obj_ref(import_obj)} is inactive')


def get_bind_obj(cluster, service):
    obj = cluster
    if service:
        obj = service

    return obj


def multi_bind(cluster, service, bind_list):
    # pylint: disable=too-many-locals,too-many-statements

    def get_pi(import_pk, _import_obj):
        _pi = PrototypeImport.obj.get(id=import_pk)
        if _pi.prototype != _import_obj.prototype:
            raise_adcm_ex("BIND_ERROR", f"Import #{import_pk} does not belong to {obj_ref(_import_obj)}")

        return _pi

    def get_export_service(_b, _export_cluster):
        _export_co = None
        if "service_id" in _b["export_id"]:
            _export_co = ClusterObject.obj.get(id=_b["export_id"]["service_id"])
            if _export_co.cluster != _export_cluster:
                raise_adcm_ex("BIND_ERROR", f"export {obj_ref(_export_co)} is not belong to {obj_ref(_export_cluster)}")

        return _export_co

    def cook_key(_cluster, _service):
        if _service:
            return f"{_cluster.pk}.{_service.pk}"

        return str(_cluster.pk)

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
            raise_adcm_ex("BIND_ERROR", "Bind list has duplicates")

        if pi.name != export_obj.prototype.name:
            raise_adcm_ex("BIND_ERROR", f'Export {obj_ref(export_obj)} does not match import name "{pi.name}"')

        if not version_in(export_obj.prototype.version, pi):
            raise_adcm_ex(
                "BIND_ERROR",
                f'Import "{export_obj.prototype.name}" of { proto_ref(pi.prototype)} '
                f'versions ({pi.min_version}, {pi.max_version}) does not match export '
                f'version: {export_obj.prototype.version} ({obj_ref(export_obj)})',
            )

        cbind = ClusterBind(
            cluster=cluster,
            service=service,
            source_cluster=export_cluster,
            source_service=export_co,
        )
        new_bind[cook_key(export_cluster, export_co)] = pi, cbind, export_obj

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

            pi, cb, export_obj = value
            check_multi_bind(pi, cluster, service, cb.source_cluster, cb.source_service)
            cb.save()
            logger.info("bind %s to %s", obj_ref(export_obj), obj_ref(import_obj))

        update_hierarchy_issues(cluster)

    return get_import(cluster, service)


def bind(cluster, service, export_cluster, export_service_pk):
    # pylint: disable=too-many-branches

    """
    Adapter between old and new bind interface
    /api/.../bind/ -> /api/.../import/
    bind() -> multi_bind()
    """

    export_service = None
    if export_service_pk:
        export_service = ClusterObject.obj.get(cluster=export_cluster, id=export_service_pk)
        if not PrototypeExport.objects.filter(prototype=export_service.prototype):
            raise_adcm_ex("BIND_ERROR", f"{obj_ref(export_service)} do not have exports")

        name = export_service.prototype.name
    else:
        if not PrototypeExport.objects.filter(prototype=export_cluster.prototype):
            raise_adcm_ex("BIND_ERROR", f"{obj_ref(export_cluster)} does not have exports")

        name = export_cluster.prototype.name

    import_obj = cluster
    if service:
        import_obj = service

    pi = None
    try:
        pi = PrototypeImport.obj.get(prototype=import_obj.prototype, name=name)
    except MultipleObjectsReturned:
        raise_adcm_ex("BIND_ERROR", "Old api does not support multi bind. Go to /api/v1/.../import/")

    bind_list = []
    for imp in get_import(cluster, service):
        for exp in imp["exports"]:
            if exp["binded"]:
                bind_list.append({"import_id": imp["id"], "export_id": exp["id"]})

    item = {"import_id": pi.id, "export_id": {"cluster_id": export_cluster.pk}}
    if export_service:
        item["export_id"]["service_id"] = export_service.pk

    bind_list.append(item)

    multi_bind(cluster, service, bind_list)
    res = {
        "export_cluster_id": export_cluster.pk,
        "export_cluster_name": export_cluster.name,
        "export_cluster_prototype_name": export_cluster.prototype.name,
    }
    if export_service:
        res["export_service_id"] = export_service.pk

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
                raise_adcm_ex("BIND_ERROR", f"can not multi bind {proto_ref(source_proto)} to {obj_ref(cluster)}")
        else:
            if source_proto == export_cluster.prototype:
                raise_adcm_ex("BIND_ERROR", f"can not multi bind {proto_ref(source_proto)} to {obj_ref(cluster)}")
