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
from typing import Iterable

from api_v2.concern.serializers import ConcernSerializer
from django.conf import settings
from django.db.transaction import on_commit
from djangorestframework_camel_case.util import camelize

from cm.adcm_config.config import get_prototype_config
from cm.adcm_config.utils import proto_ref
from cm.data_containers import PrototypeData
from cm.errors import AdcmEx
from cm.hierarchy import Tree
from cm.logger import logger
from cm.models import (
    ADCMEntity,
    Bundle,
    Cluster,
    ClusterBind,
    ClusterObject,
    ConcernCause,
    ConcernItem,
    ConcernType,
    ConfigLog,
    Host,
    HostComponent,
    JobLog,
    ObjectType,
    Prototype,
    PrototypeImport,
    ServiceComponent,
    TaskLog,
)
from cm.services.concern.messages import ConcernMessage, PlaceholderObjectsDTO, build_concern_reason
from cm.status_api import send_concern_creation_event, send_concern_delete_event
from cm.utils import obj_ref


def check_config(obj: ADCMEntity) -> bool:
    spec, _, _, _ = get_prototype_config(prototype=obj.prototype)
    conf, attr = get_obj_config(obj=obj)
    for key, value in spec.items():
        if "required" in value:
            if value["required"] and key in conf and conf[key] is None:
                logger.debug("required config key %s of %s is missing", key, obj_ref(obj=obj))
                return False
        else:
            if key in attr and "active" in attr[key] and not attr[key]["active"]:
                continue
            for subkey in value:
                if value[subkey]["required"]:
                    if key not in conf:
                        logger.debug("required config group %s of %s is missing", key, obj_ref(obj=obj))
                        return False
                    if subkey in conf[key]:
                        if conf[key][subkey] is None:
                            msg = "required config value for key %s/%s of %s is missing"
                            logger.debug(msg, key, subkey, obj_ref(obj=obj))
                            return False
                    else:
                        msg = "required config key %s/%s of %s is missing"
                        logger.debug(msg, key, subkey, obj_ref(obj=obj))
                        return False
    return True


def check_required_services(cluster: Cluster) -> bool:
    bundle = cluster.prototype.bundle
    for proto in Prototype.objects.filter(bundle=bundle, type="service", required=True):
        try:
            ClusterObject.objects.get(cluster=cluster, prototype=proto)
        except ClusterObject.DoesNotExist:
            logger.debug("required service %s of %s is missing", proto_ref(prototype=proto), obj_ref(obj=cluster))
            return False
    return True


def check_required_import(obj: [Cluster, ClusterObject]) -> bool:
    if obj.prototype.type == ObjectType.CLUSTER:
        cluster = obj
        service = None
    elif obj.prototype.type == ObjectType.SERVICE:
        service = obj
        cluster = obj.cluster
    else:
        raise AdcmEx(code="ISSUE_INTEGRITY_ERROR", msg=f"Could not check import for {obj}")

    res, _ = do_check_import(cluster=cluster, service=service)
    return res


def check_service_requires(cluster: Cluster, proto: Prototype) -> None:
    if not proto.requires:
        return

    for require in proto.requires:
        req_service = ClusterObject.objects.filter(prototype__name=require["service"], cluster=cluster)
        obj_prototype = Prototype.objects.filter(name=require["service"], type="service")

        if comp_name := require.get("component"):
            req_obj = ServiceComponent.objects.filter(
                prototype__name=comp_name, service=req_service.first(), cluster=cluster
            )
            obj_prototype = Prototype.objects.filter(name=comp_name, type="component", parent=obj_prototype.first())
        else:
            req_obj = req_service

        if not req_obj.exists():
            raise AdcmEx(
                code="SERVICE_CONFLICT",
                msg=f"No required {proto_ref(prototype=obj_prototype.first())} for {proto_ref(prototype=proto)}",
            )


def check_requires(service: ClusterObject) -> bool:
    try:
        check_service_requires(cluster=service.cluster, proto=service.prototype)
    except AdcmEx:
        logger.debug("requirements not satisfied for %s", proto_ref(prototype=service.prototype))

        return False

    return True


