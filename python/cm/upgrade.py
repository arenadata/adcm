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

from abc import ABC, abstractmethod
from collections import defaultdict, deque
from operator import itemgetter
import functools

from adcm_version import compare_prototype_versions
from core.cluster.types import HostComponentEntry
from core.types import ADCMCoreType, ClusterID, CoreObjectDescriptor
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from rbac.models import Policy

from cm.adcm_config.config import (
    init_object_config,
    make_object_config,
    save_object_config,
    switch_config,
)
from cm.adcm_config.utils import proto_ref
from cm.api import (
    add_components_to_service,
    add_service_to_cluster,
    check_license,
    is_version_suitable,
)
from cm.converters import orm_object_to_core_type
from cm.errors import AdcmEx
from cm.logger import logger
from cm.models import (
    ADCMEntity,
    Bundle,
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
    MaintenanceMode,
    ObjectType,
    Prototype,
    PrototypeImport,
    Provider,
    Service,
    Upgrade,
)
from cm.services.cluster import retrieve_cluster_topology, retrieve_multiple_clusters_topology
from cm.services.concern import create_issue, retrieve_issue
from cm.services.concern.cases import (
    recalculate_concerns_on_cluster_upgrade,
)
from cm.services.concern.checks import object_configuration_has_issue
from cm.services.concern.distribution import (
    AffectedObjectConcernMap,
    distribute_concern_on_related_objects,
    redistribute_issues_and_flags,
)
from cm.services.job.action import ActionRunPayload, run_action
from cm.services.job.types import HcAclAction
from cm.services.mapping import change_host_component_mapping, check_nothing
from cm.status_api import send_prototype_and_state_update_event
from cm.utils import obj_ref


def check_upgrade(obj: Cluster | Provider, upgrade: Upgrade) -> tuple[bool, str]:
    if obj.locked:
        concerns = [concern.name or "Action lock" for concern in obj.concerns.order_by("id")]

        return False, f"{obj} has blocking concerns to address: {concerns}"

    success, msg = _check_upgrade_version(prototype=obj.prototype, upgrade=upgrade)
    if not success:
        return False, msg

    success, msg = _check_upgrade_edition(prototype=obj.prototype, upgrade=upgrade)
    if not success:
        return False, msg

    if not upgrade.allowed(obj=obj):
        return False, "no available states"

    if obj.prototype.type == ObjectType.CLUSTER:
        success, msg = _check_upgrade_import(obj=obj, upgrade=upgrade)
        if not success:
            return False, msg

    return True, ""


def get_upgrade(obj: Cluster | Provider, order=None) -> list[Upgrade]:
    res = []
    for upgrade in Upgrade.objects.filter(bundle__name=obj.prototype.bundle.name):
        success, _ = _check_upgrade_version(prototype=obj.prototype, upgrade=upgrade)
        if not success:
            continue

        success, _ = _check_upgrade_edition(prototype=obj.prototype, upgrade=upgrade)
        if not success:
            continue

        if obj.locked or not upgrade.allowed(obj=obj):
            continue

        upgrade_proto = Prototype.objects.filter(bundle=upgrade.bundle, name=upgrade.bundle.name).first()
        upgrade.license = upgrade_proto.license
        res.append(upgrade)

    if order:
        if "name" in order:
            return sorted(
                res,
                key=functools.cmp_to_key(mycmp=lambda obj1, obj2: compare_prototype_versions(obj1.name, obj2.name)),
            )

        if "-name" in order:
            return sorted(
                res,
                key=functools.cmp_to_key(mycmp=lambda obj1, obj2: compare_prototype_versions(obj2.name, obj2.name)),
            )

    return res


