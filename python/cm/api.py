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
from functools import partial
from typing import Literal, TypedDict
import json

from adcm_version import compare_prototype_versions
from core.cluster.operations import find_hosts_difference
from core.types import CoreObjectDescriptor
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import MultipleObjectsReturned
from django.db.transaction import atomic, on_commit
from rbac.models import Policy, re_apply_object_policy
from rbac.roles import apply_policy_for_new_config

from cm.adcm_config.config import (
    init_object_config,
    process_json_config,
    reraise_file_errors_as_adcm_ex,
    save_object_config,
)
from cm.adcm_config.utils import proto_ref
from cm.converters import orm_object_to_core_type
from cm.errors import AdcmEx, raise_adcm_ex
from cm.issue import (
    add_concern_to_object,
    check_bound_components,
    check_component_constraint,
    check_hc_requires,
    check_service_requires,
    remove_concern_from_object,
    update_hierarchy_issues,
    update_issues_and_flags_after_deleting,
)
from cm.logger import logger
from cm.models import (
    ADCM,
    ActionHostGroup,
    ADCMEntity,
    AnsibleConfig,
    Cluster,
    ClusterBind,
    ClusterObject,
    ConcernItem,
    ConcernType,
    ConfigLog,
    GroupConfig,
    Host,
    HostComponent,
    HostProvider,
    MainObject,
    MaintenanceMode,
    ObjectConfig,
    Prototype,
    PrototypeExport,
    PrototypeImport,
    ServiceComponent,
    TaskLog,
)
from cm.services.action_host_group import ActionHostGroupRepo
from cm.services.cluster import retrieve_clusters_topology
from cm.services.concern.flags import BuiltInFlag, raise_flag, update_hierarchy
from cm.services.concern.locks import get_lock_on_object
from cm.services.group_config import ConfigHostGroupRepo
from cm.services.status.notify import reset_hc_map, reset_objects_in_mm
from cm.status_api import (
    send_config_creation_event,
    send_delete_service_event,
    send_host_component_map_update_event,
)
from cm.utils import obj_ref

# There's no good place to place it for now.
# Since it's more about API than `cm.services.job`, it'll live here.
# But don't stick to it.
DEFAULT_FORKS_AMOUNT: str = "5"


def check_license(prototype: Prototype) -> None:
    if prototype.license == "unaccepted":
        raise_adcm_ex(
            "LICENSE_ERROR",
            f'License for prototype "{prototype.name}" {prototype.type} {prototype.version} is not accepted',
        )


def is_version_suitable(version: str, prototype_import: PrototypeImport) -> bool:
    if (
        prototype_import.min_strict
        and compare_prototype_versions(version, prototype_import.min_version) <= 0
        or prototype_import.min_version
        and compare_prototype_versions(version, prototype_import.min_version) < 0
    ):
        return False

    if (
        prototype_import.max_strict
        and compare_prototype_versions(version, prototype_import.max_version) >= 0
        or prototype_import.max_version
        and compare_prototype_versions(version, prototype_import.max_version) > 0
    ):
        return False

    return True


def add_cluster(prototype: Prototype, name: str, description: str = "") -> Cluster:
    if prototype.type != "cluster":
        raise_adcm_ex("OBJ_TYPE_ERROR", f"Prototype type should be cluster, not {prototype.type}")

    check_license(prototype)

    with atomic():
        cluster = Cluster.objects.create(prototype=prototype, name=name, description=description)
        obj_conf = init_object_config(prototype, cluster)
        cluster.config = obj_conf
        cluster.save()

        AnsibleConfig.objects.create(
            value={"defaults": {"forks": DEFAULT_FORKS_AMOUNT}},
            object_id=cluster.id,
            object_type=ContentType.objects.get_for_model(Cluster),
        )

        update_hierarchy_issues(cluster)

    reset_hc_map()

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
        add_concern_to_object(object_=host, concern=get_lock_on_object(object_=provider))
        update_hierarchy_issues(host.provider)
        re_apply_object_policy(provider)

    reset_hc_map()
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
        update_hierarchy_issues(provider)

    logger.info("host provider #%s %s is added", provider.pk, provider.name)

    return provider


