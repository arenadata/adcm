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

from functools import partial
from typing import Literal, TypedDict
import json

from adcm_version import compare_prototype_versions
from core.cluster import ClusterService
from core.types import ADCMCoreType, ConcernID, CoreObjectDescriptor
from django.contrib.contenttypes.models import ContentType
from django.db.transaction import atomic, on_commit
from rbac.roles import apply_policy_for_new_config
from rbac.scenarios import RBACScenarios

from cm.converters import (
    CoreObject,
    orm_object_to_action_target_type,
    orm_object_to_core_descriptor,
    orm_object_to_core_type,
)
from cm.errors import AdcmEx, raise_adcm_ex
from cm.legacy.adcm_config.config import (
    process_json_config,
    save_object_config,
)
from cm.legacy.adcm_config.utils import proto_ref
from cm.legacy.config import init_object_config
from cm.legacy.issue import (
    add_concern_to_object,
    unlink_concern_from_object,
    update_hierarchy_issues,
)
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.concern import create_issue, delete_concerns_of_removed_objects, delete_issue, retrieve_issue
from cm.legacy.services.concern.cases import (
    recalculate_own_concerns_on_add_clusters,
    recalculate_own_concerns_on_add_hosts,
    recalculate_own_concerns_on_add_services,
)
from cm.legacy.services.concern.checks import (
    cluster_mapping_has_issue_orm_version,
    object_configuration_has_issue,
    object_imports_has_issue,
)
from cm.legacy.services.concern.distribution import (
    ConcernRelatedObjects,
    distribute_concern_on_related_objects,
    redistribute_issues_and_flags,
)
from cm.legacy.services.concern.flags import BuiltInFlag, raise_flag
from cm.legacy.services.concern.locks import get_lock_on_object
from cm.legacy.services.job.run import update_related_configs
from cm.legacy.services.status.notify import reset_hc_map, reset_objects_in_mm
from cm.legacy.status_api import (
    notify_about_new_concern,
    notify_about_redistributed_concerns_from_maps,
    send_config_creation_event,
)
from cm.legacy.utils import obj_ref
from cm.logger import logger
from cm.models import (
    ADCM,
    ActionHostGroup,
    ADCMEntity,
    AnsibleConfig,
    Cluster,
    ClusterBind,
    Component,
    ConcernCause,
    ConcernItem,
    ConcernType,
    ConfigHostGroup,
    ConfigLog,
    Host,
    HostComponent,
    MainObject,
    MaintenanceMode,
    ObjectConfig,
    Prototype,
    PrototypeExport,
    PrototypeImport,
    Provider,
    Service,
    TaskLog,
)

# There's no good place to place it for now.
# Since it's more about API than `cm.legacy.services.job`, it'll live here.
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

        added, removed = {}, {}
        if recalculate_own_concerns_on_add_clusters(cluster):
            added, removed = redistribute_issues_and_flags(topology=retrieve_cluster_topology(cluster.pk))

    reset_hc_map()
    notify_about_redistributed_concerns_from_maps(added=added, removed=removed)

    logger.info("cluster #%s %s is added", cluster.pk, cluster.name)

    return cluster


def add_host(
    prototype: Prototype,
    provider: Provider,
    fqdn: str,
    rbac_scenarios: RBACScenarios,
    description: str = "",
):
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

        related_objects = {}
        concern_id = None
        if concerns := recalculate_own_concerns_on_add_hosts(host):
            concern_id = next(iter(concerns[ADCMCoreType.HOST][host.id]))
            related_objects = distribute_concern_on_related_objects(
                owner=CoreObjectDescriptor(id=host.id, type=ADCMCoreType.HOST), concern_id=concern_id
            )
        if concern := retrieve_issue(
            owner=CoreObjectDescriptor(id=provider.id, type=ADCMCoreType.PROVIDER), cause=ConcernCause.CONFIG
        ):
            host.concerns.add(concern)

        rbac_scenarios.re_apply_object_policy(apply_object=provider)

    reset_hc_map()

    if concern_id:
        notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

    logger.info("host #%s %s is added", host.pk, host.fqdn)

    return host