def do_upgrade(
    obj: Cluster | Provider,
    upgrade: Upgrade,
    config: dict,
    attr: dict,
    hostcomponent: list[dict],
    verbose: bool = False,
) -> dict:
    check_license(prototype=obj.prototype)
    upgrade_prototype = Prototype.objects.filter(
        bundle=upgrade.bundle, name=upgrade.bundle.name, type__in=[ObjectType.CLUSTER, ObjectType.PROVIDER]
    ).first()
    check_license(prototype=upgrade_prototype)

    success, msg = check_upgrade(obj=obj, upgrade=upgrade)
    if not success:
        raise AdcmEx(code="UPGRADE_ERROR", msg=msg)

    logger.info("upgrade %s version %s (upgrade #%s)", obj_ref(obj), obj.prototype.version, upgrade.id)

    task_id = None

    obj.before_upgrade["bundle_id"] = obj.prototype.bundle.pk
    _update_before_upgrade(obj=obj)

    if not upgrade.action:
        bundle_switch(obj=obj, upgrade=upgrade)

        if upgrade.state_on_success:
            obj.state = upgrade.state_on_success
            obj.save(update_fields=["state"])

        send_prototype_and_state_update_event(object_=obj)
    else:
        bundle_id = upgrade.bundle_id
        add_hc_rules = {
            (rule["service"], rule["component"])
            for rule in upgrade.action.hostcomponentmap
            if rule["action"] == HcAclAction.ADD.value
        }

        existing_hostcomponent: set[HostComponentEntry] = set()
        post_upgrade: list[dict] = []
        for entry in hostcomponent:
            # alternative to removed `_check_upgrade_hc`
            if "component_prototype_id" in entry:
                component_name, service_name = Prototype.obj.values_list("name", "parent__name").get(
                    type="component",
                    id=entry["component_prototype_id"],
                    bundle_id=bundle_id,
                )
                if (service_name, component_name) not in add_hc_rules:
                    raise AdcmEx(
                        code="WRONG_ACTION_HC",
                        msg="New components from bundle with upgrade you can only add, not remove",
                    )

                post_upgrade.append(entry)
            else:
                existing_hostcomponent.add(
                    HostComponentEntry(host_id=entry["host_id"], component_id=entry["component_id"])
                )

        task = run_action(
            action=upgrade.action,
            obj=obj,
            payload=ActionRunPayload(conf=config, attr=attr, hostcomponent=existing_hostcomponent, verbose=verbose),
            post_upgrade_hc=post_upgrade,
        )
        task_id = task.id

    obj.refresh_from_db()

    return {"id": obj.id, "upgradable": bool(get_upgrade(obj=obj)), "task_id": task_id}


def bundle_switch(obj: Cluster | Provider, upgrade: Upgrade) -> None:
    if isinstance(obj, Cluster):
        switch = _ClusterBundleSwitch(target=obj, upgrade=upgrade)
    elif isinstance(obj, Provider):
        switch = _ProviderBundleSwitch(target=obj, upgrade=upgrade)
    else:
        raise AdcmEx(code="UPGRADE_ERROR", msg="can upgrade only cluster or host provider")

    switch.perform()


def bundle_revert(obj: Cluster | Provider) -> None:
    upgraded_bundle = obj.prototype.bundle
    old_bundle = Bundle.objects.get(pk=obj.before_upgrade["bundle_id"])
    old_proto = Prototype.objects.filter(bundle=old_bundle, name=old_bundle.name).first()
    before_upgrade_hc = obj.before_upgrade.get("hc")
    service_names = obj.before_upgrade.get("services")

    _revert_object(obj=obj, old_proto=old_proto)

    if isinstance(obj, Cluster):
        for service_prototype in Prototype.objects.filter(bundle=old_bundle, type="service"):
            service = Service.objects.filter(cluster=obj, prototype__name=service_prototype.name).first()
            if not service:
                continue

            _revert_object(obj=service, old_proto=service_prototype)
            for component_prototype in Prototype.objects.filter(
                bundle=old_bundle, parent=service_prototype, type="component"
            ):
                component = Component.objects.filter(
                    cluster=obj,
                    service=service,
                    prototype__name=component_prototype.name,
                ).first()

                if component:
                    _revert_object(obj=component, old_proto=component_prototype)
                else:
                    component = Component.objects.create(
                        cluster=obj,
                        service=service,
                        prototype=component_prototype,
                    )
                    obj_conf = init_object_config(proto=component_prototype, obj=component)
                    component.config = obj_conf
                    component.save(update_fields=["config"])

        Service.objects.filter(cluster=obj, prototype__bundle=upgraded_bundle).delete()
        Component.objects.filter(cluster=obj, prototype__bundle=upgraded_bundle).delete()

        for service_name in service_names:
            prototype = Prototype.objects.get(bundle=old_bundle, name=service_name, type="service")

            if not Service.objects.filter(prototype=prototype, cluster=obj).exists():
                add_service_to_cluster(cluster=obj, proto=prototype)

        host_comp_list = []
        for hostcomponent in before_upgrade_hc:
            host = Host.objects.get(fqdn=hostcomponent["host"], cluster=obj)
            service = Service.objects.get(prototype__name=hostcomponent["service"], cluster=obj)
            component = Component.objects.get(
                prototype__name=hostcomponent["component"],
                cluster=obj,
                service=service,
            )
            host_comp_list.append((service, host, component))

        change_host_component_mapping(
            cluster_id=obj.id,
            bundle_id=old_proto.bundle_id,
            flat_mapping=(
                HostComponentEntry(host_id=host.id, component_id=component.id)
                for (_, host, component) in host_comp_list
            ),
            checks_func=check_nothing,
        )

    if isinstance(obj, Provider):
        for host in Host.objects.filter(provider=obj):
            old_host_proto = Prototype.objects.get(bundle=old_bundle, type="host", name=host.prototype.name)
            _revert_object(obj=host, old_proto=old_host_proto)


