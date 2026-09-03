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

from core.action.job import JobService
from core.action.job.errors import JobOperationError
from core.cluster import ClusterService
from core.types import ADCMCoreType, ConcernID, CoreObjectDescriptor
from core.versions import is_version_suitable
from django.db.transaction import atomic, on_commit
from rbac.scenarios import RBACScenarios
import core

from cm.converters import orm_object_to_core_type
from cm.errors import AdcmEx, raise_adcm_ex
from cm.legacy.issue import (
    unlink_concern_from_object,
)
from cm.legacy.services.concern import create_issue, delete_concerns_of_removed_objects, delete_issue, retrieve_issue
from cm.legacy.services.concern.checks import (
    cluster_mapping_has_issue_orm_version,
    object_configuration_has_issue,
    object_imports_has_issue,
)
from cm.legacy.services.concern.distribution import (
    ConcernRelatedObjects,
    distribute_concern_on_related_objects,
)
from cm.legacy.services.concern.flags import BuiltInFlag, raise_flag
from cm.legacy.services.concern.locks import get_lock_on_object
from cm.legacy.services.status.notify import reset_hc_map, reset_objects_in_mm
from cm.legacy.status_api import (
    notify_about_new_concern,
)
from cm.legacy.utils import obj_ref
from cm.logger import logger
from cm.models import (
    ActionHostGroup,
    ADCMEntity,
    Cluster,
    ClusterBind,
    Component,
    ConcernCause,
    ConcernItem,
    ConcernType,
    ConfigLog,
    Host,
    HostComponent,
    MainObject,
    MaintenanceMode,
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


def proto_ref(prototype: Prototype) -> str:
    return f'{prototype.type} "{prototype.name}" {prototype.version}'


def check_license(prototype: Prototype) -> None:
    if prototype.license == "unaccepted":
        raise_adcm_ex(
            "LICENSE_ERROR",
            f'License for prototype "{prototype.name}" {prototype.type} {prototype.version} is not accepted',
        )


def add_host_provider(
    prototype: Prototype, name: str, config_service: core.config.ConfigService, description: str = ""
):
    if prototype.type != "provider":
        raise_adcm_ex("OBJ_TYPE_ERROR", f"Prototype type should be provider, not {prototype.type}")

    check_license(prototype)
    with atomic():
        provider = Provider.objects.create(prototype=prototype, name=name, description=description)
        provider_cod = CoreObjectDescriptor(id=provider.id, type=ADCMCoreType.PROVIDER)
        config_service.create_initial_configuration_if_required(owner=provider_cod)

        concern_id = None
        if object_configuration_has_issue(provider, config_service=config_service):
            concern = create_issue(owner=provider_cod, cause=ConcernCause.CONFIG)
            concern_id = concern.id
            related_objects = distribute_concern_on_related_objects(owner=provider_cod, concern_id=concern_id)

    if concern_id:
        notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

    logger.info("host provider #%s %s is added", provider.pk, provider.name)

    return provider


def cancel_locking_tasks(obj: ADCMEntity, job_service: JobService, obj_deletion=False):
    for lock in obj.concerns.filter(type=ConcernType.LOCK, owner_type=obj.content_type, owner_id=obj.id):
        for task in TaskLog.objects.filter(lock=lock):
            _terminate_task(task_id=task.pk, job_service=job_service, obj_deletion=obj_deletion)


def _terminate_task(task_id: int, job_service: JobService, obj_deletion: bool) -> None:
    try:
        job_service.terminate_task(task_id=task_id, force_allow_termination=obj_deletion)
    except JobOperationError as e:
        raise AdcmEx("NOT_ALLOWED_TERMINATION", e.message) from None


def delete_host_provider(provider, job_service: JobService, cancel_tasks=True):
    hosts = Host.objects.filter(provider=provider)
    if hosts:
        raise_adcm_ex(
            "PROVIDER_CONFLICT",
            f'There is host #{hosts[0].pk} "{hosts[0].fqdn}" of host {obj_ref(provider)}',
        )

    if cancel_tasks:
        cancel_locking_tasks(provider, job_service=job_service, obj_deletion=True)

    provider.delete()
    logger.info("host provider #%s is deleted", provider.pk)


def delete_host(
    host: Host, cluster_service: ClusterService, job_service: JobService, cancel_tasks: bool = True
) -> None:
    cluster = host.cluster
    if cluster:
        raise AdcmEx(code="HOST_CONFLICT", msg="Unable to remove a host associated with a cluster.")

    if host.duplicates.filter(cluster__isnull=False).exists():
        raise AdcmEx(
            code="HOST_CONFLICT",
            msg="It is forbidden to delete a host if at least one duplicate is associated with the cluster.",
        )

    if cancel_tasks:
        cancel_locking_tasks(obj=host, job_service=job_service, obj_deletion=True)

    host_pk = host.pk
    host.delete()
    reset_hc_map()
    reset_objects_in_mm(cluster_service=cluster_service)

    logger.info("host #%s is deleted", host_pk)


def delete_cluster(cluster: Cluster, cluster_service: ClusterService, job_service: JobService) -> None:
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
        _terminate_task(task_id=task.pk, job_service=job_service, obj_deletion=True)


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
        if not is_version_suitable(version=prototype_export.prototype.version, versions_object=proto_import):
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

        if not is_version_suitable(version=export_obj.prototype.version, versions_object=prototype_import):
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


def are_configlogs_equal(old: ConfigLog, new: ConfigLog) -> bool:
    return old.config == new.config and old.attr == new.attr