def add_host_provider(prototype: Prototype, name: str, description: str = ""):
    if prototype.type != "provider":
        raise_adcm_ex("OBJ_TYPE_ERROR", f"Prototype type should be provider, not {prototype.type}")

    check_license(prototype)
    with atomic():
        provider = Provider.objects.create(prototype=prototype, name=name, description=description)
        obj_conf = init_object_config(prototype, provider)
        provider.config = obj_conf
        provider.save()

        provider_cod = CoreObjectDescriptor(id=provider.id, type=ADCMCoreType.PROVIDER)
        concern_id = None
        if object_configuration_has_issue(provider):
            concern = create_issue(owner=provider_cod, cause=ConcernCause.CONFIG)
            concern_id = concern.id
            related_objects = distribute_concern_on_related_objects(owner=provider_cod, concern_id=concern_id)

    if concern_id:
        notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

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


def delete_host(host: Host, cluster_service: ClusterService, cancel_tasks: bool = True) -> None:
    cluster = host.cluster
    if cluster:
        raise AdcmEx(code="HOST_CONFLICT", msg="Unable to remove a host associated with a cluster.")

    if host.duplicates.filter(cluster__isnull=False).exists():
        raise AdcmEx(
            code="HOST_CONFLICT",
            msg="It is forbidden to delete a host if at least one duplicate is associated with the cluster.",
        )

    if cancel_tasks:
        cancel_locking_tasks(obj=host, obj_deletion=True)

    host_pk = host.pk
    host.delete()
    reset_hc_map()
    reset_objects_in_mm(cluster_service=cluster_service)

    logger.info("host #%s is deleted", host_pk)


def delete_cluster(cluster: Cluster, cluster_service: ClusterService) -> None:
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

    delete_concerns_of_removed_objects(
        objects={
            ADCMCoreType.CLUSTER: (cluster.id,),
            ADCMCoreType.SERVICE: tuple(Service.objects.values_list("id", flat=True).filter(cluster_id=cluster.id)),
            ADCMCoreType.COMPONENT: tuple(Component.objects.values_list("id", flat=True).filter(cluster_id=cluster.id)),
        }
    )

    cluster.delete()

    reset_hc_map()
    reset_objects_in_mm(cluster_service=cluster_service)

    for task in tasks:
        task.cancel(obj_deletion=True)


def remove_host_from_cluster(host: Host, cluster_service: ClusterService, rbac_scenarios: RBACScenarios) -> Host:
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

        for group in cluster.config_host_group.order_by("id"):
            group.hosts.remove(host)

        # if there's no lock on cluster, nothing should be removed
        unlink_concern_from_object(object_=host, concern=get_lock_on_object(object_=cluster))

        if not cluster_mapping_has_issue_orm_version(cluster):
            delete_issue(
                owner=CoreObjectDescriptor(id=cluster.id, type=ADCMCoreType.CLUSTER), cause=ConcernCause.HOSTCOMPONENT
            )

        rbac_scenarios.re_apply_object_policy(apply_object=cluster)

    reset_hc_map()
    reset_objects_in_mm(cluster_service=cluster_service)

    return host


def add_service_to_cluster(cluster: Cluster, proto: Prototype, rbac_scenarios: RBACScenarios) -> Service:
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
        service = Service.objects.create(cluster=cluster, prototype=proto)
        obj_conf = init_object_config(proto=proto, obj=service)
        service.config = obj_conf
        service.save(update_fields=["config"])
        add_components_to_service(cluster=cluster, service=service)

        recalculate_own_concerns_on_add_services(cluster=cluster, services=(service,))
        added, removed = redistribute_issues_and_flags(retrieve_cluster_topology(cluster.id))

        rbac_scenarios.re_apply_object_policy(apply_object=cluster)

    reset_hc_map()
    notify_about_redistributed_concerns_from_maps(added=added, removed=removed)
    logger.info(
        "service #%s %s is added to cluster #%s %s",
        service.pk,
        service.prototype.name,
        cluster.pk,
        cluster.name,
    )

    return service