def _switch_object(obj: Host | Service, new_prototype: Prototype) -> None:
    logger.info("upgrade switch from %s to %s", proto_ref(prototype=obj.prototype), proto_ref(prototype=new_prototype))

    old_prototype = obj.prototype
    obj.prototype = new_prototype
    obj.save(update_fields=["prototype"])

    switch_config(obj=obj, new_prototype=new_prototype, old_prototype=old_prototype)


def _switch_components(cluster: Cluster, service: Service, new_component_prototype: Prototype) -> None:
    for component in Component.objects.filter(cluster=cluster, service=service):
        try:
            new_comp_prototype = Prototype.objects.get(
                parent=new_component_prototype, type="component", name=component.prototype.name
            )
            _switch_object(obj=component, new_prototype=new_comp_prototype)
        except Prototype.DoesNotExist:
            component.delete()

    for component_prototype in Prototype.objects.filter(parent=new_component_prototype, type="component"):
        kwargs = {"cluster": cluster, "service": service, "prototype": component_prototype}
        if not Component.objects.filter(**kwargs).exists():
            component = Component.objects.create(**kwargs)
            make_object_config(obj=component, prototype=component_prototype)


def _check_upgrade_version(prototype: Prototype, upgrade: Upgrade) -> tuple[bool, str]:
    if upgrade.min_strict:
        if compare_prototype_versions(prototype.version, upgrade.min_version) <= 0:
            return (
                False,
                f"{prototype.type} version {prototype.version} "
                f"is less than or equal to upgrade min version {upgrade.min_version}",
            )
    else:
        if compare_prototype_versions(prototype.version, upgrade.min_version) < 0:
            return (
                False,
                "{prototype.type} version {prototype.version} is less than upgrade min version {upgrade.min_version}",
            )

    if upgrade.max_strict:
        if compare_prototype_versions(prototype.version, upgrade.max_version) >= 0:
            return (
                False,
                f"{prototype.type} version {prototype.version} "
                f"is more than or equal to upgrade max version {upgrade.max_version}",
            )
    else:
        if compare_prototype_versions(prototype.version, upgrade.max_version) > 0:
            return (
                False,
                f"{prototype.type} version {prototype.version} is more than upgrade max version {upgrade.max_version}",
            )

    return True, ""


def _check_upgrade_edition(prototype: Prototype, upgrade: Upgrade) -> tuple[bool, str]:
    if upgrade.from_edition == "any":
        return True, ""

    if upgrade.from_edition and prototype.bundle.edition not in upgrade.from_edition:
        return False, f'bundle edition "{prototype.bundle.edition}" is not in upgrade list: {upgrade.from_edition}'

    return True, ""