def do_check_import(cluster: Cluster, service: ClusterObject | None = None) -> tuple[bool, str | None]:
    import_exist = (True, None)
    proto = cluster.prototype

    if service:
        proto = service.prototype

    prototype_imports = PrototypeImport.objects.filter(prototype=proto)
    if not prototype_imports.exists():
        return import_exist

    if not any(prototype_imports.values_list("required", flat=True)):
        return True, "NOT_REQUIRED"

    for prototype_import in prototype_imports.filter(required=True):
        import_exist = (False, None)
        for cluster_bind in ClusterBind.objects.filter(cluster=cluster):
            if cluster_bind.source_cluster and cluster_bind.source_cluster.prototype.name == prototype_import.name:
                import_exist = (True, "CLUSTER_IMPORTED")

            if cluster_bind.source_service and cluster_bind.source_service.prototype.name == prototype_import.name:
                import_exist = (True, "SERVICE_IMPORTED")

        if not import_exist[0]:
            break

    return import_exist


def check_hc(cluster: Cluster) -> bool:
    shc_list = []
    for hostcomponent in HostComponent.objects.filter(cluster=cluster):
        shc_list.append((hostcomponent.service, hostcomponent.host, hostcomponent.component))

    if not shc_list:
        for service in ClusterObject.objects.filter(cluster=cluster):
            for comp in Prototype.objects.filter(parent=service.prototype, type="component"):
                const = comp.constraint
                if len(const) == 2 and const[0] == 0:
                    continue
                logger.debug("void host components for %s", proto_ref(prototype=service.prototype))
                return False

    for service in ClusterObject.objects.filter(cluster=cluster):
        try:
            check_component_constraint(
                cluster=cluster, service_prototype=service.prototype, hc_in=[i for i in shc_list if i[0] == service]
            )
        except AdcmEx:
            return False

    try:
        check_hc_requires(shc_list=shc_list)
        check_bound_components(shc_list=shc_list)
    except AdcmEx:
        return False

    return True


def check_hc_requires(shc_list: list[tuple[ClusterObject, Host, ServiceComponent]]) -> None:
    for serv_host_comp in [i for i in shc_list if i[2].prototype.requires or i[0].prototype.requires]:
        for require in [*serv_host_comp[2].prototype.requires, *serv_host_comp[0].prototype.requires]:
            if require in serv_host_comp[2].prototype.requires:
                ref = f'component "{serv_host_comp[2].prototype.name}" of service "{serv_host_comp[0].prototype.name}"'
            else:
                ref = f'service "{serv_host_comp[0].prototype.name}"'

            req_comp = require.get("component")

            if not ClusterObject.objects.filter(prototype__name=require["service"]).exists() and not req_comp:
                raise AdcmEx(
                    code="COMPONENT_CONSTRAINT_ERROR", msg=f"No required service \"{require['service']}\" for {ref}"
                )

            if not req_comp:
                continue

            if not any(
                {  # noqa: C419
                    (shc[0].prototype.name == require["service"] and shc[2].prototype.name == req_comp)
                    for shc in shc_list
                }
            ):
                raise AdcmEx(
                    code="COMPONENT_CONSTRAINT_ERROR",
                    msg=f'No required component "{req_comp}" of service "{require["service"]}" for {ref}',
                )


def check_bound_components(shc_list: list[tuple[ClusterObject, Host, ServiceComponent]]) -> None:
    for shc in [i for i in shc_list if i[2].prototype.bound_to]:
        component_prototype = shc[2].prototype
        service_name = component_prototype.bound_to["service"]
        component_name = component_prototype.bound_to["component"]

        bound_targets_shc = [
            i for i in shc_list if i[0].prototype.name == service_name and i[2].prototype.name == component_name
        ]

        if not bound_targets_shc:
            bound_target_ref = f'component "{component_name}" of service "{service_name}"'
            bound_requester_ref = f'component "{shc[2].display_name}" of service "{shc[0].display_name}"'
            msg = f"{bound_target_ref.capitalize()} not in hc for {bound_requester_ref}"
            raise AdcmEx(code="COMPONENT_CONSTRAINT_ERROR", msg=msg)

        for target_shc in bound_targets_shc:
            if not [i for i in shc_list if i[1] == target_shc[1] and i[2].prototype == component_prototype]:
                bound_target_ref = f'component "{shc[2].prototype.name}" of service "{shc[0].prototype.name}"'
                bound_requester_ref = (
                    f'component "{target_shc[2].prototype.name}" of service "{target_shc[0].prototype.name}"'
                )
                msg = f'No {bound_target_ref} on host "{target_shc[1].fqdn}" for {bound_requester_ref}'
                raise AdcmEx(code="COMPONENT_CONSTRAINT_ERROR", msg=msg)