def cancel_locking_tasks(obj: ADCMEntity, obj_deletion=False):
    for lock in obj.concerns.filter(type=ConcernType.LOCK, owner_type=obj.content_type, owner_id=obj.id):
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

    provider.delete()
    logger.info("host provider #%s is deleted", provider.pk)


def delete_host(host: Host, cancel_tasks: bool = True) -> None:
    cluster = host.cluster
    if cluster:
        raise AdcmEx(code="HOST_CONFLICT", msg="Unable to remove a host associated with a cluster.")

    if cancel_tasks:
        cancel_locking_tasks(obj=host, obj_deletion=True)

    host_pk = host.pk
    host.delete()
    reset_hc_map()
    reset_objects_in_mm()
    update_issues_and_flags_after_deleting()
    logger.info("host #%s is deleted", host_pk)


def delete_service(service: ClusterObject) -> None:
    service_pk = service.pk
    service.delete()

    update_issues_and_flags_after_deleting()
    update_hierarchy_issues(service.cluster)

    keep_objects = defaultdict(set)
    for task in TaskLog.objects.filter(
        object_type=ContentType.objects.get_for_model(ClusterObject), object_id=service_pk
    ).prefetch_related("joblog_set", "joblog_set__logstorage_set"):
        keep_objects[task.__class__].add(task.pk)
        for job in task.joblog_set.all():
            keep_objects[job.__class__].add(job.pk)
            for log in job.logstorage_set.all():
                keep_objects[log.__class__].add(log.pk)

    re_apply_object_policy(apply_object=service.cluster, keep_objects=keep_objects)

    reset_hc_map()
    on_commit(func=partial(send_delete_service_event, service_id=service_pk))
    logger.info("service #%s is deleted", service_pk)


def delete_cluster(cluster: Cluster) -> None:
    tasks = []
    for lock in cluster.concerns.filter(type=ConcernType.LOCK):
        for task in TaskLog.objects.filter(lock=lock):
            tasks.append(task)

    hosts = cluster.host_set.order_by("id")
    host_pks = [str(host.pk) for host in hosts]
    hosts.update(maintenance_mode=MaintenanceMode.OFF)
    logger.debug(
        "Deleting cluster #%s. Set `%s` maintenance mode value for `%s` hosts.",
        cluster.pk,
        MaintenanceMode.OFF,
        ", ".join(host_pks),
    )
    cluster.delete()
    update_issues_and_flags_after_deleting()
    reset_hc_map()
    reset_objects_in_mm()

    for task in tasks:
        task.cancel(obj_deletion=True)


def remove_host_from_cluster(host: Host) -> Host:
    cluster = host.cluster

    if HostComponent.objects.filter(cluster=cluster, host=host).exists():
        return raise_adcm_ex(code="HOST_CONFLICT", msg="There are components on the host.")

    if cluster.state == "upgrading":
        return raise_adcm_ex(code="HOST_CONFLICT", msg="It is forbidden to delete host from cluster in upgrade mode")

    with atomic():
        # As the host is bounded to a certain cluster it is safe to delete all relations at once
        ActionHostGroup.hosts.through.objects.filter(host_id=host.id).delete()
        host.maintenance_mode = MaintenanceMode.OFF
        host.cluster = None
        host.save()

        for group in cluster.group_config.order_by("id"):
            group.hosts.remove(host)
            update_hierarchy_issues(obj=host)

        # if there's no lock on cluster, nothing should be removed
        remove_concern_from_object(object_=host, concern=get_lock_on_object(object_=cluster))
        update_hierarchy_issues(obj=cluster)
        re_apply_object_policy(apply_object=cluster)

    reset_hc_map()
    reset_objects_in_mm()

    return host


def unbind(cbind):
    import_obj = get_bind_obj(cbind.cluster, cbind.service)
    export_obj = get_bind_obj(cbind.source_cluster, cbind.source_service)
    check_import_default(import_obj, export_obj)

    with atomic():
        cbind.delete()
        update_hierarchy_issues(cbind.cluster)