def _check_upgrade_import(obj: Cluster, upgrade: Upgrade) -> tuple[bool, str]:
    for cbind in ClusterBind.objects.filter(cluster=obj):
        export = cbind.source_service if cbind.source_service else cbind.source_cluster
        import_obj = cbind.service if cbind.service else cbind.cluster
        try:
            prototype = Prototype.objects.get(
                bundle=upgrade.bundle,
                name=import_obj.prototype.name,
                type=import_obj.prototype.type,
            )
        except Prototype.DoesNotExist:
            return (
                False,
                f"Upgrade does not have new version of "
                f'{import_obj.prototype.type} "{import_obj.prototype.name}" {import_obj.prototype.version}',
            )

        try:
            prototype_import = PrototypeImport.objects.get(prototype=prototype, name=export.prototype.name)
            if not is_version_suitable(export.prototype.version, prototype_import):
                return (
                    False,
                    f'Import "{export.prototype.name}" of {prototype.type} "{prototype.name}" {prototype.version} '
                    f"versions ({prototype_import.min_version}, {prototype_import.max_version}) "
                    f"does not match export version: {export.prototype.version} ({obj_ref(obj=export)})",
                )
        except PrototypeImport.DoesNotExist:
            cbind.delete()

    for cbind in ClusterBind.objects.filter(source_cluster=obj):
        export = cbind.source_service if cbind.source_service else cbind.source_cluster
        try:
            prototype = Prototype.objects.get(
                bundle=upgrade.bundle,
                name=export.prototype.name,
                type=export.prototype.type,
            )
        except Prototype.DoesNotExist:
            return (
                False,
                f"Upgrade does not have new version of "
                f'{export.prototype.type} "{export.prototype.name}" {export.prototype.version} required for export',
            )

        import_obj = cbind.service if cbind.service else cbind.cluster
        prototype_import = PrototypeImport.objects.get(prototype=import_obj.prototype, name=export.prototype.name)
        if not is_version_suitable(prototype.version, prototype_import):
            return (
                False,
                f'Export of {prototype.type} "{prototype.name}" {prototype.version} '
                f"does not match import versions: ({prototype_import.min_version}, "
                f"{prototype_import.max_version}) ({obj_ref(obj=import_obj)})",
            )

    return True, ""


def _revert_object(obj: ADCMEntity, old_proto: Prototype) -> None:
    if obj.prototype == old_proto:
        return

    obj.prototype = old_proto

    if "config_id" in obj.before_upgrade:
        config_log = ConfigLog.objects.get(id=obj.before_upgrade["config_id"])
        obj.config.current = 0
        save_object_config(
            object_config=obj.config, config=config_log.config, attr=config_log.attr, description="revert_upgrade"
        )
    else:
        obj.config = None

    obj.state = obj.before_upgrade["state"]
    obj.before_upgrade = {"state": None}
    obj.save(update_fields=["prototype", "config", "state", "before_upgrade"])


def _set_before_upgrade(obj: ADCMEntity) -> None:
    obj.before_upgrade["state"] = obj.state
    if obj.config:
        obj.before_upgrade["config_id"] = obj.config.current

    if groups := ConfigHostGroup.objects.filter(object_id=obj.id, object_type=ContentType.objects.get_for_model(obj)):
        obj.before_upgrade["groups"] = {}

        for group in groups:
            obj.before_upgrade["groups"][group.name] = {"group_config_id": group.config.current}

    if isinstance(obj, Cluster):
        hc_map = []
        for hostcomponent in HostComponent.objects.filter(cluster=obj):
            hc_map.append(
                {
                    "service": hostcomponent.service.name,
                    "component": hostcomponent.component.name,
                    "host": hostcomponent.host.name,
                },
            )

        obj.before_upgrade["hc"] = hc_map
        obj.before_upgrade["services"] = [service.prototype.name for service in Service.objects.filter(cluster=obj)]

    obj.save(update_fields=["before_upgrade"])


def _update_before_upgrade(obj: Cluster | Provider) -> None:
    _set_before_upgrade(obj=obj)

    if isinstance(obj, Cluster):
        for service in Service.objects.filter(cluster=obj):
            _set_before_upgrade(obj=service)
            for component in Component.objects.filter(service=service, cluster=obj):
                _set_before_upgrade(obj=component)

    if isinstance(obj, Provider):
        for host in Host.objects.filter(provider=obj):
            _set_before_upgrade(obj=host)