def get_obj_config(obj: ADCMEntity) -> tuple[dict, dict]:
    if obj.config is None:
        return {}, {}

    config_log = ConfigLog.obj.get(obj_ref=obj.config, id=obj.config.current)
    attr = config_log.attr
    if not attr:
        attr = {}

    return config_log.config, attr


def check_min_required_components(count: int, constraint: int, component_prototype: Prototype, ref: str) -> None:
    if count < constraint:
        raise AdcmEx(
            code="COMPONENT_CONSTRAINT_ERROR",
            msg=f'Less then {constraint} required component "{component_prototype.name}" ({count}) {ref}',
        )


def check_max_required_components(count: int, constraint: int, component_prototype: Prototype, ref: str) -> None:
    if count > constraint:
        raise AdcmEx(
            code="COMPONENT_CONSTRAINT_ERROR",
            msg=f'Amount ({count}) of component "{component_prototype.name}" more then maximum ({constraint}) {ref}',
        )


def check_components_number_is_odd(count: int, constraint: str, component_prototype: Prototype, ref: str) -> None:
    if count % 2 == 0:
        raise AdcmEx(
            code="COMPONENT_CONSTRAINT_ERROR",
            msg=f'Amount ({count}) of component "{component_prototype.name}" should be odd ({constraint}) {ref}',
        )


def check_components_mapping_contraints(
    hosts_count: int,
    target_mapping_count: int,
    service_prototype: Prototype | PrototypeData,
    component_prototype: Prototype | PrototypeData,
) -> None:
    constraint = component_prototype.constraint
    ref = f'in host component list for {service_prototype.type} "{service_prototype.name}"'

    if isinstance(constraint[0], int):
        check_min_required_components(
            count=target_mapping_count, constraint=constraint[0], component_prototype=component_prototype, ref=ref
        )
        if len(constraint) < 2:
            check_max_required_components(
                count=target_mapping_count, constraint=constraint[0], component_prototype=component_prototype, ref=ref
            )

    if len(constraint) > 1:
        if isinstance(constraint[1], int):
            check_max_required_components(
                count=target_mapping_count, constraint=constraint[1], component_prototype=component_prototype, ref=ref
            )
        elif constraint[1] == "odd" and target_mapping_count:
            check_components_number_is_odd(
                count=target_mapping_count, constraint=constraint[1], component_prototype=component_prototype, ref=ref
            )

    if constraint[0] == "+":
        check_min_required_components(
            count=target_mapping_count, constraint=hosts_count, component_prototype=component_prototype, ref=ref
        )
    elif constraint[0] == "odd":  # synonym to [1,odd]
        check_min_required_components(
            count=target_mapping_count, constraint=1, component_prototype=component_prototype, ref=ref
        )
        check_components_number_is_odd(
            count=target_mapping_count, constraint=constraint[0], component_prototype=component_prototype, ref=ref
        )


def check_component_constraint(
    cluster: Cluster, service_prototype: Prototype, hc_in: list, old_bundle: Bundle | None = None
) -> None:
    for component_prototype in Prototype.objects.filter(parent=service_prototype, type="component"):
        if old_bundle:
            try:
                old_service_proto = Prototype.objects.get(
                    name=service_prototype.name,
                    type="service",
                    bundle=old_bundle,
                )
                Prototype.objects.get(
                    parent=old_service_proto,
                    bundle=old_bundle,
                    type="component",
                    name=component_prototype.name,
                )
            except Prototype.DoesNotExist:
                continue

        check_components_mapping_contraints(
            hosts_count=Host.objects.filter(cluster=cluster).count(),
            target_mapping_count=len(
                [
                    i
                    for i in hc_in
                    if i[0].prototype.name == service_prototype.name and i[2].prototype.name == component_prototype.name
                ]
            ),
            service_prototype=service_prototype,
            component_prototype=component_prototype,
        )