def add_service_to_cluster(cluster: Cluster, proto: Prototype) -> ClusterObject:
    if proto.type != "service":
        raise_adcm_ex(code="OBJ_TYPE_ERROR", msg=f"Prototype type should be service, not {proto.type}")

    check_license(prototype=proto)
    if not proto.shared and cluster.prototype.bundle != proto.bundle:
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

    reset_hc_map()
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
        raise AdcmEx("LICENSE_ERROR")

    with reraise_file_errors_as_adcm_ex(filepath=proto.license_path, reference="license file"):
        return (settings.BUNDLE_DIR / proto.bundle.hash / proto.license_path).read_text(encoding="utf-8")


def accept_license(proto: Prototype) -> None:
    if not proto.license_path:
        raise_adcm_ex("LICENSE_ERROR", "This bundle has no license")

    if proto.license == "absent":
        raise_adcm_ex("LICENSE_ERROR", "This bundle has no license")

    Prototype.objects.filter(license_hash=proto.license_hash, license="unaccepted").update(license="accepted")


def update_obj_config(obj_conf: ObjectConfig, config: dict, attr: dict, description: str = "") -> ConfigLog:
    if not isinstance(config, dict) or not isinstance(attr, dict):
        message = f"Both `config` and `attr` should be of `dict` type, not {type(config)} and {type(attr)} respectively"
        raise TypeError(message)

    obj: MainObject | ADCM | GroupConfig = obj_conf.object
    if obj is None:
        message = "Can't update configuration that have no linked object"
        raise ValueError(message)

    group = None
    if isinstance(obj, GroupConfig):
        group = obj
        obj: MainObject = group.object
        proto = obj.prototype
    else:
        proto = obj.prototype

    old_conf = ConfigLog.objects.get(obj_ref=obj_conf, id=obj_conf.current)
    new_conf = process_json_config(
        prototype=proto,
        obj=group or obj,
        new_config=config,
        new_attr=attr,
        current_attr=old_conf.attr,
    )

    with atomic():
        config_log = save_object_config(object_config=obj_conf, config=new_conf, attr=attr, description=description)
        update_hierarchy_issues(obj=obj)
        # flag on ADCM can't be raised (only objects of `ADCMCoreType` are supported)
        if not isinstance(obj, ADCM):
            raise_outdated_config_flag_if_required(object_=obj)
        apply_policy_for_new_config(config_object=obj, config_log=config_log)

    send_config_creation_event(object_=obj)

    return config_log


def raise_outdated_config_flag_if_required(object_: MainObject):
    if object_.state == "created" or not object_.prototype.flag_autogeneration.get("enable_outdated_config", False):
        return

    flag = BuiltInFlag.ADCM_OUTDATED_CONFIG.value
    flag_exists = object_.concerns.filter(name=flag.name, type=ConcernType.FLAG).exists()
    # raise unconditionally here, because message should be from "default" flag
    raise_flag(flag=flag, on_objects=[CoreObjectDescriptor(id=object_.id, type=orm_object_to_core_type(object_))])
    if not flag_exists:
        update_hierarchy(
            concern=ConcernItem.objects.get(
                name=flag.name, type=ConcernType.FLAG, owner_id=object_.id, owner_type=object_.content_type
            )
        )


def set_object_config_with_plugin(obj: ADCMEntity, config: dict, attr: dict) -> ConfigLog:
    new_conf = process_json_config(prototype=obj.prototype, obj=obj, new_config=config, new_attr=attr)

    with atomic():
        config_log = save_object_config(
            object_config=obj.config, config=new_conf, attr=attr, description="ansible update"
        )
        update_hierarchy_issues(obj=obj)
        apply_policy_for_new_config(config_object=obj, config_log=config_log)

    return config_log


