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
from collections import deque
from operator import itemgetter
import functools

from adcm_version import compare_prototype_versions
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
    save_hc,
)
from cm.converters import orm_object_to_core_type
from cm.errors import AdcmEx
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
    GroupConfig,
    Host,
    HostComponent,
    HostProvider,
    MaintenanceMode,
    ObjectType,
    Prototype,
    PrototypeImport,
    ServiceComponent,
    Upgrade,
)
from cm.services.cluster import retrieve_clusters_topology
from cm.services.concern import create_issue, retrieve_issue
from cm.services.concern.cases import (
    recalculate_concerns_on_cluster_upgrade,
)
from cm.services.concern.checks import object_configuration_has_issue
from cm.services.concern.distribution import distribute_concern_on_related_objects, redistribute_issues_and_flags
from cm.services.job.action import ActionRunPayload, run_action
from cm.status_api import send_prototype_and_state_update_event
from cm.utils import obj_ref


def check_upgrade(obj: Cluster | HostProvider, upgrade: Upgrade) -> tuple[bool, str]:
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


def get_upgrade(obj: Cluster | HostProvider, order=None) -> list[Upgrade]:
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
    obj: Cluster | HostProvider,
    upgrade: Upgrade,
    config: dict,
    attr: dict,
    hostcomponent: list,
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
        task = run_action(
            action=upgrade.action,
            obj=obj,
            payload=ActionRunPayload(conf=config, attr=attr, hostcomponent=hostcomponent, verbose=verbose),
        )
        task_id = task.id

    obj.refresh_from_db()

    return {"id": obj.id, "upgradable": bool(get_upgrade(obj=obj)), "task_id": task_id}


def bundle_switch(obj: Cluster | HostProvider, upgrade: Upgrade) -> None:
    if isinstance(obj, Cluster):
        switch = _ClusterBundleSwitch(target=obj, upgrade=upgrade)
    elif isinstance(obj, HostProvider):
        switch = _HostProviderBundleSwitch(target=obj, upgrade=upgrade)
    else:
        raise AdcmEx(code="UPGRADE_ERROR", msg="can upgrade only cluster or host provider")

    switch.perform()


def bundle_revert(obj: Cluster | HostProvider) -> None:
    upgraded_bundle = obj.prototype.bundle
    old_bundle = Bundle.objects.get(pk=obj.before_upgrade["bundle_id"])
    old_proto = Prototype.objects.filter(bundle=old_bundle, name=old_bundle.name).first()
    before_upgrade_hc = obj.before_upgrade.get("hc")
    service_names = obj.before_upgrade.get("services")

    _revert_object(obj=obj, old_proto=old_proto)

    if isinstance(obj, Cluster):
        for service_prototype in Prototype.objects.filter(bundle=old_bundle, type="service"):
            service = ClusterObject.objects.filter(cluster=obj, prototype__name=service_prototype.name).first()
            if not service:
                continue

            _revert_object(obj=service, old_proto=service_prototype)
            for component_prototype in Prototype.objects.filter(
                bundle=old_bundle, parent=service_prototype, type="component"
            ):
                component = ServiceComponent.objects.filter(
                    cluster=obj,
                    service=service,
                    prototype__name=component_prototype.name,
                ).first()

                if component:
                    _revert_object(obj=component, old_proto=component_prototype)
                else:
                    component = ServiceComponent.objects.create(
                        cluster=obj,
                        service=service,
                        prototype=component_prototype,
                    )
                    obj_conf = init_object_config(proto=component_prototype, obj=component)
                    component.config = obj_conf
                    component.save(update_fields=["config"])

        ClusterObject.objects.filter(cluster=obj, prototype__bundle=upgraded_bundle).delete()
        ServiceComponent.objects.filter(cluster=obj, prototype__bundle=upgraded_bundle).delete()

        for service_name in service_names:
            prototype = Prototype.objects.get(bundle=old_bundle, name=service_name, type="service")

            if not ClusterObject.objects.filter(prototype=prototype, cluster=obj).exists():
                add_service_to_cluster(cluster=obj, proto=prototype)

        host_comp_list = []
        for hostcomponent in before_upgrade_hc:
            host = Host.objects.get(fqdn=hostcomponent["host"], cluster=obj)
            service = ClusterObject.objects.get(prototype__name=hostcomponent["service"], cluster=obj)
            component = ServiceComponent.objects.get(
                prototype__name=hostcomponent["component"],
                cluster=obj,
                service=service,
            )
            host_comp_list.append((service, host, component))

        save_hc(cluster=obj, host_comp_list=host_comp_list)

    if isinstance(obj, HostProvider):
        for host in Host.objects.filter(provider=obj):
            old_host_proto = Prototype.objects.get(bundle=old_bundle, type="host", name=host.prototype.name)
            _revert_object(obj=host, old_proto=old_host_proto)


def _switch_object(obj: Host | ClusterObject, new_prototype: Prototype) -> None:
    logger.info("upgrade switch from %s to %s", proto_ref(prototype=obj.prototype), proto_ref(prototype=new_prototype))

    old_prototype = obj.prototype
    obj.prototype = new_prototype
    obj.save(update_fields=["prototype"])

    switch_config(obj=obj, new_prototype=new_prototype, old_prototype=old_prototype)