def add_components_to_service(cluster: Cluster, service: Service) -> None:
    for comp in Prototype.objects.filter(type="component", parent=service.prototype):
        service_component = Component.objects.create(cluster=cluster, service=service, prototype=comp)
        obj_conf = init_object_config(proto=comp, obj=service_component)
        service_component.config = obj_conf
        service_component.save(update_fields=["config"])


def update_obj_config(obj_conf: ObjectConfig, config: dict, attr: dict, description: str = "") -> ConfigLog:
    if not isinstance(config, dict) or not isinstance(attr, dict):
        message = f"Both `config` and `attr` should be of `dict` type, not {type(config)} and {type(attr)} respectively"
        raise TypeError(message)

    obj = obj_conf.object
    if obj is None:
        message = "Can't update configuration that have no linked object"
        raise ValueError(message)

    group = None
    if isinstance(obj, ConfigHostGroup):
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

    concern_id, related_objects = None, {}

    with atomic():
        config_log = save_object_config(object_config=obj_conf, config=new_conf, attr=attr, description=description)

        delete_issue(
            owner=CoreObjectDescriptor(id=obj.id, type=orm_object_to_action_target_type(object_=obj)),
            cause=ConcernCause.CONFIG,
        )
        # flag on ADCM can't be raised (only objects of `ADCMCoreType` are supported)
        if not isinstance(obj, ADCM) and not are_configlogs_equal(old_conf, config_log):
            concern_id, related_objects = raise_outdated_config_flag_if_required(object_=obj)
        apply_policy_for_new_config(config_object=obj, config_log=config_log)

    send_config_creation_event(
        object_id=obj.id, object_type=obj.prototype.type, changes={"createdBy": config_log.created_by}
    )
    if concern_id:
        notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

    return config_log


def raise_outdated_config_flag_if_required(object_: MainObject) -> tuple[ConcernID | None, ConcernRelatedObjects]:
    if object_.state == "created" or not object_.prototype.flag_autogeneration.get("enable_outdated_config", False):
        return None, {}

    flag = BuiltInFlag.ADCM_OUTDATED_CONFIG.value
    flag_exists = object_.concerns.filter(
        name=flag.name, type=ConcernType.FLAG, owner_id=object_.id, owner_type=object_.content_type
    ).exists()
    # raise unconditionally here, because message should be from "default" flag
    owner = CoreObjectDescriptor(id=object_.id, type=orm_object_to_core_type(object_))
    raise_flag(flag=flag, on_objects=[owner])
    if not flag_exists:
        concern_id = ConcernItem.objects.values_list("id", flat=True).get(
            name=flag.name, type=ConcernType.FLAG, owner_id=object_.id, owner_type=object_.content_type
        )
        return concern_id, distribute_concern_on_related_objects(owner=owner, concern_id=concern_id)

    return None, {}


def set_object_config_with_plugin(
    job_id: int, obj: ADCM | CoreObject, config: dict, attr: dict, description: str
) -> None:
    old_config_log_id = obj.config.current
    new_conf = process_json_config(prototype=obj.prototype, obj=obj, new_config=config, new_attr=attr)

    with atomic():
        config_log = save_object_config(object_config=obj.config, config=new_conf, attr=attr, description=description)
        apply_policy_for_new_config(config_object=obj, config_log=config_log)

    core_object = orm_object_to_core_descriptor(object_=obj)
    update_related_configs(
        job_id=job_id,
        object_=core_object,
        object_prototype_id=obj.prototype_id,
        old_config_id=old_config_log_id,
        new_config_id=config_log.id,
    )
    send_config_creation_event(
        object_id=obj.id, object_type=obj.prototype.type, changes={"createdBy": config_log.created_by}
    )


def get_hc(cluster: Cluster | None) -> list[dict] | None:
    if not cluster:
        return None

    return list(HostComponent.objects.values("host_id", "service_id", "component_id").filter(cluster=cluster))


