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
    ActionHostGroup,
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
    MainObject,
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
from cm.services.mapping import check_nothing, set_host_component_mapping
from cm.status_api import notify_about_redistributed_concerns_from_maps, send_prototype_and_state_update_event
from cm.upgrade.before_upgrade_schemas import (
    ActionHostGroupBeforeUpgrade,
    BeforeUpgrade,
    ClusterBeforeUpgrade,
    ComponentBeforeUpgrade,
    ConfigHostGroupWithIdConfigBeforeUpgrade,
    DeletedObjectBeforeUpgrade,
    DeletedServiceBeforeUpgrade,
    HostBeforeUpgrade,
    ProviderBeforeUpgrade,
    ServiceBeforeUpgrade,
    ServiceHostComponentMapBeforeUpgrade,
)
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
    if isinstance(obj, Cluster):
        upgraded_bundle = obj.prototype.bundle
        before_upgrade = ClusterBeforeUpgrade(**obj.before_upgrade)
        old_bundle = Bundle.objects.get(pk=before_upgrade.bundle_id)
        old_proto = Prototype.objects.get(bundle=old_bundle, name=old_bundle.name, type=ObjectType.CLUSTER)
        _revert_object(obj=obj, old_proto=old_proto)

        for service_prototype in Prototype.objects.filter(bundle=old_bundle, type=ObjectType.SERVICE):
            service = Service.objects.filter(cluster=obj, prototype__name=service_prototype.name).first()
            if not service:
                continue

            _revert_object(obj=service, old_proto=service_prototype)
            for component_prototype in Prototype.objects.filter(
                bundle=old_bundle, parent=service_prototype, type=ObjectType.COMPONENT
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
                    _restore_deleted_objects(
                        obj=component,
                        before_upgrade=before_upgrade.service_deleted_components[service_prototype.name][
                            component_prototype.name
                        ],
                    )

        Service.objects.filter(cluster=obj, prototype__bundle=upgraded_bundle).delete()
        Component.objects.filter(cluster=obj, prototype__bundle=upgraded_bundle).delete()

        for service_name in before_upgrade.services:
            prototype = Prototype.objects.get(bundle=old_bundle, name=service_name, type=ObjectType.SERVICE)

            if not Service.objects.filter(prototype=prototype, cluster=obj).exists():
                service = add_service_to_cluster(cluster=obj, proto=prototype)
                _restore_deleted_objects(obj=service, before_upgrade=before_upgrade.deleted_services[service.name])

                for component in service.components.all():
                    _restore_deleted_objects(
                        obj=component,
                        before_upgrade=before_upgrade.deleted_services[service_name].components[component.name],
                    )

        host_comp_list = []
        for hostcomponent in before_upgrade.hc:
            host = Host.objects.get(fqdn=hostcomponent.host, cluster=obj)
            service = Service.objects.get(prototype__name=hostcomponent.service, cluster=obj)
            component = Component.objects.get(
                prototype__name=hostcomponent.component,
                cluster=obj,
                service=service,
            )
            host_comp_list.append((service, host, component))

        new_mapping = (
            HostComponentEntry(host_id=host.id, component_id=component.id) for (_, host, component) in host_comp_list
        )
        set_host_component_mapping(
            cluster_id=obj.id, bundle_id=old_proto.bundle_id, new_mapping=new_mapping, checks_func=check_nothing
        )

    if isinstance(obj, Provider):
        before_upgrade = ProviderBeforeUpgrade(**obj.before_upgrade)
        old_bundle = Bundle.objects.get(pk=before_upgrade.bundle_id)
        old_proto = Prototype.objects.get(bundle=old_bundle, name=old_bundle.name, type=ObjectType.PROVIDER)
        _revert_object(obj=obj, old_proto=old_proto)

        for host in Host.objects.filter(provider=obj):
            old_host_proto = Prototype.objects.get(bundle=old_bundle, type=ObjectType.HOST, name=host.prototype.name)
            _revert_object(obj=host, old_proto=old_host_proto)


def _restore_deleted_objects(
    obj: Service | Component, before_upgrade: DeletedObjectBeforeUpgrade | DeletedServiceBeforeUpgrade
) -> None:
    obj.state = before_upgrade.state

    if before_upgrade.config is not None:
        save_object_config(
            object_config=obj.config,
            config=before_upgrade.config.data,
            attr=before_upgrade.config.attributes,
            description="revert_upgrade",
        )

    obj.save(update_fields=["state", "config"])

    for group_name, group in before_upgrade.config_host_groups.items():
        config_host_group = ConfigHostGroup.objects.create(
            name=group_name,
            description="revert_upgrade",
            object_id=obj.id,
            object_type=ContentType.objects.get_for_model(obj),
        )
        config_host_group.hosts.set(Host.objects.filter(fqdn__in=group.hosts))
        save_object_config(
            object_config=config_host_group.config,
            config=group.config.data,
            attr=group.config.attributes,
            description="revert_upgrade",
        )

    for group_name, group in before_upgrade.action_host_groups.items():
        # Here you need to use the service layer.
        # But the current implementation is not ready. Since we have a lot of checks, as well as
        # the order in which the objects are prepared, it matters.
        action_host_group = ActionHostGroup.objects.create(
            name=group_name,
            description="revert_upgrade",
            object_id=obj.id,
            object_type=ContentType.objects.get_for_model(obj),
        )
        action_host_group.hosts.set(Host.objects.filter(fqdn__in=group.hosts))


def _switch_object(obj: Host | Service, new_prototype: Prototype) -> None:
    logger.info("upgrade switch from %s to %s", proto_ref(prototype=obj.prototype), proto_ref(prototype=new_prototype))

    old_prototype = obj.prototype
    obj.prototype = new_prototype
    obj.save(update_fields=["prototype"])

    switch_config(obj=obj, new_prototype=new_prototype, old_prototype=old_prototype)


def _switch_components(
    cluster: Cluster, service: Service, new_component_prototype: Prototype
) -> dict[str, DeletedObjectBeforeUpgrade]:
    before_upgrade_deleted_components = {}

    for component in Component.objects.filter(cluster=cluster, service=service):
        try:
            new_comp_prototype = Prototype.objects.get(
                parent=new_component_prototype, type="component", name=component.prototype.name
            )
            _switch_object(obj=component, new_prototype=new_comp_prototype)
        except Prototype.DoesNotExist:
            before_upgrade_deleted_components[component.prototype.name] = _get_before_upgrade_for_deleted_object(
                object_before_upgrade=component.before_upgrade
            )
            component.delete()

    for component_prototype in Prototype.objects.filter(parent=new_component_prototype, type="component"):
        kwargs = {"cluster": cluster, "service": service, "prototype": component_prototype}
        if not Component.objects.filter(**kwargs).exists():
            component = Component.objects.create(**kwargs)
            make_object_config(obj=component, prototype=component_prototype)

    return before_upgrade_deleted_components


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


def _revert_object(obj: MainObject, old_proto: Prototype) -> None:
    if obj.prototype == old_proto:
        return

    obj.prototype = old_proto

    if "config_id" in obj.before_upgrade and obj.before_upgrade["config_id"]:
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


def _set_before_upgrade(obj: MainObject, before_upgrade: BeforeUpgrade) -> None:
    before_upgrade.state = obj.state

    if obj.config:
        before_upgrade.config_id = obj.config.current

    if not isinstance(obj, Host):
        before_upgrade.config_host_groups = {
            group.name: ConfigHostGroupWithIdConfigBeforeUpgrade(
                config_id=group.config.current,
                hosts=list(group.hosts.values_list("fqdn", flat=True)),
            )
            for group in obj.config_host_group.all()
        }

    if not isinstance(obj, Provider | Host):
        before_upgrade.action_host_groups = {
            group.name: ActionHostGroupBeforeUpgrade(hosts=list(group.hosts.values_list("fqdn", flat=True)))
            for group in obj.action_host_group.all()
        }

    if isinstance(obj, Cluster):
        before_upgrade.hc = [
            ServiceHostComponentMapBeforeUpgrade(
                service=service,
                component=component,
                host=host,
            )
            for service, component, host in obj.hostcomponent_set.values_list(
                "service__prototype__name", "component__prototype__name", "host__fqdn"
            )
        ]
        before_upgrade.services = list(
            obj.services.select_related("prototype").values_list("prototype__name", flat=True)
        )

    obj.before_upgrade = before_upgrade.model_dump()
    obj.save(update_fields=["before_upgrade"])


def _update_before_upgrade(obj: Cluster | Provider) -> None:
    if isinstance(obj, Cluster):
        _set_before_upgrade(obj=obj, before_upgrade=ClusterBeforeUpgrade(**obj.before_upgrade))

        for service in Service.objects.filter(cluster=obj):
            _set_before_upgrade(obj=service, before_upgrade=ServiceBeforeUpgrade())

            for component in Component.objects.filter(service=service, cluster=obj):
                _set_before_upgrade(obj=component, before_upgrade=ComponentBeforeUpgrade())

    if isinstance(obj, Provider):
        _set_before_upgrade(obj=obj, before_upgrade=ProviderBeforeUpgrade(**obj.before_upgrade))

        for host in Host.objects.filter(provider=obj):
            _set_before_upgrade(obj=host, before_upgrade=HostBeforeUpgrade())


def _get_before_upgrade_for_deleted_object(object_before_upgrade: dict) -> DeletedObjectBeforeUpgrade:
    before_upgrade = DeletedObjectBeforeUpgrade(state=object_before_upgrade["state"])

    config = None
    if object_before_upgrade["config_id"] is not None:
        config_log = ConfigLog.objects.get(id=object_before_upgrade["config_id"])
        config = {"data": config_log.config, "attributes": config_log.attr}

    config_host_groups = {}
    for group_name, group in object_before_upgrade["config_host_groups"].items():
        config_log = ConfigLog.objects.get(id=group["config_id"])
        config_host_groups[group_name] = {
            "config": {"data": config_log.config, "attributes": config_log.attr},
            "hosts": group["hosts"],
        }

    before_upgrade.config = config
    before_upgrade.config_host_groups = config_host_groups
    before_upgrade.action_host_groups = object_before_upgrade["action_host_groups"]

    return before_upgrade


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

        if added or removed:
            notify_about_redistributed_concerns_from_maps(added=added, removed=removed)

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
        update_before_upgrade_after_delete_service = False
        before_upgrade = ClusterBeforeUpgrade(**self._target.before_upgrade)

        for service in Service.objects.select_related("prototype").filter(cluster=self._target):
            check_license(prototype=service.prototype)
            try:
                new_service_prototype = Prototype.objects.get(
                    bundle_id=self._upgrade.bundle_id, type="service", name=service.prototype.name
                )
                check_license(prototype=new_service_prototype)
                _switch_object(obj=service, new_prototype=new_service_prototype)
                before_upgrade_deleted_components = _switch_components(
                    cluster=self._target, service=service, new_component_prototype=new_service_prototype
                )

                if before_upgrade_deleted_components:
                    update_before_upgrade_after_delete_service = True
                    before_upgrade.service_deleted_components[
                        service.prototype.name
                    ] = before_upgrade_deleted_components
            except Prototype.DoesNotExist:
                update_before_upgrade_after_delete_service = True
                delete_service_before_upgrade = DeletedServiceBeforeUpgrade(
                    **_get_before_upgrade_for_deleted_object(object_before_upgrade=service.before_upgrade).model_dump()
                )

                for component_name, component_before_upgrade in service.components.select_related(
                    "prototype"
                ).values_list("prototype__name", "before_upgrade"):
                    delete_service_before_upgrade.components[component_name] = _get_before_upgrade_for_deleted_object(
                        object_before_upgrade=component_before_upgrade
                    )

                before_upgrade.deleted_services[service.name] = delete_service_before_upgrade

                service.delete()

        if update_before_upgrade_after_delete_service:
            self._target.before_upgrade = before_upgrade.model_dump()
            self._target.save(update_fields=["before_upgrade"])

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