class _BundleSwitch(ABC):
    def __init__(self, target: Cluster | Provider, upgrade: Upgrade):
        self._target = target
        self._upgrade = upgrade

    def perform(self) -> None:
        with transaction.atomic():
            old_prototype = self._target.prototype
            new_prototype = Prototype.objects.get(
                bundle_id=self._upgrade.bundle_id, type__in=(ObjectType.CLUSTER, ObjectType.PROVIDER)
            )
            self._target.prototype = new_prototype
            self._target.save(update_fields=["prototype"])
            switch_config(obj=self._target, new_prototype=new_prototype, old_prototype=old_prototype)

            self._target.refresh_from_db()

            self._upgrade_children(old_prototype=old_prototype, new_prototype=new_prototype)
            added, removed = self._update_concerns()

            for policy_object, content_type in self._get_objects_map_for_policy_update().items():
                for policy in Policy.objects.filter(
                    object__object_id=policy_object.id, object__content_type=content_type
                ):
                    policy.apply()

        logger.info("upgrade %s OK to version %s", obj_ref(obj=self._target), new_prototype.version)

    @abstractmethod
    def _upgrade_children(self, old_prototype: Prototype, new_prototype: Prototype) -> None:
        ...

    @abstractmethod
    def _update_concerns(self) -> tuple[AffectedObjectConcernMap, AffectedObjectConcernMap]:
        ...

    @abstractmethod
    def _get_objects_map_for_policy_update(self) -> dict[ADCMEntity, ContentType]:
        ...


class _ClusterBundleSwitch(_BundleSwitch):
    def __init__(self, target: Cluster, upgrade: Upgrade):
        super().__init__(target, upgrade)

    def _upgrade_children(self, old_prototype: Prototype, new_prototype: Prototype) -> None:
        for service in Service.objects.select_related("prototype").filter(cluster=self._target):
            check_license(prototype=service.prototype)
            try:
                new_service_prototype = Prototype.objects.get(
                    bundle_id=self._upgrade.bundle_id, type="service", name=service.prototype.name
                )
                check_license(prototype=new_service_prototype)
                _switch_object(obj=service, new_prototype=new_service_prototype)
                _switch_components(cluster=self._target, service=service, new_component_prototype=new_service_prototype)
            except Prototype.DoesNotExist:
                service.delete()

        # remove HC entries that which components don't exist anymore
        existing_names: set[tuple[str, str]] = set(
            Prototype.objects.values_list("parent__name", "name").filter(
                bundle_id=self._upgrade.bundle_id, type="component"
            )
        )
        entries_to_delete = deque()
        for hc_id, service_name, component_name in HostComponent.objects.values_list(
            "id", "service__prototype__name", "component__prototype__name"
        ).filter(cluster=self._target):
            if (service_name, component_name) not in existing_names:
                entries_to_delete.append(hc_id)

        HostComponent.objects.filter(id__in=entries_to_delete).delete()

        if old_prototype.allow_maintenance_mode != new_prototype.allow_maintenance_mode:
            Host.objects.filter(cluster=self._target).update(maintenance_mode=MaintenanceMode.OFF)

        if self._upgrade.action and self._upgrade.action.hostcomponentmap:
            logger.info("update component from %s after upgrade with hc_acl", self._target)
            services_in_new_hc = set(map(itemgetter("service"), self._upgrade.action.hostcomponentmap))
            for proto_service in Prototype.objects.filter(
                type="service",
                bundle_id=self._upgrade.bundle_id,
                name__in=services_in_new_hc,
            ):
                # probably operations below can be performed in bulk for speed improvement
                try:
                    service = Service.objects.select_related("prototype").get(
                        cluster=self._target, prototype=proto_service
                    )
                except Service.DoesNotExist:
                    # this code was taken from service creation from `cm.api` skipping checks, concerns, etc.
                    check_license(prototype=proto_service)
                    service = Service.objects.create(cluster=self._target, prototype=proto_service)
                    service.config = init_object_config(proto=proto_service, obj=service)
                    service.save(update_fields=["config"])

                if not Component.objects.filter(cluster=self._target, service=service).exists():
                    add_components_to_service(cluster=self._target, service=service)

    def _update_concerns(self) -> tuple[AffectedObjectConcernMap, AffectedObjectConcernMap]:
        recalculate_concerns_on_cluster_upgrade(cluster=self._target)
        return redistribute_issues_and_flags(topology=retrieve_cluster_topology(self._target.id))

    def _get_objects_map_for_policy_update(self) -> dict[Cluster | Service | Component, ContentType]:
        obj_type_map = {self._target: ContentType.objects.get_for_model(Cluster)}

        service_content_type = ContentType.objects.get_for_model(Service)
        for service in Service.objects.filter(cluster=self._target):
            obj_type_map[service] = service_content_type

        component_content_type = ContentType.objects.get_for_model(Component)
        for component in Component.objects.filter(cluster=self._target):
            obj_type_map[component] = component_content_type

        return obj_type_map