_issue_check_map = {
    ConcernCause.CONFIG: check_config,
    ConcernCause.IMPORT: check_required_import,
    ConcernCause.SERVICE: check_required_services,
    ConcernCause.HOSTCOMPONENT: check_hc,
    ConcernCause.REQUIREMENT: check_requires,
}
_prototype_issue_map = {
    ObjectType.ADCM: (ConcernCause.CONFIG,),
    ObjectType.CLUSTER: (
        ConcernCause.CONFIG,
        ConcernCause.IMPORT,
        ConcernCause.SERVICE,
        ConcernCause.HOSTCOMPONENT,
    ),
    ObjectType.SERVICE: (ConcernCause.CONFIG, ConcernCause.IMPORT, ConcernCause.REQUIREMENT),
    ObjectType.COMPONENT: (ConcernCause.CONFIG,),
    ObjectType.PROVIDER: (ConcernCause.CONFIG,),
    ObjectType.HOST: (ConcernCause.CONFIG,),
}
_issue_template_map = {
    ConcernCause.CONFIG: ConcernMessage.CONFIG_ISSUE,
    ConcernCause.IMPORT: ConcernMessage.REQUIRED_IMPORT_ISSUE,
    ConcernCause.SERVICE: ConcernMessage.REQUIRED_SERVICE_ISSUE,
    ConcernCause.HOSTCOMPONENT: ConcernMessage.HOST_COMPONENT_ISSUE,
    ConcernCause.REQUIREMENT: ConcernMessage.UNSATISFIED_REQUIREMENT_ISSUE,
}


def _gen_issue_name(cause: ConcernCause) -> str:
    return f"{ConcernType.ISSUE}_{cause.value}"


def _get_kwargs_for_issue(concern_name: ConcernMessage, source: ADCMEntity) -> dict:
    kwargs = {"source": source}
    target = None

    if concern_name == ConcernMessage.REQUIRED_SERVICE_ISSUE:
        bundle = source.prototype.bundle
        # source is expected to be Cluster here
        target = (
            Prototype.objects.filter(
                bundle=bundle,
                type="service",
                required=True,
            )
            .exclude(id__in=ClusterObject.objects.values_list("prototype_id", flat=True).filter(cluster=source))
            .first()
        )

    elif concern_name == ConcernMessage.UNSATISFIED_REQUIREMENT_ISSUE:
        for require in source.prototype.requires:
            try:
                ClusterObject.objects.get(prototype__name=require["service"], cluster=source.cluster)
            except ClusterObject.DoesNotExist:
                target = Prototype.objects.get(name=require["service"], type="service", bundle=source.prototype.bundle)
                break

    kwargs["target"] = target
    return kwargs


def create_issue(obj: ADCMEntity, issue_cause: ConcernCause) -> ConcernItem:
    concern_message = _issue_template_map[issue_cause]
    kwargs = _get_kwargs_for_issue(concern_name=concern_message, source=obj)
    reason = build_concern_reason(
        template=concern_message.template, placeholder_objects=PlaceholderObjectsDTO(**kwargs)
    )
    type_: str = ConcernType.ISSUE.value
    cause: str = issue_cause.value
    return ConcernItem.objects.create(
        type=type_, name=f"{cause or ''}_{type_}".strip("_"), reason=reason, owner=obj, cause=cause
    )


def add_issue_on_linked_objects(obj: ADCMEntity, issue_cause: ConcernCause) -> None:
    """Create newly discovered issue and add it to linked objects concerns"""
    issue = obj.get_own_issue(cause=issue_cause) or create_issue(obj=obj, issue_cause=issue_cause)

    tree = Tree(obj)
    affected_nodes = tree.get_directly_affected(node=tree.built_from)

    for node in affected_nodes:
        add_concern_to_object(object_=node.value, concern=issue)