def get_hc(cluster: Cluster | None) -> list[dict] | None:
    if not cluster:
        return None

    return list(HostComponent.objects.values("host_id", "service_id", "component_id").filter(cluster=cluster))


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
    hc_queryset = HostComponent.objects.filter(cluster=cluster).order_by("id")
    service_set = {hc.service for hc in hc_queryset.select_related("service")}
    old_hosts = {i.host for i in hc_queryset.select_related("host")}
    new_hosts = {i[1] for i in host_comp_list}

    previous_topology = next(retrieve_clusters_topology(cluster_ids=(cluster.id,)))

    lock = get_lock_on_object(object_=cluster)
    if lock:
        for removed_host in old_hosts.difference(new_hosts):
            remove_concern_from_object(object_=removed_host, concern=lock)

        for added_host in new_hosts.difference(old_hosts):
            add_concern_to_object(object_=added_host, concern=lock)

    hc_queryset.delete()
    host_component_list = []

    for service, host, comp in host_comp_list:
        host_component = HostComponent(
            cluster=cluster,
            service=service,
            host=host,
            component=comp,
        )
        host_component.save()
        host_component_list.append(host_component)

    updated_topology = next(retrieve_clusters_topology(cluster_ids=(cluster.id,)))
    unmapped_hosts = find_hosts_difference(new_topology=updated_topology, old_topology=previous_topology).unmapped
    ActionHostGroupRepo().remove_unmapped_hosts_from_groups(unmapped_hosts)
    ConfigHostGroupRepo().remove_unmapped_hosts_from_groups(unmapped_hosts)

    update_hierarchy_issues(cluster)

    for provider in {host.provider for host in Host.objects.filter(cluster=cluster)}:
        update_hierarchy_issues(provider)

    update_issues_and_flags_after_deleting()
    reset_hc_map()
    reset_objects_in_mm()

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

    send_host_component_map_update_event(cluster=cluster)
    return host_component_list


def add_hc(cluster: Cluster, hc_in: list[dict]) -> list[HostComponent]:
    host_comp_list = check_hc(cluster=cluster, hc_in=hc_in)

    with atomic():
        return save_hc(cluster=cluster, host_comp_list=host_comp_list)


def get_bind(
    cluster: Cluster, service: ClusterObject | None, source_cluster: Cluster, source_service: ClusterObject | None
):
    try:
        return ClusterBind.objects.get(
            cluster=cluster,
            service=service,
            source_cluster=source_cluster,
            source_service=source_service,
        )
    except ClusterBind.DoesNotExist:
        return None


def get_export(cluster: Cluster, service: ClusterObject | None, proto_import: PrototypeImport):
    exports = []
    export_proto = {}
    for prototype_export in PrototypeExport.objects.filter(prototype__name=proto_import.name):
        # Merge all export groups of prototype to one export
        if export_proto.get(prototype_export.prototype.pk):
            continue

        export_proto[prototype_export.prototype.pk] = True
        if not is_version_suitable(version=prototype_export.prototype.version, prototype_import=proto_import):
            continue

        if prototype_export.prototype.type == "cluster":
            for export_cls in Cluster.objects.filter(prototype=prototype_export.prototype):
                bound = get_bind(cluster=cluster, service=service, source_cluster=export_cls, source_service=None)
                exports.append(
                    {
                        "obj_name": export_cls.name,
                        "bundle_name": export_cls.prototype.display_name,
                        "bundle_version": export_cls.prototype.version,
                        "id": {"cluster_id": export_cls.pk},
                        "binded": bool(bound),
                        "bind_id": getattr(bound, "id", None),
                    },
                )
        elif prototype_export.prototype.type == "service":
            for export_service in ClusterObject.objects.filter(prototype=prototype_export.prototype):
                bound = get_bind(
                    cluster=cluster,
                    service=service,
                    source_cluster=export_service.cluster,
                    source_service=export_service,
                )
                exports.append(
                    {
                        "obj_name": export_service.cluster.name + "/" + export_service.prototype.display_name,
                        "bundle_name": export_service.prototype.display_name,
                        "bundle_version": export_service.prototype.version,
                        "id": {"cluster_id": export_service.cluster.pk, "service_id": export_service.pk},
                        "binded": bool(bound),
                        "bind_id": getattr(bound, "id", None),
                    },
                )
        else:
            raise_adcm_ex("BIND_ERROR", f"unexpected export type: {prototype_export.prototype.type}")

    return exports


def get_import(cluster: Cluster, service: ClusterObject | None = None):
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


