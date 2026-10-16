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


from collections import defaultdict, deque
from dataclasses import dataclass
from functools import partial
from typing import Any

from core.config import ConfigService
from core.scenarios.config import ConfigScenarios
from core.types import ADCMCoreType, ClusterID, CoreObjectDescriptor
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.db.transaction import atomic
from rbac.models import Policy

from cm.converters import orm_object_to_core_descriptor, orm_object_to_core_type
from cm.legacy.api import check_license, proto_ref
from cm.legacy.services.cluster import retrieve_cluster_topology, retrieve_multiple_clusters_topology
from cm.legacy.services.concern import create_issue, retrieve_issue
from cm.legacy.services.concern.cases import recalculate_concerns_on_cluster_upgrade
from cm.legacy.services.concern.checks import object_configuration_has_issue
from cm.legacy.services.concern.distribution import (
    AffectedObjectConcernMap,
    distribute_concern_on_related_objects,
    redistribute_issues_and_flags,
)
from cm.legacy.upgrade.before_upgrade_schemas import (
    ClusterBeforeUpgrade,
    DeletedObjectBeforeUpgrade,
    DeletedServiceBeforeUpgrade,
)
from cm.legacy.utils import obj_ref
from cm.logger import logger
from cm.models import (
    ADCM,
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
from cm.transition.status import StatusScenarios

PolicyObject = Cluster | Service | Component | Provider | Host
ConcernMaps = tuple[AffectedObjectConcernMap, AffectedObjectConcernMap]


@dataclass(slots=True)
class BundleSwitch:
    """Switches cluster/provider (with its whole hierarchy) to the bundle of given upgrade"""

    config_service: ConfigService
    config_scenarios: ConfigScenarios
    status_scenarios: StatusScenarios

    def do(self, target: Cluster | Provider, upgrade: Upgrade) -> None:
        match target:
            case Cluster():
                switch_children = partial(self._switch_cluster_children, cluster=target, old_prototype=target.prototype)
                update_concerns = partial(self._update_cluster_concerns, cluster=target)
                retrieve_policy_objects = partial(_retrieve_cluster_policy_objects, cluster=target)
            case Provider():
                switch_children = partial(self._switch_hosts, provider=target)
                update_concerns = partial(self._update_provider_concerns, provider=target)
                retrieve_policy_objects = partial(_retrieve_provider_policy_objects, provider=target)

        with atomic():
            new_prototype = self._switch_prototype_and_config(target=target, upgrade=upgrade)
            switch_children(upgrade=upgrade)
            added, removed = update_concerns()
            _apply_policies(objects=retrieve_policy_objects())

        if added or removed:
            self.status_scenarios.notify_about_redistributed_concerns_from_maps(added=added, removed=removed)

        logger.info("upgrade %s OK to version %s", obj_ref(obj=target), new_prototype.version)

    def _switch_prototype_and_config(self, target: Cluster | Provider, upgrade: Upgrade) -> Prototype:
        old_prototype = target.prototype
        new_prototype = Prototype.objects.get(
            bundle_id=upgrade.bundle_id,  # pyright: ignore[reportAttributeAccessIssue]
            type__in=(ObjectType.CLUSTER, ObjectType.PROVIDER),
        )
        target.prototype = new_prototype
        target.save(update_fields=["prototype"])
        switch_config(
            obj=target,
            new_prototype=new_prototype,
            old_prototype=old_prototype,
            config_service=self.config_service,
            config_scenarios=self.config_scenarios,
        )

        target.refresh_from_db()

        return new_prototype

    def _switch_object(self, obj: Host | Service | Component, new_prototype: Prototype) -> None:
        logger.info(
            "upgrade switch from %s to %s", proto_ref(prototype=obj.prototype), proto_ref(prototype=new_prototype)
        )

        old_prototype = obj.prototype
        obj.prototype = new_prototype
        obj.save(update_fields=["prototype"])

        switch_config(
            obj=obj,
            new_prototype=new_prototype,
            old_prototype=old_prototype,
            config_service=self.config_service,
            config_scenarios=self.config_scenarios,
        )

    # Cluster

    def _switch_cluster_children(self, cluster: Cluster, upgrade: Upgrade, old_prototype: Prototype) -> None:
        self._switch_services(cluster=cluster, upgrade=upgrade)
        _remove_hostcomponent_of_missing_components(cluster=cluster, upgrade=upgrade)

        # cluster is already switched to new prototype
        if old_prototype.allow_maintenance_mode != cluster.prototype.allow_maintenance_mode:
            Host.objects.filter(cluster=cluster).update(maintenance_mode=MaintenanceMode.OFF)

        _remove_binds_of_missing_imports(cluster=cluster, upgrade=upgrade)

    def _update_cluster_concerns(self, cluster: Cluster) -> ConcernMaps:
        recalculate_concerns_on_cluster_upgrade(cluster=cluster, config_service=self.config_service)
        return redistribute_issues_and_flags(topology=retrieve_cluster_topology(cluster.pk))

    def _switch_services(self, cluster: Cluster, upgrade: Upgrade) -> None:
        """
        Switches services that are present in new bundle, removes the others.
        Removed objects (services and components) are recorded in cluster's `before_upgrade`.
        """

        update_before_upgrade_after_delete_service = False
        before_upgrade = ClusterBeforeUpgrade(**cluster.before_upgrade)

        for service in Service.objects.select_related("prototype").filter(cluster=cluster):
            check_license(prototype=service.prototype)
            try:
                new_service_prototype = Prototype.objects.get(
                    bundle_id=upgrade.bundle_id,  # pyright: ignore[reportAttributeAccessIssue]
                    type="service",
                    name=service.prototype.name,
                )
            except Prototype.DoesNotExist:
                update_before_upgrade_after_delete_service = True
                deleted_service = DeletedServiceBeforeUpgrade(
                    **_get_before_upgrade_for_deleted_object(object_before_upgrade=service.before_upgrade).model_dump()
                )

                for component_name, component_before_upgrade in service.components.select_related(  # pyright: ignore
                    "prototype"
                ).values_list("prototype__name", "before_upgrade"):
                    deleted_service.components[component_name] = _get_before_upgrade_for_deleted_object(
                        object_before_upgrade=component_before_upgrade
                    )

                before_upgrade.deleted_services[service.name] = deleted_service

                service.delete()
                continue

            check_license(prototype=new_service_prototype)
            self._switch_object(obj=service, new_prototype=new_service_prototype)
            deleted_components = self._switch_components(
                cluster=cluster, service=service, new_service_prototype=new_service_prototype
            )

            if deleted_components:
                update_before_upgrade_after_delete_service = True
                before_upgrade.service_deleted_components[service.prototype.name] = deleted_components

        if update_before_upgrade_after_delete_service:
            cluster.before_upgrade = before_upgrade.model_dump()
            cluster.save(update_fields=["before_upgrade"])

    def _switch_components(
        self, cluster: Cluster, service: Service, new_service_prototype: Prototype
    ) -> dict[str, DeletedObjectBeforeUpgrade]:
        """Switches/removes existing components of service and creates the ones that are new in bundle"""

        deleted_components: dict[str, DeletedObjectBeforeUpgrade] = {}

        for component in Component.objects.filter(cluster=cluster, service=service):
            try:
                new_component_prototype = Prototype.objects.get(
                    parent=new_service_prototype, type="component", name=component.prototype.name
                )
            except Prototype.DoesNotExist:
                deleted_components[component.prototype.name] = _get_before_upgrade_for_deleted_object(
                    object_before_upgrade=component.before_upgrade
                )
                component.delete()
                continue

            self._switch_object(obj=component, new_prototype=new_component_prototype)

        for component_prototype in Prototype.objects.filter(parent=new_service_prototype, type="component"):
            if not Component.objects.filter(cluster=cluster, service=service, prototype=component_prototype).exists():
                component = Component.objects.create(
                    cluster_id=service.cluster_id,  # pyright: ignore[reportAttributeAccessIssue]
                    service=service,
                    prototype=component_prototype,
                )
                self.config_service.create_initial_configuration_if_required(
                    owner=orm_object_to_core_descriptor(component)
                )

        return deleted_components

    # Provider

    def _switch_hosts(self, provider: Provider, upgrade: Upgrade) -> None:
        for prototype in Prototype.objects.filter(bundle_id=upgrade.bundle_id, type="host"):  # pyright: ignore[reportAttributeAccessIssue]
            for host in Host.objects.filter(provider=provider, prototype__name=prototype.name):
                self._switch_object(obj=host, new_prototype=prototype)

    def _update_provider_concerns(self, provider: Provider) -> ConcernMaps:
        added: AffectedObjectConcernMap = defaultdict(lambda: defaultdict(set))
        # kept as plain dict as it was in legacy implementation
        removed: AffectedObjectConcernMap = {}

        self._add_own_config_issue_of_provider(provider=provider, added=added)
        clusters_for_redistribution = self._add_config_issues_of_hosts(provider=provider, added=added)

        if clusters_for_redistribution:
            for topology in retrieve_multiple_clusters_topology(cluster_ids=clusters_for_redistribution):
                added_, removed_ = redistribute_issues_and_flags(topology=topology)
                _merge_concern_maps(target=added, source=added_)
                _merge_concern_maps(target=removed, source=removed_)

        return added, removed

    def _add_own_config_issue_of_provider(self, provider: Provider, added: AffectedObjectConcernMap) -> None:
        provider_cod = CoreObjectDescriptor(id=provider.pk, type=orm_object_to_core_type(provider))
        if retrieve_issue(owner=provider_cod, cause=ConcernCause.CONFIG) is not None:
            return

        if not object_configuration_has_issue(provider, config_service=self.config_service):
            return

        concern = create_issue(owner=provider_cod, cause=ConcernCause.CONFIG)
        related_objects = distribute_concern_on_related_objects(owner=provider_cod, concern_id=concern.pk)
        for core_type, object_ids in related_objects.items():
            for object_id in object_ids:
                added[core_type][object_id].add(concern.pk)

    def _add_config_issues_of_hosts(self, provider: Provider, added: AffectedObjectConcernMap) -> set[ClusterID]:
        """Creates CONFIG issues on hosts that don't have one yet, returns IDs of clusters these hosts are in"""

        clusters_for_redistribution: set[ClusterID] = set()
        m2m_model = Host.concerns.through
        host_own_concerns_to_link: deque[Model] = deque()

        for host in (
            Host.objects.select_related("prototype__bundle")
            .filter(provider=provider)
            .exclude(
                id__in=ConcernItem.objects.values_list("owner_id", flat=True).filter(
                    owner_type=ContentType.objects.get_for_model(Host),
                    type=ConcernType.ISSUE,
                    cause=ConcernCause.CONFIG,
                )
            )
        ):
            if object_configuration_has_issue(host, config_service=self.config_service):
                concern = create_issue(
                    owner=CoreObjectDescriptor(id=host.pk, type=ADCMCoreType.HOST), cause=ConcernCause.CONFIG
                )
                clusters_for_redistribution.add(host.cluster_id)  # pyright: ignore[reportAttributeAccessIssue]
                host_own_concerns_to_link.append(m2m_model(host_id=host.pk, concernitem_id=concern.pk))
                added[ADCMCoreType.HOST][host.pk].add(concern.pk)

        m2m_model.objects.bulk_create(objs=host_own_concerns_to_link)

        return clusters_for_redistribution - {None}


def switch_config(
    obj: Cluster | Service | Component | Provider | Host | ADCM,
    new_prototype: Prototype,
    old_prototype: Prototype,
    config_service: ConfigService,
    config_scenarios: ConfigScenarios,
) -> None:
    """Adapts configuration of `obj` (already switched to `new_prototype`) from `old_prototype` specification"""

    specs_and_defaults = config_service.retrieve_specifications_by_prototypes_with_defaults(
        prototypes=(new_prototype.pk, old_prototype.pk)
    )
    old = specs_and_defaults[old_prototype.pk]
    new = specs_and_defaults[new_prototype.pk]

    new_spec, _ = new
    if new_spec.is_empty:
        _remove_config_host_groups(obj=obj)

    config_scenarios.switch_configuration(owner=orm_object_to_core_descriptor(obj), old=old, new=new)


def _remove_config_host_groups(obj: Cluster | Service | Component | Provider | Host | ADCM) -> None:
    chg_qs = ConfigHostGroup.objects.filter(object_id=obj.pk, object_type=ContentType.objects.get_for_model(obj))
    if chg_qs.exists():
        repr_ = ", ".join(f"<ConfigHostGroup #{chg.pk} {chg.name}>" for chg in chg_qs)
        logger.warning(f"Removing configuration host groups: {repr_} of <{obj}> without configuration")
        chg_qs.delete()


def _apply_policies(objects: dict[PolicyObject, ContentType]) -> None:
    for policy_object, content_type in objects.items():
        for policy in Policy.objects.filter(object__object_id=policy_object.pk, object__content_type=content_type):
            policy.apply()


# Cluster


def _retrieve_cluster_policy_objects(cluster: Cluster) -> dict[PolicyObject, ContentType]:
    objects: dict[PolicyObject, ContentType] = {cluster: ContentType.objects.get_for_model(Cluster)}

    service_content_type = ContentType.objects.get_for_model(Service)
    for service in Service.objects.filter(cluster=cluster):
        objects[service] = service_content_type

    component_content_type = ContentType.objects.get_for_model(Component)
    for component in Component.objects.filter(cluster=cluster):
        objects[component] = component_content_type

    return objects


def _get_before_upgrade_for_deleted_object(object_before_upgrade: dict[str, Any]) -> DeletedObjectBeforeUpgrade:
    before_upgrade = DeletedObjectBeforeUpgrade(state=object_before_upgrade["state"])  # pyright: ignore[reportCallIssue]

    config = None
    if object_before_upgrade["config_id"] is not None:
        config_log = ConfigLog.objects.get(id=object_before_upgrade["config_id"])
        config = {"data": config_log.config, "attributes": config_log.attr}

    config_host_groups: dict[str, dict[str, Any]] = {}
    for group_name, group in object_before_upgrade["config_host_groups"].items():
        config_log = ConfigLog.objects.get(id=group["config_id"])
        config_host_groups[group_name] = {
            "config": {"data": config_log.config, "attributes": config_log.attr},
            "hosts": group["hosts"],
        }

    before_upgrade.config = config  # pyright: ignore[reportAttributeAccessIssue]
    before_upgrade.config_host_groups = config_host_groups  # pyright: ignore[reportAttributeAccessIssue]
    before_upgrade.action_host_groups = object_before_upgrade["action_host_groups"]

    return before_upgrade


def _remove_hostcomponent_of_missing_components(cluster: Cluster, upgrade: Upgrade) -> None:
    existing_names: set[tuple[str, str]] = set(
        Prototype.objects.values_list("parent__name", "name").filter(
            bundle_id=upgrade.bundle_id,  # pyright: ignore[reportAttributeAccessIssue]
            type="component",
        )
    )
    entries_to_delete: deque[int] = deque()
    for hc_id, service_name, component_name in HostComponent.objects.values_list(
        "id", "service__prototype__name", "component__prototype__name"
    ).filter(cluster=cluster):
        if (service_name, component_name) not in existing_names:
            entries_to_delete.append(hc_id)

    HostComponent.objects.filter(id__in=entries_to_delete).delete()


def _remove_binds_of_missing_imports(cluster: Cluster, upgrade: Upgrade) -> None:
    # TODO: this copy from '_check_upgrade_import' function without checks. Need refactor
    #  Fix for ADCM-7888 in release 2.11.0
    for cbind in ClusterBind.objects.filter(cluster=cluster):
        export_obj = cbind.source_service if cbind.source_service else cbind.source_cluster
        import_obj = cbind.service if cbind.service else cbind.cluster

        try:
            prototype = Prototype.objects.get(
                bundle=upgrade.bundle,
                name=import_obj.prototype.name,
                type=import_obj.prototype.type,
            )
        except Prototype.DoesNotExist:
            continue

        try:
            PrototypeImport.objects.get(prototype=prototype, name=export_obj.prototype.name)
        except PrototypeImport.DoesNotExist:
            cbind.delete()


# Provider


def _retrieve_provider_policy_objects(provider: Provider) -> dict[PolicyObject, ContentType]:
    objects: dict[PolicyObject, ContentType] = {provider: ContentType.objects.get_for_model(Provider)}

    host_content_type = ContentType.objects.get_for_model(Host)
    for host in Host.objects.filter(provider=provider):
        objects[host] = host_content_type

    return objects


def _merge_concern_maps(target: AffectedObjectConcernMap, source: AffectedObjectConcernMap) -> None:
    for core_type, entries in source.items():
        for object_id, concern_ids in entries.items():
            target[core_type][object_id].update(concern_ids)
