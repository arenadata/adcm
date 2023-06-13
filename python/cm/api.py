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
from functools import partial, wraps

from cm.adcm_config.config import (
    init_object_config,
    process_json_config,
    read_bundle_file,
    save_obj_config,
)
from cm.adcm_config.utils import proto_ref
from cm.api_context import CTX
from cm.errors import raise_adcm_ex
from cm.issue import (
    check_bound_components,
    check_component_constraint,
    check_hc_requires,
    check_service_requires,
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
    GroupConfig,
    Host,
    HostComponent,
    HostProvider,
    MaintenanceMode,
    ObjectConfig,
    ObjectType,
    Prototype,
    PrototypeExport,
    PrototypeImport,
    ServiceComponent,
    TaskLog,
)
from cm.status_api import api_request, post_event
from cm.utils import obj_ref
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import MultipleObjectsReturned
from django.db.transaction import atomic, on_commit
from rbac.models import Policy, re_apply_object_policy
from rbac.roles import apply_policy_for_new_config
from version_utils import rpm


def check_license(prototype: Prototype) -> None:
    if prototype.license == "unaccepted":
        raise_adcm_ex(
            "LICENSE_ERROR",
            f'License for prototype "{prototype.name}" {prototype.type} {prototype.version} is not accepted',
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


def load_service_map():
    comps = {}
    hosts = {}
    hc_map = {}
    services = {}
    passive = {}
    for service_component in ServiceComponent.objects.filter(prototype__monitoring="passive"):
        passive[service_component.pk] = True

    for hostcomponent in HostComponent.objects.order_by("id"):
        if hostcomponent.component.pk in passive:
            continue

        key = f"{hostcomponent.host.pk}.{hostcomponent.component.pk}"
        hc_map[key] = {"cluster": hostcomponent.cluster.pk, "service": hostcomponent.service.pk}
        if str(hostcomponent.cluster.pk) not in comps:
            comps[str(hostcomponent.cluster.pk)] = {}

        if str(hostcomponent.service.pk) not in comps[str(hostcomponent.cluster.pk)]:
            comps[str(hostcomponent.cluster.pk)][str(hostcomponent.service.pk)] = []

        comps[str(hostcomponent.cluster.pk)][str(hostcomponent.service.pk)].append(key)

    for host in Host.objects.filter(prototype__monitoring="active"):
        if host.cluster:
            cluster_pk = host.cluster.pk
        else:
            cluster_pk = 0

        if cluster_pk not in hosts:
            hosts[cluster_pk] = []

        hosts[cluster_pk].append(host.pk)

    for service in ClusterObject.objects.filter(prototype__monitoring="active"):
        if service.cluster.pk not in services:
            services[service.cluster.pk] = []

        services[service.cluster.pk].append(service.pk)

    data = {
        "hostservice": hc_map,
        "component": comps,
        "service": services,
        "host": hosts,
    }
    api_request(method="post", url="servicemap/", data=data)
    load_mm_objects()


def load_mm_objects():
    """send ids of all objects in mm to status server"""
    clusters = Cluster.objects.filter(prototype__type=ObjectType.CLUSTER, prototype__allow_maintenance_mode=True)

    service_ids = set()
    component_ids = set()
    host_ids = []

    for service in ClusterObject.objects.filter(cluster__in=clusters).prefetch_related("servicecomponent_set"):
        if service.maintenance_mode == MaintenanceMode.ON:
            service_ids.add(service.pk)
        for component in service.servicecomponent_set.order_by("id"):
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
    return api_request(method="post", url="object/mm/", data=data)


def update_mm_objects(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        load_mm_objects()
        return res

    return wrapper


def add_cluster(prototype: Prototype, name: str, description: str = "") -> Cluster:
    if prototype.type != "cluster":
        raise_adcm_ex("OBJ_TYPE_ERROR", f"Prototype type should be cluster, not {prototype.type}")

    check_license(prototype)
    with atomic():
        cluster = Cluster.objects.create(prototype=prototype, name=name, description=description)
        obj_conf = init_object_config(prototype, cluster)
        cluster.config = obj_conf
        cluster.save()
        update_hierarchy_issues(cluster)

    post_event(event="create", object_id=cluster.pk, object_type="cluster")
    load_service_map()
    logger.info("cluster #%s %s is added", cluster.pk, cluster.name)

    return cluster


def add_host(prototype: Prototype, provider: HostProvider, fqdn: str, description: str = ""):
    if prototype.type != "host":
        raise_adcm_ex("OBJ_TYPE_ERROR", f"Prototype type should be host, not {prototype.type}")

    check_license(prototype)
    if prototype.bundle != provider.prototype.bundle:
        raise_adcm_ex(
            "FOREIGN_HOST",
            f"Host prototype bundle #{prototype.bundle.pk} does not match with "
            f"host provider bundle #{provider.prototype.bundle.pk}",
        )

    with atomic():
        host = Host.objects.create(prototype=prototype, provider=provider, fqdn=fqdn, description=description)
        obj_conf = init_object_config(prototype, host)
        host.config = obj_conf
        host.save()
        host.add_to_concerns(CTX.lock)
        update_hierarchy_issues(host.provider)
        re_apply_object_policy(provider)

    CTX.event.send_state()
    post_event(
        event="create", object_id=host.pk, object_type="host", details={"type": "provider", "value": str(provider.pk)}
    )
    load_service_map()
    logger.info("host #%s %s is added", host.pk, host.fqdn)

    return host


def add_host_provider(prototype: Prototype, name: str, description: str = ""):
    if prototype.type != "provider":
        raise_adcm_ex("OBJ_TYPE_ERROR", f"Prototype type should be provider, not {prototype.type}")

    check_license(prototype)
    with atomic():
        provider = HostProvider.objects.create(prototype=prototype, name=name, description=description)
        obj_conf = init_object_config(prototype, provider)
        provider.config = obj_conf
        provider.save()
        provider.add_to_concerns(CTX.lock)
        update_hierarchy_issues(provider)

    CTX.event.send_state()
    post_event(event="create", object_id=provider.pk, object_type="provider")
    logger.info("host provider #%s %s is added", provider.pk, provider.name)

    return provider


def cancel_locking_tasks(obj: ADCMEntity, obj_deletion=False):
    for lock in obj.concerns.filter(type=ConcernType.LOCK):
        for task in TaskLog.objects.filter(lock=lock):
            task.cancel(obj_deletion=obj_deletion)


def delete_host_provider(provider, cancel_tasks=True):
    hosts = Host.objects.filter(provider=provider)
    if hosts:
        raise_adcm_ex(
            "PROVIDER_CONFLICT",
            f'There is host #{hosts[0].pk} "{hosts[0].fqdn}" of host {obj_ref(provider)}',
        )

    if cancel_tasks:
        cancel_locking_tasks(provider, obj_deletion=True)

    provider_pk = provider.pk
    post_event(event="delete", object_id=provider.pk, object_type="provider")
    provider.delete()
    logger.info("host provider #%s is deleted", provider_pk)


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
        raise_adcm_ex(code="HOST_CONFLICT", msg=f'Host #{host.pk} "{host.fqdn}" belong to {obj_ref(cluster)}')

    if cancel_tasks:
        cancel_locking_tasks(obj=host, obj_deletion=True)

    host_pk = host.pk
    post_event(event="delete", object_id=host.pk, object_type="host")
    host.delete()
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

    queryset = (
        HostComponent.objects.filter(cluster=service.cluster)
        .exclude(service=service)
        .select_related("host", "component")
        .order_by("id")
    )
    new_hc_list = []
    for hostcomponent in queryset:
        new_hc_list.append((hostcomponent.service, hostcomponent.host, hostcomponent.component))

    save_hc(service.cluster, new_hc_list)


def delete_service_by_pk(service_pk):
    """
    Unconditional removal of service from cluster

    This is intended for use in adcm_delete_service ansible plugin only
    """

    service = ClusterObject.obj.get(pk=service_pk)
    with atomic():
        on_commit(
            func=partial(
                post_event, event="change_hostcomponentmap", object_id=service.cluster.pk, object_type="cluster"
            )
        )
        _clean_up_related_hc(service=service)
        ClusterBind.objects.filter(source_service=service).delete()
        delete_service(service=service)


def delete_service_by_name(service_name, cluster_pk):
    """
    Unconditional removal of service from cluster

    This is intended for use in adcm_delete_service ansible plugin only
    """

    service = ClusterObject.obj.get(cluster__pk=cluster_pk, prototype__name=service_name)
    with atomic():
        on_commit(
            func=partial(
                post_event, event="change_hostcomponentmap", object_id=service.cluster.pk, object_type="cluster"
            )
        )
        _clean_up_related_hc(service=service)
        ClusterBind.objects.filter(source_service=service).delete()
        delete_service(service=service)


def delete_service(service: ClusterObject) -> None:
    service_pk = service.pk
    post_event(event="delete", object_id=service.pk, object_type="service")
    service.delete()
    update_issue_after_deleting()
    update_hierarchy_issues(service.cluster)
    re_apply_object_policy(service.cluster)
    load_service_map()
    logger.info("service #%s is deleted", service_pk)


@atomic
def delete_cluster(cluster, cancel_tasks=True):
    if cancel_tasks:
        cancel_locking_tasks(cluster, obj_deletion=True)

    cluster_pk = cluster.pk
    hosts = cluster.host_set.order_by("id")
    host_pks = [str(host.pk) for host in hosts]
    hosts.update(maintenance_mode=MaintenanceMode.OFF)
    logger.debug(
        "Deleting cluster #%s. Set `%s` maintenance mode value for `%s` hosts.",
        cluster_pk,
        MaintenanceMode.OFF,
        ", ".join(host_pks),
    )
    post_event(event="delete", object_id=cluster.pk, object_type="cluster")
    cluster.delete()
    update_issue_after_deleting()
    load_service_map()


def remove_host_from_cluster(host: Host) -> Host:
    cluster = host.cluster
    hostcomponent = HostComponent.objects.filter(cluster=cluster, host=host)
    if hostcomponent:
        return raise_adcm_ex(code="HOST_CONFLICT", msg=f"Host #{host.pk} has component(s)")

    if cluster.state == "upgrading":
        return raise_adcm_ex(code="HOST_CONFLICT", msg="It is forbidden to delete host from cluster in upgrade mode")

    with atomic():
        host.maintenance_mode = MaintenanceMode.OFF
        host.cluster = None
        host.save()

        for group in cluster.group_config.order_by("id"):
            group.hosts.remove(host)
            update_hierarchy_issues(obj=host)

        host.remove_from_concerns(CTX.lock)
        update_hierarchy_issues(obj=cluster)
        re_apply_object_policy(apply_object=cluster)

    CTX.event.send_state()
    post_event(
        event="remove", object_id=host.pk, object_type="host", details={"type": "cluster", "value": str(cluster.pk)}
    )
    load_service_map()

    return host


def unbind(cbind):
    import_obj = get_bind_obj(cbind.cluster, cbind.service)
    export_obj = get_bind_obj(cbind.source_cluster, cbind.source_service)
    check_import_default(import_obj, export_obj)

    with atomic():
        post_event(
            event="delete",
            object_id=cbind.pk,
            object_type="cbind",
            details={"type": "cluster", "value": str(cbind.cluster.pk)},
        )
        cbind.delete()
        update_hierarchy_issues(cbind.cluster)


def add_service_to_cluster(cluster: Cluster, proto: Prototype) -> ClusterObject:
    if proto.type != "service":
        raise_adcm_ex(code="OBJ_TYPE_ERROR", msg=f"Prototype type should be service, not {proto.type}")

    check_license(prototype=proto)
    if not proto.shared:
        if cluster.prototype.bundle != proto.bundle:
            raise_adcm_ex(
                code="SERVICE_CONFLICT",
                msg=f"{proto_ref(prototype=proto)} does not belong to bundle "
                f'"{cluster.prototype.bundle.name}" {cluster.prototype.version}',
            )

    with atomic():
        service = ClusterObject.objects.create(cluster=cluster, prototype=proto)
        obj_conf = init_object_config(proto=proto, obj=service)
        service.config = obj_conf
        service.save(update_fields=["config"])
        add_components_to_service(cluster=cluster, service=service)
        update_hierarchy_issues(obj=cluster)
        re_apply_object_policy(apply_object=cluster)

    post_event(
        event="add", object_id=service.pk, object_type="service", details={"type": "cluster", "value": str(cluster.pk)}
    )
    load_service_map()
    logger.info(
        "service #%s %s is added to cluster #%s %s",
        service.pk,
        service.prototype.name,
        cluster.pk,
        cluster.name,
    )

    return service


def add_components_to_service(cluster: Cluster, service: ClusterObject) -> None:
    for comp in Prototype.objects.filter(type="component", parent=service.prototype):
        service_component = ServiceComponent.objects.create(cluster=cluster, service=service, prototype=comp)
        obj_conf = init_object_config(proto=comp, obj=service_component)
        service_component.config = obj_conf
        service_component.save(update_fields=["config"])
        update_hierarchy_issues(obj=service_component)


def get_license(proto: Prototype) -> str | None:
    if not proto.license_path:
        return None

    if not isinstance(proto, Prototype):
        raise_adcm_ex("LICENSE_ERROR")

    return read_bundle_file(proto=proto, fname=proto.license_path, bundle_hash=proto.bundle.hash, ref="license file")


def accept_license(proto: Prototype) -> None:
    if not proto.license_path:
        raise_adcm_ex("LICENSE_ERROR", "This bundle has no license")

    if proto.license == "absent":
        raise_adcm_ex("LICENSE_ERROR", "This bundle has no license")

    Prototype.objects.filter(license_hash=proto.license_hash, license="unaccepted").update(license="accepted")


def update_obj_config(obj_conf: ObjectConfig, config: dict, attr: dict, description: str = "") -> ConfigLog:
    if not isinstance(attr, dict):
        raise_adcm_ex("INVALID_CONFIG_UPDATE", "attr should be a map")

    obj: ADCMEntity = obj_conf.object
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
    new_conf = process_json_config(
        proto=proto,
        obj=group or obj,
        new_config=config,
        current_config=old_conf.config,
        new_attr=attr,
        current_attr=old_conf.attr,
    )
    with atomic():
        config_log = save_obj_config(obj_conf=obj_conf, conf=new_conf, attr=attr, desc=description)
        update_hierarchy_issues(obj=obj)
        apply_policy_for_new_config(config_object=obj, config_log=config_log)

    if group is not None:
        post_event(
            event="change_config",
            object_id=group.pk,
            object_type="group-config",
            details={"type": "version", "value": str(config_log.pk)},
        )
    else:
        post_event(
            event="change_config",
            object_id=obj.pk,
            object_type=obj.prototype.type,
            details={"type": "version", "value": str(config_log.pk)},
        )

    return config_log


def set_object_config(obj: ADCMEntity, config: dict, attr: dict) -> ConfigLog:
    new_conf = process_json_config(proto=obj.prototype, obj=obj, new_config=config, new_attr=attr)

    with atomic():
        config_log = save_obj_config(obj_conf=obj.config, conf=new_conf, attr=attr, desc="ansible update")
        update_hierarchy_issues(obj=obj)
        apply_policy_for_new_config(config_object=obj, config_log=config_log)

    post_event(
        event="change_config",
        object_id=obj.pk,
        object_type=obj.prototype.type,
        details={"type": "version", "value": str(config_log.pk)},
    )
    return config_log


def get_hc(cluster: Cluster | None) -> list[dict] | None:
    if not cluster:
        return None

    hc_map = []
    for hostcomponent in HostComponent.objects.filter(cluster=cluster):
        hc_map.append(
            {
                "host_id": hostcomponent.host.pk,
                "service_id": hostcomponent.service.pk,
                "component_id": hostcomponent.component.pk,
            },
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


def make_host_comp_list(cluster: Cluster, hc_in: list[dict]) -> list[tuple[ClusterObject, Host, ServiceComponent]]:
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


def check_hc(cluster: Cluster, hc_in: list[dict]) -> list[tuple[ClusterObject, Host, ServiceComponent]]:
    check_sub_key(hc_in=hc_in)
    host_comp_list = make_host_comp_list(cluster=cluster, hc_in=hc_in)

    check_hc_requires(shc_list=host_comp_list)
    check_bound_components(shc_list=host_comp_list)
    for service in ClusterObject.objects.filter(cluster=cluster):
        check_component_constraint(
            cluster=cluster, service_prototype=service.prototype, hc_in=[i for i in host_comp_list if i[0] == service]
        )
        check_service_requires(cluster=cluster, proto=service.prototype)
    check_maintenance_mode(cluster=cluster, host_comp_list=host_comp_list)

    return host_comp_list


def check_maintenance_mode(
    cluster: Cluster, host_comp_list: list[tuple[ClusterObject, Host, ServiceComponent]]
) -> None:
    for service, host, comp in host_comp_list:
        try:
            HostComponent.objects.get(cluster=cluster, service=service, host=host, component=comp)
        except HostComponent.DoesNotExist:
            if host.maintenance_mode == MaintenanceMode.ON:
                raise_adcm_ex("INVALID_HC_HOST_IN_MM")


def still_existed_hc(cluster: Cluster, host_comp_list: list[tuple[ClusterObject, Host, ServiceComponent]]) -> list:
    result = []
    for service, host, comp in host_comp_list:
        try:
            existed_hc = HostComponent.objects.get(cluster=cluster, service=service, host=host, component=comp)
            result.append(existed_hc)
        except HostComponent.DoesNotExist:
            continue

    return result


def save_hc(
    cluster: Cluster, host_comp_list: list[tuple[ClusterObject, Host, ServiceComponent]]
) -> list[HostComponent]:
    # pylint: disable=too-many-locals

    hc_queryset = HostComponent.objects.filter(cluster=cluster).order_by("id")
    service_set = {hc.service for hc in hc_queryset}
    old_hosts = {i.host for i in hc_queryset.select_related("host")}
    new_hosts = {i[1] for i in host_comp_list}

    for removed_host in old_hosts.difference(new_hosts):
        removed_host.remove_from_concerns(CTX.lock)

    for added_host in new_hosts.difference(old_hosts):
        added_host.add_to_concerns(CTX.lock)

    still_hc = still_existed_hc(cluster, host_comp_list)
    host_service_of_still_hc = {(hc.host, hc.service) for hc in still_hc}

    for removed_hc in set(hc_queryset) - set(still_hc):
        groupconfigs = GroupConfig.objects.filter(
            object_type__model__in=["clusterobject", "servicecomponent"],
            hosts=removed_hc.host,
        )
        for group_config in groupconfigs:
            if (group_config.object_type.model == "clusterobject") and (
                (removed_hc.host, removed_hc.service) in host_service_of_still_hc
            ):
                continue

            group_config.hosts.remove(removed_hc.host)

    hc_queryset.delete()
    host_component_list = []

    for proto, host, comp in host_comp_list:
        host_component = HostComponent(
            cluster=cluster,
            service=proto,
            host=host,
            component=comp,
        )
        host_component.save()
        host_component_list.append(host_component)

    CTX.event.send_state()
    update_hierarchy_issues(cluster)

    for provider in {host.provider for host in Host.objects.filter(cluster=cluster)}:
        update_hierarchy_issues(provider)

    update_issue_after_deleting()
    load_service_map()

    for host_component_item in host_component_list:
        service_set.add(host_component_item.service)

    if service_set:
        service_list = list(service_set)
        service_content_type = ContentType.objects.get_for_model(model=service_list[0])
        for service in service_list:
            for policy in Policy.objects.filter(
                object__object_id=service.pk, object__content_type=service_content_type
            ):
                policy.apply()

        for policy in Policy.objects.filter(
            object__object_id=service_list[0].cluster.pk,
            object__content_type=ContentType.objects.get_for_model(model=service_list[0].cluster),
        ):
            policy.apply()

    return host_component_list


def add_hc(cluster: Cluster, hc_in: list[dict]) -> list[HostComponent]:
    host_comp_list = check_hc(cluster=cluster, hc_in=hc_in)

    with atomic():
        on_commit(
            func=partial(post_event, event="change_hostcomponentmap", object_id=cluster.pk, object_type="cluster")
        )
        new_hc = save_hc(cluster=cluster, host_comp_list=host_comp_list)

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
        for prototype_export in PrototypeExport.objects.filter(prototype__name=_pi.name):
            # Merge all export groups of prototype to one export
            if prototype_export.prototype.pk in export_proto:
                continue

            export_proto[prototype_export.prototype.pk] = True
            if not version_in(prototype_export.prototype.version, _pi):
                continue

            if prototype_export.prototype.type == "cluster":
                for cls in Cluster.objects.filter(prototype=prototype_export.prototype):
                    bound = get_bind(_cluster, _service, cls, None)
                    exports.append(
                        {
                            "obj_name": cls.name,
                            "bundle_name": cls.prototype.display_name,
                            "bundle_version": cls.prototype.version,
                            "id": {"cluster_id": cls.pk},
                            "binded": bool(bound),
                            "bind_id": getattr(bound, "id", None),
                        },
                    )
            elif prototype_export.prototype.type == "service":
                for service in ClusterObject.objects.filter(prototype=prototype_export.prototype):
                    bound = get_bind(_cluster, _service, service.cluster, service)
                    exports.append(
                        {
                            "obj_name": service.cluster.name + "/" + service.prototype.display_name,
                            "bundle_name": service.prototype.display_name,
                            "bundle_version": service.prototype.version,
                            "id": {"cluster_id": service.cluster.pk, "service_id": service.pk},
                            "binded": bool(bound),
                            "bind_id": getattr(bound, "id", None),
                        },
                    )
            else:
                raise_adcm_ex("BIND_ERROR", f"unexpected export type: {prototype_export.prototype.type}")

        return exports

    imports = []
    proto = cluster.prototype
    if service:
        proto = service.prototype

    for prototype_import in PrototypeImport.objects.filter(prototype=proto):
        imports.append(
            {
                "id": prototype_import.pk,
                "name": prototype_import.name,
                "required": prototype_import.required,
                "multibind": prototype_import.multibind,
                "exports": get_export(cluster, service, prototype_import),
            },
        )

    return imports


def check_bind_post(bind_list):
    if not isinstance(bind_list, list):
        raise_adcm_ex("BIND_ERROR", "bind should be an array")

    for bind_item in bind_list:
        if not isinstance(bind_item, dict):
            raise_adcm_ex("BIND_ERROR", "bind item should be a map")

        if "import_id" not in bind_item:
            raise_adcm_ex("BIND_ERROR", 'bind item does not have required "import_id" key')

        if not isinstance(bind_item["import_id"], int):
            raise_adcm_ex("BIND_ERROR", 'bind item "import_id" value should be integer')

        if "export_id" not in bind_item:
            raise_adcm_ex("BIND_ERROR", 'bind item does not have required "export_id" key')

        if not isinstance(bind_item["export_id"], dict):
            raise_adcm_ex("BIND_ERROR", 'bind item "export_id" value should be a map')

        if "cluster_id" not in bind_item["export_id"]:
            raise_adcm_ex("BIND_ERROR", 'bind item export_id does not have required "cluster_id" key')

        if not isinstance(bind_item["export_id"]["cluster_id"], int):
            raise_adcm_ex("BIND_ERROR", 'bind item export_id "cluster_id" value should be integer')


def check_import_default(import_obj, export_obj):
    prototype_import = PrototypeImport.objects.get(prototype=import_obj.prototype, name=export_obj.prototype.name)
    if not prototype_import.default:
        return

    config_log = ConfigLog.objects.get(obj_ref=import_obj.config, pk=import_obj.config.current)
    if not config_log.attr:
        return

    for name in json.loads(prototype_import.default):
        if name in config_log.attr:
            if "active" in config_log.attr[name] and not config_log.attr[name]["active"]:
                raise_adcm_ex("BIND_ERROR", f'Default import "{name}" for {obj_ref(import_obj)} is inactive')


def get_bind_obj(cluster, service):
    obj = cluster
    if service:
        obj = service

    return obj


def multi_bind(cluster, service, bind_list):
    # pylint: disable=too-many-locals,too-many-statements

    def get_prototype_import(import_pk, _import_obj):
        _pi = PrototypeImport.obj.get(id=import_pk)
        if _pi.prototype != _import_obj.prototype:
            raise_adcm_ex("BIND_ERROR", f"Import #{import_pk} does not belong to {obj_ref(_import_obj)}")

        return _pi

    def get_export_service(_b, _export_cluster):
        _export_co = None
        if "service_id" in _b["export_id"]:
            _export_co = ClusterObject.obj.get(id=_b["export_id"]["service_id"])
            if _export_co.cluster != _export_cluster:
                raise_adcm_ex(
                    "BIND_ERROR",
                    f"export {obj_ref(_export_co)} is not belong to {obj_ref(_export_cluster)}",
                )

        return _export_co

    def cook_key(_cluster, _service):
        if _service:
            return f"{_cluster.pk}.{_service.pk}"

        return str(_cluster.pk)

    check_bind_post(bind_list)
    import_obj = get_bind_obj(cluster, service)
    old_bind = {}
    cluster_bind_list = ClusterBind.objects.filter(cluster=cluster, service=service)
    for cluster_bind in cluster_bind_list:
        old_bind[cook_key(cluster_bind.source_cluster, cluster_bind.source_service)] = cluster_bind

    new_bind = {}
    for bind_item in bind_list:
        prototype_import = get_prototype_import(bind_item["import_id"], import_obj)
        export_cluster = Cluster.obj.get(id=bind_item["export_id"]["cluster_id"])
        export_obj = export_cluster
        export_co = get_export_service(bind_item, export_cluster)
        if export_co:
            export_obj = export_co

        if cook_key(export_cluster, export_co) in new_bind:
            raise_adcm_ex("BIND_ERROR", "Bind list has duplicates")

        if prototype_import.name != export_obj.prototype.name:
            raise_adcm_ex(
                "BIND_ERROR",
                f'Export {obj_ref(export_obj)} does not match import name "{prototype_import.name}"',
            )

        if not version_in(export_obj.prototype.version, prototype_import):
            raise_adcm_ex(
                "BIND_ERROR",
                f'Import "{export_obj.prototype.name}" of { proto_ref(prototype_import.prototype)} '
                f"versions ({prototype_import.min_version}, {prototype_import.max_version}) does not match export "
                f"version: {export_obj.prototype.version} ({obj_ref(export_obj)})",
            )

        cluster_bind = ClusterBind(
            cluster=cluster,
            service=service,
            source_cluster=export_cluster,
            source_service=export_co,
        )
        new_bind[cook_key(export_cluster, export_co)] = prototype_import, cluster_bind, export_obj

    with atomic():
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

            prototype_import, cluster_bind, export_obj = value
            check_multi_bind(
                prototype_import,
                cluster,
                service,
                cluster_bind.source_cluster,
                cluster_bind.source_service,
            )
            cluster_bind.save()
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

    prototype_import = None
    try:
        prototype_import = PrototypeImport.obj.get(prototype=import_obj.prototype, name=name)
    except MultipleObjectsReturned:
        raise_adcm_ex("BIND_ERROR", "Old api does not support multi bind. Go to /api/v1/.../import/")

    bind_list = []
    for imp in get_import(cluster, service):
        for exp in imp["exports"]:
            if exp["binded"]:
                bind_list.append({"import_id": imp["id"], "export_id": exp["id"]})

    item = {"import_id": prototype_import.id, "export_id": {"cluster_id": export_cluster.pk}}
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


def check_multi_bind(actual_import, cluster, service, export_cluster, export_service, cluster_bind_list=None):
    if actual_import.multibind:
        return

    if cluster_bind_list is None:
        cluster_bind_list = ClusterBind.objects.filter(cluster=cluster, service=service)

    for cluster_bind in cluster_bind_list:
        if cluster_bind.source_service:
            source_proto = cluster_bind.source_service.prototype
        else:
            source_proto = cluster_bind.source_cluster.prototype

        if export_service:
            if source_proto == export_service.prototype:
                raise_adcm_ex("BIND_ERROR", f"can not multi bind {proto_ref(source_proto)} to {obj_ref(cluster)}")
        else:
            if source_proto == export_cluster.prototype:
                raise_adcm_ex("BIND_ERROR", f"can not multi bind {proto_ref(source_proto)} to {obj_ref(cluster)}")


def add_host_to_cluster(cluster: Cluster, host: Host) -> Host:
    if host.cluster:
        if host.cluster.pk != cluster.pk:
            raise_adcm_ex("FOREIGN_HOST", f"Host #{host.pk} belong to cluster #{host.cluster.pk}")
        else:
            raise_adcm_ex("HOST_CONFLICT")

    with atomic():
        host.cluster = cluster
        host.save()
        host.add_to_concerns(CTX.lock)
        update_hierarchy_issues(host)
        re_apply_object_policy(cluster)

    post_event(
        event="add", object_id=host.pk, object_type="host", details={"type": "cluster", "value": str(cluster.pk)}
    )
    load_service_map()
    logger.info("host #%s %s is added to cluster #%s %s", host.pk, host.fqdn, cluster.pk, cluster.name)

    return host