def check_bind_post(bind_list: list) -> None:
    if not isinstance(bind_list, list):
        raise_adcm_ex(code="BIND_ERROR", msg="bind should be an array")

    for bind_item in bind_list:
        if not isinstance(bind_item, dict):
            raise_adcm_ex(code="BIND_ERROR", msg="bind item should be a map")

        if "import_id" not in bind_item:
            raise_adcm_ex(code="BIND_ERROR", msg='bind item does not have required "import_id" key')

        if not isinstance(bind_item["import_id"], int):
            raise_adcm_ex(code="BIND_ERROR", msg='bind item "import_id" value should be integer')

        if "export_id" not in bind_item:
            raise_adcm_ex(code="BIND_ERROR", msg='bind item does not have required "export_id" key')

        if not isinstance(bind_item["export_id"], dict):
            raise_adcm_ex(code="BIND_ERROR", msg='bind item "export_id" value should be a map')

        if "cluster_id" not in bind_item["export_id"]:
            raise_adcm_ex(code="BIND_ERROR", msg='bind item export_id does not have required "cluster_id" key')

        if not isinstance(bind_item["export_id"]["cluster_id"], int):
            raise_adcm_ex(code="BIND_ERROR", msg='bind item export_id "cluster_id" value should be integer')


def check_import_default(import_obj: Cluster | ClusterObject, export_obj: Cluster | ClusterObject):
    prototype_import = PrototypeImport.objects.get(prototype=import_obj.prototype, name=export_obj.prototype.name)
    if not prototype_import.default:
        return

    config_log = ConfigLog.objects.get(obj_ref=import_obj.config, pk=import_obj.config.current)
    if not config_log.attr:
        return

    for name in json.loads(prototype_import.default):
        if name in config_log.attr and "active" in config_log.attr[name] and not config_log.attr[name]["active"]:
            raise_adcm_ex("BIND_ERROR", f'Default import "{name}" for {obj_ref(import_obj)} is inactive')


def get_bind_obj(cluster: Cluster, service: ClusterObject | None) -> Cluster | ClusterObject:
    obj = cluster
    if service:
        obj = service

    return obj


def cook_key(cluster: Cluster, service: ClusterObject | None) -> str:
    if service:
        return f"{cluster.pk}.{service.pk}"

    return str(cluster.pk)


def get_export_service(bound: dict, export_cluster: Cluster) -> ClusterObject | None:
    export_co = None
    if "service_id" in bound["export_id"]:
        export_co = ClusterObject.obj.get(id=bound["export_id"]["service_id"])
        if export_co.cluster != export_cluster:
            raise_adcm_ex(
                "BIND_ERROR",
                f"export {obj_ref(obj=export_co)} is not belong to {obj_ref(obj=export_cluster)}",
            )

    return export_co


def get_prototype_import(import_pk: int, import_obj: Cluster | ClusterObject) -> PrototypeImport:
    proto_import = PrototypeImport.obj.get(id=import_pk)
    if proto_import.prototype != import_obj.prototype:
        raise_adcm_ex("BIND_ERROR", f"Import #{import_pk} does not belong to {obj_ref(obj=import_obj)}")

    return proto_import


class DataForMultiBind(TypedDict):
    import_id: int
    export_id: dict[Literal["cluster_id", "service_id"], int]