def _switch_components(cluster: Cluster, service: ClusterObject, new_component_prototype: Prototype) -> None:
    for component in ServiceComponent.objects.filter(cluster=cluster, service=service):
        try:
            new_comp_prototype = Prototype.objects.get(
                parent=new_component_prototype, type="component", name=component.prototype.name
            )
            _switch_object(obj=component, new_prototype=new_comp_prototype)
        except Prototype.DoesNotExist:
            component.delete()

    for component_prototype in Prototype.objects.filter(parent=new_component_prototype, type="component"):
        kwargs = {"cluster": cluster, "service": service, "prototype": component_prototype}
        if not ServiceComponent.objects.filter(**kwargs).exists():
            component = ServiceComponent.objects.create(**kwargs)
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

    if groups := GroupConfig.objects.filter(object_id=obj.id, object_type=ContentType.objects.get_for_model(obj)):
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
        obj.before_upgrade["services"] = [
            service.prototype.name for service in ClusterObject.objects.filter(cluster=obj)
        ]

    obj.save(update_fields=["before_upgrade"])


def _update_before_upgrade(obj: Cluster | HostProvider) -> None:
    _set_before_upgrade(obj=obj)

    if isinstance(obj, Cluster):
        for service in ClusterObject.objects.filter(cluster=obj):
            _set_before_upgrade(obj=service)
            for component in ServiceComponent.objects.filter(service=service, cluster=obj):
                _set_before_upgrade(obj=component)

    if isinstance(obj, HostProvider):
        for host in Host.objects.filter(provider=obj):
            _set_before_upgrade(obj=host)


class _BundleSwitch(ABC):
    def __init__(self, target: Cluster | HostProvider, upgrade: Upgrade):
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
            self._update_concerns()

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
    def _update_concerns(self) -> None:
        ...

    @abstractmethod
    def _get_objects_map_for_policy_update(self) -> dict[ADCMEntity, ContentType]:
        ...


class _ClusterBundleSwitch(_BundleSwitch):
    def __init__(self, target: Cluster, upgrade: Upgrade):
        super().__init__(target, upgrade)

    def _upgrade_children(self, old_prototype: Prototype, new_prototype: Prototype) -> None:
        for service in ClusterObject.objects.select_related("prototype").filter(cluster=self._target):
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
                    service = ClusterObject.objects.select_related("prototype").get(
                        cluster=self._target, prototype=proto_service
                    )
                except ClusterObject.DoesNotExist:
                    # this code was taken from service creation from `cm.api` skipping checks, concerns, etc.
                    check_license(prototype=proto_service)
                    service = ClusterObject.objects.create(cluster=self._target, prototype=proto_service)
                    service.config = init_object_config(proto=proto_service, obj=service)
                    service.save(update_fields=["config"])

                if not ServiceComponent.objects.filter(cluster=self._target, service=service).exists():
                    add_components_to_service(cluster=self._target, service=service)

    def _update_concerns(self) -> None:
        recalculate_concerns_on_cluster_upgrade(cluster=self._target)
        redistribute_issues_and_flags(topology=next(retrieve_clusters_topology((self._target.id,))))

    def _get_objects_map_for_policy_update(self) -> dict[Cluster | ClusterObject | ServiceComponent, ContentType]:
        obj_type_map = {self._target: ContentType.objects.get_for_model(Cluster)}

        service_content_type = ContentType.objects.get_for_model(ClusterObject)
        for service in ClusterObject.objects.filter(cluster=self._target):
            obj_type_map[service] = service_content_type

        component_content_type = ContentType.objects.get_for_model(ServiceComponent)
        for component in ServiceComponent.objects.filter(cluster=self._target):
            obj_type_map[component] = component_content_type

        return obj_type_map


class _HostProviderBundleSwitch(_BundleSwitch):
    def __init__(self, target: HostProvider, upgrade: Upgrade):
        super().__init__(target, upgrade)

    def _upgrade_children(self, old_prototype: Prototype, new_prototype: Prototype) -> None:  # noqa: ARG002
        for prototype in Prototype.objects.filter(bundle_id=self._upgrade.bundle_id, type="host"):
            for host in Host.objects.filter(provider=self._target, prototype__name=prototype.name):
                _switch_object(host, prototype)

    def _update_concerns(self) -> None:
        target_cod = CoreObjectDescriptor(id=self._target.id, type=orm_object_to_core_type(self._target))
        target_own_config_issue = retrieve_issue(owner=target_cod, cause=ConcernCause.CONFIG)
        if target_own_config_issue is None and object_configuration_has_issue(self._target):
            concern = create_issue(owner=target_cod, cause=ConcernCause.CONFIG)
            distribute_concern_on_related_objects(owner=target_cod, concern_id=concern.id)

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

        m2m_model.objects.bulk_create(objs=host_own_concerns_to_link)

        clusters_for_redistribution -= {None}
        if clusters_for_redistribution:
            for topology in retrieve_clusters_topology(cluster_ids=clusters_for_redistribution):
                redistribute_issues_and_flags(topology=topology)

    def _get_objects_map_for_policy_update(self) -> dict[HostProvider | Host, ContentType]:
        obj_type_map = {self._target: ContentType.objects.get_for_model(HostProvider)}

        host_content_type = ContentType.objects.get_for_model(Host)
        for host in Host.objects.filter(provider=self._target):
            obj_type_map[host] = host_content_type

        return obj_type_map
