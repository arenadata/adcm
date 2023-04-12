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

from cm.adcm_config import get_prototype_config, proto_ref
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
    KnownNames,
    MessageTemplate,
    ObjectType,
    Prototype,
    PrototypeImport,
    ServiceComponent,
)
from cm.utils import obj_ref


def check_config(obj: ADCMEntity) -> bool:  # pylint: disable=too-many-branches # noqa: C901
    spec, _, _, _ = get_prototype_config(proto=obj.prototype)
    conf, attr = get_obj_config(obj=obj)
    for key, value in spec.items():  # pylint: disable=too-many-nested-blocks
        if "required" in value:
            if value["required"]:
                if key in conf and conf[key] is None:
                    logger.debug("required config key %s of %s is missing", key, obj_ref(obj=obj))
                    return False
        else:
            if key in attr:
                if "active" in attr[key] and not attr[key]["active"]:
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

    for prototype_import in PrototypeImport.objects.filter(prototype=proto):
        if not prototype_import.required:
            return True, "NOT_REQUIRED"

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
            ref = f'component "{serv_host_comp[2].prototype.name}" of service "{serv_host_comp[0].prototype.name}"'

            if not ClusterObject.objects.filter(prototype__name=require["service"]).exists():
                raise AdcmEx(
                    code="COMPONENT_CONSTRAINT_ERROR", msg=f"No required service {require['service']} for {ref}"
                )

            if not require.get("component"):
                continue

            if not any(
                {
                    (shc[0].prototype.name == require["service"] and shc[2].prototype.name == require["component"])
                    for shc in shc_list
                }
            ):
                msg = f'No required component "{require["component"]}" of service "{require["service"]}" for {ref}'
                raise AdcmEx(code="COMPONENT_CONSTRAINT_ERROR", msg=msg)


def check_bound_components(shc_list: list[tuple[ClusterObject, Host, ServiceComponent]]) -> None:
    for shc in [i for i in shc_list if i[2].prototype.bound_to]:
        component = shc[2].prototype
        service = component.bound_to["service"]
        comp_name = component.bound_to["component"]
        ref = f'component "{comp_name}" of service "{service}"'
        bound_hc = [i for i in shc_list if i[0].prototype.name == service and i[2].prototype.name == comp_name]
        if not bound_hc:
            msg = f'bound service "{service}", component "{comp_name}" not in hc for {ref}'
            raise AdcmEx(code="COMPONENT_CONSTRAINT_ERROR", msg=msg)
        for shc in bound_hc:
            if not [i for i in shc_list if i[1] == shc[1] and i[2].prototype == component]:
                msg = f'No bound component "{component.name}" on host "{shc[1].fqdn}" for {ref}'
                raise AdcmEx(code="COMPONENT_CONSTRAINT_ERROR", msg=msg)


def get_obj_config(obj: ADCMEntity) -> tuple[dict, dict]:
    if obj.config is None:
        return {}, {}

    config_log = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
    attr = config_log.attr
    if not attr:
        attr = {}

    return config_log.config, attr


def check_component_constraint(
    cluster: Cluster, service_prototype: Prototype, hc_in: list, old_bundle: Bundle | None = None
) -> None:
    ref = f"in host component list for {service_prototype.type} {service_prototype.name}"
    all_host = Host.objects.filter(cluster=cluster)

    def check_min(count: int, constraint: int, comp: ServiceComponent) -> None:
        if count < constraint:
            raise AdcmEx(
                code="COMPONENT_CONSTRAINT_ERROR",
                msg=f'less then {constraint} required component "{comp.name}" ({count}) {ref}',
            )

    def check_max(count: int, constraint: int, comp: ServiceComponent) -> None:
        if count > constraint:
            raise AdcmEx(
                code="COMPONENT_CONSTRAINT_ERROR",
                msg=f'amount ({count}) of component "{comp.name}" more then maximum ({constraint}) {ref}',
            )

    def check_odd(count: int, constraint: str, comp: ServiceComponent) -> None:
        if count % 2 == 0:
            raise AdcmEx(
                code="COMPONENT_CONSTRAINT_ERROR",
                msg=f'amount ({count}) of component "{comp.name}" should be odd ({constraint}) {ref}',
            )

    def check(comp: ServiceComponent, constraint: list) -> None:
        count = 0
        for _, _, component in hc_in:
            if comp.name == component.prototype.name:
                count += 1

        if isinstance(constraint[0], int):
            check_min(count=count, constraint=constraint[0], comp=comp)
            if len(constraint) < 2:
                check_max(count=count, constraint=constraint[0], comp=comp)

        if len(constraint) > 1:
            if isinstance(constraint[1], int):
                check_max(count=count, constraint=constraint[1], comp=comp)
            elif constraint[1] == "odd" and count:
                check_odd(count=count, constraint=constraint[1], comp=comp)

        if constraint[0] == "+":
            check_min(count=count, constraint=len(all_host), comp=comp)
        elif constraint[0] == "odd":
            check_odd(count=count, constraint=constraint[0], comp=comp)

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

        check(comp=component_prototype, constraint=component_prototype.constraint)