def get_bind(cluster: Cluster, service: Service | None, source_cluster: Cluster, source_service: Service | None):
    try:
        return ClusterBind.objects.get(
            cluster=cluster,
            service=service,
            source_cluster=source_cluster,
            source_service=source_service,
        )
    except ClusterBind.DoesNotExist:
        return None


def get_export(cluster: Cluster, service: Service | None, proto_import: PrototypeImport):
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
            for export_service in Service.objects.filter(prototype=prototype_export.prototype):
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


def get_import(cluster: Cluster, service: Service | None = None):
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


def check_import_default(import_obj: Cluster | Service, export_obj: Cluster | Service):
    prototype_import = PrototypeImport.objects.get(prototype=import_obj.prototype, name=export_obj.prototype.name)
    if not prototype_import.default:
        return

    config_log = ConfigLog.objects.get(obj_ref=import_obj.config, pk=import_obj.config.current)
    if not config_log.attr:
        return

    for name in json.loads(prototype_import.default):
        if name in config_log.attr and "active" in config_log.attr[name] and not config_log.attr[name]["active"]:
            raise_adcm_ex("BIND_ERROR", f'Default import "{name}" for {obj_ref(import_obj)} is inactive')


def get_bind_obj(cluster: Cluster, service: Service | None) -> Cluster | Service:
    obj = cluster
    if service:
        obj = service

    return obj


def cook_key(cluster: Cluster, service: Service | None) -> str:
    if service:
        return f"{cluster.pk}.{service.pk}"

    return str(cluster.pk)


def get_export_service(bound: dict, export_cluster: Cluster) -> Service | None:
    export_co = None
    if "service_id" in bound["export_id"]:
        export_co = Service.obj.get(id=bound["export_id"]["service_id"])
        if export_co.cluster != export_cluster:
            raise_adcm_ex(
                "BIND_ERROR",
                f"export {obj_ref(obj=export_co)} is not belong to {obj_ref(obj=export_cluster)}",
            )

    return export_co


def get_prototype_import(import_pk: int, import_obj: Cluster | Service) -> PrototypeImport:
    proto_import = PrototypeImport.obj.get(id=import_pk)
    if proto_import.prototype != import_obj.prototype:
        raise_adcm_ex("BIND_ERROR", f"Import #{import_pk} does not belong to {obj_ref(obj=import_obj)}")

    return proto_import


class DataForMultiBind(TypedDict):
    import_id: int
    export_id: dict[Literal["cluster_id", "service_id"], int]


def multi_bind(cluster: Cluster, service: Service | None, bind_list: list[DataForMultiBind]):
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

    import_target = CoreObjectDescriptor(id=import_obj.id, type=orm_object_to_core_type(import_obj))
    if not object_imports_has_issue(target=import_obj):
        delete_issue(owner=import_target, cause=ConcernCause.IMPORT)
    elif retrieve_issue(owner=import_target, cause=ConcernCause.IMPORT) is None:
        concern = create_issue(owner=import_target, cause=ConcernCause.IMPORT)
        related_objects = distribute_concern_on_related_objects(owner=import_target, concern_id=concern.id)
        on_commit(func=partial(notify_about_new_concern, concern_id=concern.id, related_objects=related_objects))

    return get_import(cluster=cluster, service=service)


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


def add_host_to_cluster(cluster: Cluster, host: Host, rbac_scenarios: RBACScenarios) -> Host:
    if host.cluster:
        if host.cluster.pk == cluster.pk:
            raise AdcmEx(code="HOST_CONFLICT", msg="The host is already associated with this cluster.")

        raise AdcmEx(code="FOREIGN_HOST", msg="Host already linked to another cluster.")

    with atomic():
        host.cluster = cluster
        host.save(update_fields=["cluster"])

        update_hierarchy_issues(host)
        update_hierarchy_issues(cluster)
        rbac_scenarios.re_apply_object_policy(apply_object=cluster)

    reset_hc_map()
    logger.info("host #%s %s is added to cluster #%s %s", host.pk, host.fqdn, cluster.pk, cluster.name)

    return host


def are_configlogs_equal(old: ConfigLog, new: ConfigLog) -> bool:
    return old.config == new.config and old.attr == new.attr