class _ProviderBundleSwitch(_BundleSwitch):
    def __init__(self, target: Provider, upgrade: Upgrade):
        super().__init__(target, upgrade)

    def _upgrade_children(self, old_prototype: Prototype, new_prototype: Prototype) -> None:  # noqa: ARG002
        for prototype in Prototype.objects.filter(bundle_id=self._upgrade.bundle_id, type="host"):
            for host in Host.objects.filter(provider=self._target, prototype__name=prototype.name):
                _switch_object(host, prototype)

    def _update_concerns(self) -> tuple[AffectedObjectConcernMap, AffectedObjectConcernMap]:
        added, removed = defaultdict(lambda: defaultdict(set)), {}
        target_cod = CoreObjectDescriptor(id=self._target.id, type=orm_object_to_core_type(self._target))
        target_own_config_issue = retrieve_issue(owner=target_cod, cause=ConcernCause.CONFIG)
        if target_own_config_issue is None and object_configuration_has_issue(self._target):
            concern = create_issue(owner=target_cod, cause=ConcernCause.CONFIG)
            related_objects = distribute_concern_on_related_objects(owner=target_cod, concern_id=concern.id)
            for core_type, object_ids in related_objects.items():
                for object_id in object_ids:
                    added[core_type][object_id].add(concern.id)

        clusters_for_redistribution: set[ClusterID] = set()
        m2m_model = Host.concerns.through
        host_own_concerns_to_link = deque()

        for host in (
            Host.objects.select_related("prototype__bundle")
            .filter(provider=self._target)
            .exclude(
                id__in=ConcernItem.objects.values_list("owner_id", flat=True).filter(
                    owner_type=ContentType.objects.get_for_model(Host),
                    type=ConcernType.ISSUE,
                    cause=ConcernCause.CONFIG,
                )
            )
        ):
            if object_configuration_has_issue(host):
                concern = create_issue(
                    owner=CoreObjectDescriptor(id=host.id, type=ADCMCoreType.HOST), cause=ConcernCause.CONFIG
                )
                clusters_for_redistribution.add(host.cluster_id)
                host_own_concerns_to_link.append(m2m_model(host_id=host.id, concernitem_id=concern.id))
                added[ADCMCoreType.HOST][host.id].add(concern.id)

        m2m_model.objects.bulk_create(objs=host_own_concerns_to_link)

        clusters_for_redistribution -= {None}
        if clusters_for_redistribution:
            for topology in retrieve_multiple_clusters_topology(cluster_ids=clusters_for_redistribution):
                added_, removed_ = redistribute_issues_and_flags(topology=topology)

                for core_type, added_entries in added_.items():
                    for object_id, concern_ids in added_entries.items():
                        added[core_type][object_id].update(concern_ids)

                for core_type, removed_entries in removed_.items():
                    for object_id, concern_ids in removed_entries.items():
                        removed[core_type][object_id].update(concern_ids)

        return added, removed

    def _get_objects_map_for_policy_update(self) -> dict[Provider | Host, ContentType]:
        obj_type_map = {self._target: ContentType.objects.get_for_model(Provider)}

        host_content_type = ContentType.objects.get_for_model(Host)
        for host in Host.objects.filter(provider=self._target):
            obj_type_map[host] = host_content_type

        return obj_type_map