def multi_bind(cluster: Cluster, service: ClusterObject | None, bind_list: list[DataForMultiBind]):
    check_bind_post(bind_list=bind_list)
    import_obj = get_bind_obj(cluster=cluster, service=service)
    old_bind = {}
    cluster_bind_list = ClusterBind.objects.filter(cluster=cluster, service=service)
    for cluster_bind in cluster_bind_list:
        old_bind[cook_key(cluster=cluster_bind.source_cluster, service=cluster_bind.source_service)] = cluster_bind

    new_bind = {}
    for bind_item in bind_list:
        prototype_import = get_prototype_import(import_pk=bind_item["import_id"], import_obj=import_obj)
        export_cluster = Cluster.obj.get(id=bind_item["export_id"]["cluster_id"])
        export_obj = export_cluster
        export_co = get_export_service(bound=bind_item, export_cluster=export_cluster)
        if export_co:
            export_obj = export_co

        if cook_key(cluster=export_cluster, service=export_co) in new_bind:
            raise_adcm_ex("BIND_ERROR", "Bind list has duplicates")

        if prototype_import.name != export_obj.prototype.name:
            raise_adcm_ex(
                "BIND_ERROR",
                f'Export {obj_ref(obj=export_obj)} does not match import name "{prototype_import.name}"',
            )

        if not is_version_suitable(version=export_obj.prototype.version, prototype_import=prototype_import):
            raise_adcm_ex(
                "BIND_ERROR",
                f'Import "{export_obj.prototype.name}" of { proto_ref(prototype=prototype_import.prototype)} '
                f"versions ({prototype_import.min_version}, {prototype_import.max_version}) does not match export "
                f"version: {export_obj.prototype.version} ({obj_ref(obj=export_obj)})",
            )

        cluster_bind = ClusterBind(
            cluster=cluster,
            service=service,
            source_cluster=export_cluster,
            source_service=export_co,
        )
        new_bind[cook_key(cluster=export_cluster, service=export_co)] = prototype_import, cluster_bind, export_obj

    for key, value in old_bind.items():
        if key in new_bind:
            continue

        export_obj = get_bind_obj(cluster=value.source_cluster, service=value.source_service)
        check_import_default(import_obj=import_obj, export_obj=export_obj)
        value.delete()
        logger.info("unbind %s from %s", obj_ref(export_obj), obj_ref(obj=import_obj))

    for key, value in new_bind.items():
        if key in old_bind:
            continue

        prototype_import, cluster_bind, export_obj = value
        check_multi_bind(
            actual_import=prototype_import,
            cluster=cluster,
            service=service,
            export_cluster=cluster_bind.source_cluster,
            export_service=cluster_bind.source_service,
        )
        cluster_bind.save()
        logger.info("bind %s to %s", obj_ref(obj=export_obj), obj_ref(obj=import_obj))

        update_hierarchy_issues(obj=cluster)

    return get_import(cluster=cluster, service=service)


def bind(
    cluster: Cluster, service: ClusterObject | None, export_cluster: Cluster, export_service_pk: int | None
) -> dict:
    """
    Adapter between old and new bind interface
    /api/.../bind/ -> /api/.../import/
    bind() -> multi_bind()
    """

    export_service = None
    if export_service_pk:
        export_service = ClusterObject.obj.get(cluster=export_cluster, id=export_service_pk)
        if not PrototypeExport.objects.filter(prototype=export_service.prototype):
            raise_adcm_ex(code="BIND_ERROR", msg=f"{obj_ref(export_service)} do not have exports")

        name = export_service.prototype.name
    else:
        if not PrototypeExport.objects.filter(prototype=export_cluster.prototype):
            raise_adcm_ex(code="BIND_ERROR", msg=f"{obj_ref(export_cluster)} does not have exports")

        name = export_cluster.prototype.name

    import_obj = cluster
    if service:
        import_obj = service

    prototype_import = None
    try:
        prototype_import = PrototypeImport.obj.get(prototype=import_obj.prototype, name=name)
    except MultipleObjectsReturned:
        raise_adcm_ex(code="BIND_ERROR", msg="Old api does not support multi bind. Go to /api/v1/.../import/")

    bind_list = []
    for imp in get_import(cluster=cluster, service=service):
        for exp in imp["exports"]:
            if exp["binded"]:
                bind_list.append({"import_id": imp["id"], "export_id": exp["id"]})

    item = {"import_id": prototype_import.id, "export_id": {"cluster_id": export_cluster.pk}}
    if export_service:
        item["export_id"]["service_id"] = export_service.pk

    bind_list.append(item)

    multi_bind(cluster=cluster, service=service, bind_list=bind_list)
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
        if host.cluster.pk == cluster.pk:
            raise AdcmEx(code="HOST_CONFLICT", msg="The host is already associated with this cluster.")

        raise AdcmEx(code="FOREIGN_HOST", msg="Host already linked to another cluster.")

    with atomic():
        host.cluster = cluster
        host.save(update_fields=["cluster"])

        update_hierarchy_issues(host)
        update_hierarchy_issues(cluster)
        re_apply_object_policy(cluster)

    reset_hc_map()
    logger.info("host #%s %s is added to cluster #%s %s", host.pk, host.fqdn, cluster.pk, cluster.name)

    return host