_issue_check_map = {
    ConcernCause.CONFIG: check_config,
    ConcernCause.IMPORT: check_required_import,
    ConcernCause.SERVICE: check_required_services,
    ConcernCause.HOSTCOMPONENT: check_hc,
    ConcernCause.REQUIREMENT: check_requires,
}
_prototype_issue_map = {
    ObjectType.ADCM: (),
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
    ConcernCause.CONFIG: KnownNames.CONFIG_ISSUE,
    ConcernCause.IMPORT: KnownNames.REQUIRED_IMPORT_ISSUE,
    ConcernCause.SERVICE: KnownNames.REQUIRED_SERVICE_ISSUE,
    ConcernCause.HOSTCOMPONENT: KnownNames.HOST_COMPONENT_ISSUE,
    ConcernCause.REQUIREMENT: KnownNames.UNSATISFIED_REQUIREMENT_ISSUE,
}


def _gen_issue_name(obj: ADCMEntity, cause: ConcernCause) -> str:
    """Make human-understandable issue name for debug use"""
    return f"{obj} has issue with {cause.value}"


def _create_concern_item(obj: ADCMEntity, issue_cause: ConcernCause) -> ConcernItem:
    msg_name = _issue_template_map[issue_cause]
    reason = MessageTemplate.get_message_from_template(name=msg_name.value, source=obj)
    issue_name = _gen_issue_name(obj=obj, cause=issue_cause)
    issue = ConcernItem.objects.create(
        type=ConcernType.ISSUE,
        name=issue_name,
        reason=reason,
        owner=obj,
        cause=issue_cause,
    )
    return issue


def create_issue(obj: ADCMEntity, issue_cause: ConcernCause) -> None:
    """Create newly discovered issue and add it to linked objects concerns"""
    issue = obj.get_own_issue(cause=issue_cause)
    if issue is None:
        issue = _create_concern_item(obj=obj, issue_cause=issue_cause)
    if issue.name != _gen_issue_name(obj=obj, cause=issue_cause):
        issue.delete()
        issue = _create_concern_item(obj=obj, issue_cause=issue_cause)
    tree = Tree(obj)
    affected_nodes = tree.get_directly_affected(node=tree.built_from)
    for node in affected_nodes:
        node.value.add_to_concerns(item=issue)


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
            create_issue(obj=obj, issue_cause=issue_cause)
        else:
            remove_issue(obj=obj, issue_cause=issue_cause)


def update_hierarchy_issues(obj: ADCMEntity) -> None:
    """Update issues on all directly connected objects"""
    tree = Tree(obj)
    affected_nodes = tree.get_directly_affected(node=tree.built_from)
    for node in affected_nodes:
        node_value = node.value
        recheck_issues(obj=node_value)


def update_issue_after_deleting() -> None:
    """Remove issues which have no owners after object deleting"""
    for concern in ConcernItem.objects.exclude(type=ConcernType.LOCK):
        tree = Tree(obj=concern.owner)
        affected = {node.value for node in tree.get_directly_affected(node=tree.built_from)}
        related = set(concern.related_objects)  # pylint: disable=consider-using-set-comprehension
        if concern.owner is None:
            concern_str = str(concern)
            concern.delete()
            logger.info("Deleted %s", concern_str)
        elif related != affected:
            for object_moved_out_hierarchy in related.difference(affected):
                object_moved_out_hierarchy.remove_from_concerns(item=concern)