def remove_issue(obj: ADCMEntity, issue_cause: ConcernCause) -> None:
    """Remove outdated issue from other's concerns"""
    issue = obj.get_own_issue(cause=issue_cause)
    if not issue:
        return
    issue.delete()


def recheck_issues(obj: ADCMEntity) -> None:
    """Re-check for object's type-specific issues"""
    issue_causes = _prototype_issue_map.get(obj.prototype.type, [])
    for issue_cause in issue_causes:
        if not _issue_check_map[issue_cause](obj):
            add_issue_on_linked_objects(obj=obj, issue_cause=issue_cause)
        else:
            remove_issue(obj=obj, issue_cause=issue_cause)


def update_hierarchy_issues(obj: ADCMEntity) -> None:
    """Update issues on all directly connected objects"""
    tree = Tree(obj)
    affected_nodes = tree.get_directly_affected(node=tree.built_from)
    for node in affected_nodes:
        recheck_issues(obj=node.value)


def update_issue_after_deleting() -> None:
    """Remove issues which have no owners after object deleting"""
    for concern in ConcernItem.objects.filter(type=ConcernType.ISSUE):
        tree = Tree(obj=concern.owner)
        affected = {node.value for node in tree.get_directly_affected(node=tree.built_from)}
        related = set(concern.related_objects)
        if concern.owner is None:
            concern_str = str(concern)
            concern.delete()
            logger.info("Deleted %s", concern_str)
        elif related != affected:
            for object_moved_out_hierarchy in related.difference(affected):
                remove_concern_from_object(object_=object_moved_out_hierarchy, concern=concern)


def add_concern_to_object(object_: ADCMEntity, concern: ConcernItem | None) -> None:
    if not concern or getattr(concern, "id", None) is None:
        return

    if object_.concerns.filter(id=concern.id).exists():
        return

    object_.concerns.add(concern)

    concern_data = camelize(data=ConcernSerializer(instance=concern).data)
    on_commit(func=partial(send_concern_creation_event, object_=object_, concern=concern_data))


def remove_concern_from_object(object_: ADCMEntity, concern: ConcernItem | None) -> None:
    if not concern or not hasattr(concern, "id"):
        return

    concern_id = concern.id

    if not object_.concerns.filter(id=concern_id).exists():
        return

    object_.concerns.remove(concern)
    on_commit(
        func=partial(
            send_concern_delete_event, object_id=object_.pk, object_type=object_.prototype.type, concern_id=concern_id
        )
    )


def lock_affected_objects(task: TaskLog, objects: Iterable[ADCMEntity]) -> None:
    if task.lock:
        return

    owner: ADCMEntity = task.task_object
    first_job = JobLog.obj.filter(task=task).order_by("id").first()
    delete_service_action = settings.ADCM_DELETE_SERVICE_ACTION_NAME
    custom_name = delete_service_action if task.action.name == delete_service_action else ""

    task.lock = create_lock(owner=owner, job=first_job, custom_name=custom_name)
    task.save(update_fields=["lock"])

    for obj in objects:
        add_concern_to_object(object_=obj, concern=task.lock)


def create_lock(owner: ADCMEntity, job: JobLog, custom_name: str = ""):
    type_: str = ConcernType.LOCK.value
    cause: str = ConcernCause.JOB.value
    return ConcernItem.objects.create(
        type=type_,
        name=custom_name or f"{cause or ''}_{type_}".strip("_"),
        reason=build_concern_reason(
            ConcernMessage.LOCKED_BY_JOB.template, placeholder_objects=PlaceholderObjectsDTO(job=job, target=owner)
        ),
        blocking=True,
        owner=owner,
        cause=cause,
    )


def update_job_in_lock_reason(lock: ConcernItem, job: JobLog) -> ConcernItem:
    lock.reason = build_concern_reason(
        ConcernMessage.LOCKED_BY_JOB.template, placeholder_objects=PlaceholderObjectsDTO(job=job, target=lock.owner)
    )
    lock.save(update_fields=["reason"])
    return lock


def unlock_affected_objects(task: TaskLog) -> None:
    task.refresh_from_db()

    if not task.lock:
        return

    lock = task.lock
    task.lock = None
    task.save(update_fields=["lock"])
    lock.delete()
