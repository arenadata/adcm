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
from dataclasses import dataclass
from functools import partial
from typing import Callable, Generic, TypeVar

from core.cluster.types import HostComponentEntry
from core.types import ADCMCoreType, ClusterID, CoreObjectDescriptor
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from rbac.models import Policy
import core

from cm.adcm_config.utils import proto_ref
from cm.api import check_license
from cm.config.repo import convert_attr_to_adcm_meta
from cm.converters import orm_object_to_core_descriptor, orm_object_to_core_type
from cm.logger import logger
from cm.models import (
    Bundle,
    Cluster,
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
from cm.services.mapping import check_nothing, set_host_component_mapping
from cm.status_api import notify_about_redistributed_concerns_from_maps
from cm.upgrade.before_upgrade_schemas import (
    ClusterBeforeUpgrade,
    DeletedObjectBeforeUpgrade,
    DeletedServiceBeforeUpgrade,
    ProviderBeforeUpgrade,
)
from cm.utils import obj_ref

OT = TypeVar("OT", Cluster, Provider)
MT = TypeVar("MT")

# COPIED FROM cm.upgrade.base FOR ADCM-7093
# and altered for config rework purposes


# todo totally BS class, never write new code with it,
#  this whole thing requires rethinking and restructuring
@dataclass(slots=True)
class SwitchRevertCallbacks:
    add_component_to_service: Callable[[Service, Prototype], Component]
    add_service_to_cluster: Callable[[Cluster, Prototype], Service]


def bundle_switch(
    obj: Cluster | Provider,
    upgrade: Upgrade,
    callbacks: SwitchRevertCallbacks,
    config_service: core.config.ConfigService,
) -> None:
    if isinstance(obj, Cluster):
        switch = _ClusterBundleSwitch(target=obj, upgrade=upgrade, callbacks=callbacks, config_service=config_service)
    elif isinstance(obj, Provider):
        switch = _ProviderBundleSwitch(target=obj, upgrade=upgrade, callbacks=callbacks, config_service=config_service)

    switch.perform()


def bundle_revert(
    obj: Cluster | Provider, callbacks: SwitchRevertCallbacks, config_service: core.config.ConfigService
) -> None:
    if isinstance(obj, Cluster):
        upgraded_bundle = obj.prototype.bundle
        before_upgrade = ClusterBeforeUpgrade(**obj.before_upgrade)
        old_bundle = Bundle.objects.get(pk=before_upgrade.bundle_id)
        old_proto = Prototype.objects.get(bundle=old_bundle, name=old_bundle.name, type=ObjectType.CLUSTER)
        _revert_object(obj=obj, old_proto=old_proto, config_service=config_service)

        for service_prototype in Prototype.objects.filter(bundle=old_bundle, type=ObjectType.SERVICE):
            service = Service.objects.filter(cluster=obj, prototype__name=service_prototype.name).first()
            if not service:
                continue

            _revert_object(obj=service, old_proto=service_prototype, config_service=config_service)
            for component_prototype in Prototype.objects.filter(
                bundle=old_bundle, parent=service_prototype, type=ObjectType.COMPONENT
            ):
                component = Component.objects.filter(
                    cluster=obj,
                    service=service,
                    prototype__name=component_prototype.name,
                ).first()

                if component:
                    _revert_object(obj=component, old_proto=component_prototype, config_service=config_service)
                else:
                    component = callbacks.add_component_to_service(service, component_prototype)
                    _restore_deleted_objects(
                        obj=component,
                        before_upgrade=before_upgrade.service_deleted_components[service_prototype.name][
                            component_prototype.name
                        ],
                        config_service=config_service,
                    )

        Service.objects.filter(cluster=obj, prototype__bundle=upgraded_bundle).delete()
        Component.objects.filter(cluster=obj, prototype__bundle=upgraded_bundle).delete()

        for service_name in before_upgrade.services:
            prototype = Prototype.objects.get(bundle=old_bundle, name=service_name, type=ObjectType.SERVICE)

            if not Service.objects.filter(prototype=prototype, cluster=obj).exists():
                service = callbacks.add_service_to_cluster(obj, prototype)
                _restore_deleted_objects(
                    obj=service,
                    before_upgrade=before_upgrade.deleted_services[service.name],
                    config_service=config_service,
                )

                for component in service.components.all():  # pyright: ignore [reportAttributeAccessIssue]
                    _restore_deleted_objects(
                        obj=component,
                        before_upgrade=before_upgrade.deleted_services[service_name].components[component.name],
                        config_service=config_service,
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
            cluster_id=obj.pk,
            bundle_id=old_proto.bundle_id,  # pyright: ignore [reportAttributeAccessIssue]
            new_mapping=new_mapping,
            checks_func=check_nothing,
        )

    if isinstance(obj, Provider):
        before_upgrade = ProviderBeforeUpgrade(**obj.before_upgrade)
        old_bundle = Bundle.objects.get(pk=before_upgrade.bundle_id)
        old_proto = Prototype.objects.get(bundle=old_bundle, name=old_bundle.name, type=ObjectType.PROVIDER)
        _revert_object(obj=obj, old_proto=old_proto, config_service=config_service)

        for host in Host.objects.filter(provider=obj):
            old_host_proto = Prototype.objects.get(bundle=old_bundle, type=ObjectType.HOST, name=host.prototype.name)
            _revert_object(obj=host, old_proto=old_host_proto, config_service=config_service)


class _BundleSwitch(ABC, Generic[OT, MT]):
    def __init__(
        self, target: OT, upgrade: Upgrade, callbacks: SwitchRevertCallbacks, config_service: core.config.ConfigService
    ):
        self._target = target
        self._upgrade = upgrade
        self._call = callbacks
        self._config_service = config_service

    def perform(self) -> None:
        with transaction.atomic():
            old_prototype = self._target.prototype
            new_prototype = Prototype.objects.get(
                bundle_id=self._upgrade.bundle_id,  # pyright: ignore [reportAttributeAccessIssue]
                type__in=(ObjectType.CLUSTER, ObjectType.PROVIDER),
            )
            self._target.prototype = new_prototype
            self._target.save(update_fields=["prototype"])
            switch_config(
                obj=self._target,
                new_prototype=new_prototype,
                old_prototype=old_prototype,
                config_service=self._config_service,
            )

            self._target.refresh_from_db()

            self._upgrade_children(old_prototype=old_prototype, new_prototype=new_prototype)
            added, removed = self._update_concerns()

            for policy_object, content_type in self._get_objects_map_for_policy_update().items():
                for policy in Policy.objects.filter(
                    object__object_id=policy_object.id,  # pyright: ignore [reportAttributeAccessIssue]
                    object__content_type=content_type,
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
    def _get_objects_map_for_policy_update(self) -> dict[MT, ContentType]:
        ...


class _ClusterBundleSwitch(_BundleSwitch[Cluster, Cluster | Service | Component]):
    def _upgrade_children(self, old_prototype: Prototype, new_prototype: Prototype) -> None:
        update_before_upgrade_after_delete_service = False
        before_upgrade = ClusterBeforeUpgrade(**self._target.before_upgrade)

        for service in Service.objects.select_related("prototype").filter(cluster=self._target):
            check_license(prototype=service.prototype)
            try:
                new_service_prototype = Prototype.objects.get(
                    bundle_id=self._upgrade.bundle_id,  # pyright: ignore [reportAttributeAccessIssue]
                    type="service",
                    name=service.prototype.name,
                )
                check_license(prototype=new_service_prototype)
                _switch_object(obj=service, new_prototype=new_service_prototype, config_service=self._config_service)
                before_upgrade_deleted_components = _switch_components(
                    cluster=self._target,
                    service=service,
                    new_component_prototype=new_service_prototype,
                    callbacks=self._call,
                    config_service=self._config_service,
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

                for component_name, component_before_upgrade in service.components.select_related(  # pyright: ignore
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
                bundle_id=self._upgrade.bundle_id,  # pyright: ignore [reportAttributeAccessIssue]
                type="component",
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

        # As I understand from ADCM-6563 upgrade's action can't have hc_acl anymore,
        # so this whole case is irrelevant.
        # Left until usage proof or refactoring.
        #
        # if self._upgrade.action and self._upgrade.action.hostcomponentmap:
        #    logger.info("update component from %s after upgrade with hc_acl", self._target)
        #    services_in_new_hc = set(map(itemgetter("service"), self._upgrade.action.hostcomponentmap))
        #    for proto_service in Prototype.objects.filter(
        #        type="service",
        #        bundle_id=self._upgrade.bundle_id,
        #        name__in=services_in_new_hc,
        #    ):
        #        # probably operations below can be performed in bulk for speed improvement
        #        try:
        #            service = Service.objects.select_related("prototype").get(
        #                cluster=self._target, prototype=proto_service
        #            )
        #        except Service.DoesNotExist:
        #            check_license(prototype=proto_service)
        #            # todo is it a case?
        #            #  previously was done differently:
        #            #  "this code was taken from service creation from `cm.api` skipping checks, concerns, etc.",
        #            #  now it's full "use case"
        #            service = self._call.add_service_to_cluster(self._target, proto_service)

        #        if not Component.objects.filter(cluster=self._target, service=service).exists():
        #            add_components_to_service(cluster=self._target, service=service)

    def _update_concerns(self) -> tuple[AffectedObjectConcernMap, AffectedObjectConcernMap]:
        recalculate_concerns_on_cluster_upgrade(cluster=self._target)
        return redistribute_issues_and_flags(topology=retrieve_cluster_topology(self._target.pk))

    def _get_objects_map_for_policy_update(self) -> dict[Cluster | Service | Component, ContentType]:
        obj_type_map: dict[Cluster | Service | Component, ContentType] = {
            self._target: ContentType.objects.get_for_model(Cluster)
        }

        service_content_type = ContentType.objects.get_for_model(Service)
        for service in Service.objects.filter(cluster=self._target):
            obj_type_map[service] = service_content_type

        component_content_type = ContentType.objects.get_for_model(Component)
        for component in Component.objects.filter(cluster=self._target):
            obj_type_map[component] = component_content_type

        return obj_type_map


class _ProviderBundleSwitch(_BundleSwitch):
    def _upgrade_children(self, old_prototype: Prototype, new_prototype: Prototype) -> None:  # noqa: ARG002
        for prototype in Prototype.objects.filter(bundle_id=self._upgrade.bundle_id, type="host"):  # pyright: ignore [reportAttributeAccessIssue]
            for host in Host.objects.filter(provider=self._target, prototype__name=prototype.name):
                _switch_object(host, prototype, config_service=self._config_service)

    def _update_concerns(self) -> tuple[AffectedObjectConcernMap, AffectedObjectConcernMap]:
        added, removed = defaultdict(lambda: defaultdict(set)), {}
        target_cod = CoreObjectDescriptor(id=self._target.id, type=orm_object_to_core_type(self._target))
        target_own_config_issue = retrieve_issue(owner=target_cod, cause=ConcernCause.CONFIG)
        if target_own_config_issue is None and object_configuration_has_issue(self._target):
            concern = create_issue(owner=target_cod, cause=ConcernCause.CONFIG)
            related_objects = distribute_concern_on_related_objects(owner=target_cod, concern_id=concern.pk)
            for core_type, object_ids in related_objects.items():
                for object_id in object_ids:
                    added[core_type][object_id].add(concern.pk)

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
                    owner=CoreObjectDescriptor(id=host.pk, type=ADCMCoreType.HOST), cause=ConcernCause.CONFIG
                )
                clusters_for_redistribution.add(host.cluster_id)  # pyright: ignore [reportAttributeAccessIssue]
                host_own_concerns_to_link.append(m2m_model(host_id=host.pk, concernitem_id=concern.pk))
                added[ADCMCoreType.HOST][host.pk].add(concern.pk)

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

        return added, removed  # pyright: ignore

    def _get_objects_map_for_policy_update(self) -> dict[Provider | Host, ContentType]:
        obj_type_map = {self._target: ContentType.objects.get_for_model(Provider)}

        host_content_type = ContentType.objects.get_for_model(Host)
        for host in Host.objects.filter(provider=self._target):
            obj_type_map[host] = host_content_type

        return obj_type_map


def _switch_object(
    obj: Host | Service | Component, new_prototype: Prototype, config_service: core.config.ConfigService
) -> None:
    logger.info("upgrade switch from %s to %s", proto_ref(prototype=obj.prototype), proto_ref(prototype=new_prototype))

    old_prototype = obj.prototype
    obj.prototype = new_prototype
    obj.save(update_fields=["prototype"])

    switch_config(obj=obj, new_prototype=new_prototype, old_prototype=old_prototype, config_service=config_service)


def _switch_components(
    cluster: Cluster,
    service: Service,
    new_component_prototype: Prototype,
    callbacks: SwitchRevertCallbacks,
    config_service: core.config.ConfigService,
) -> dict[str, DeletedObjectBeforeUpgrade]:
    before_upgrade_deleted_components = {}

    for component in Component.objects.filter(cluster=cluster, service=service):
        try:
            new_comp_prototype = Prototype.objects.get(
                parent=new_component_prototype, type="component", name=component.prototype.name
            )
            _switch_object(obj=component, new_prototype=new_comp_prototype, config_service=config_service)
        except Prototype.DoesNotExist:
            before_upgrade_deleted_components[component.prototype.name] = _get_before_upgrade_for_deleted_object(
                object_before_upgrade=component.before_upgrade
            )
            component.delete()

    for component_prototype in Prototype.objects.filter(parent=new_component_prototype, type="component"):
        kwargs = {"cluster": cluster, "service": service, "prototype": component_prototype}
        if not Component.objects.filter(**kwargs).exists():
            callbacks.add_component_to_service(service, component_prototype)

    return before_upgrade_deleted_components


def _get_before_upgrade_for_deleted_object(object_before_upgrade: dict) -> DeletedObjectBeforeUpgrade:
    before_upgrade = DeletedObjectBeforeUpgrade(state=object_before_upgrade["state"])  # pyright: ignore [reportCallIssue]

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

    before_upgrade.config = config  # pyright: ignore [reportAttributeAccessIssue]
    before_upgrade.config_host_groups = config_host_groups
    before_upgrade.action_host_groups = object_before_upgrade["action_host_groups"]

    return before_upgrade


def _revert_object(obj: MainObject, old_proto: Prototype, config_service: core.config.ConfigService) -> None:
    if obj.prototype == old_proto:
        return

    obj.prototype = old_proto
    obj.state = obj.before_upgrade["state"]
    obj.before_upgrade = {"state": None}
    obj.save(update_fields=["prototype", "state", "before_upgrade"])

    if "config_id" in obj.before_upgrade and (config_id := obj.before_upgrade["config_id"]):
        owner = orm_object_to_core_descriptor(obj)
        config = config_service.retrieve_configurations_by_id(configurations=(config_id,))[config_id]
        _restore_config_of_main_object(owner=owner, config=config, config_service=config_service)


def _restore_deleted_objects(
    obj: Service | Component,
    before_upgrade: DeletedObjectBeforeUpgrade | DeletedServiceBeforeUpgrade,
    config_service: core.config.ConfigService,
) -> None:
    obj.state = before_upgrade.state
    obj.save(update_fields=["state"])

    owner = orm_object_to_core_descriptor(obj)

    if before_upgrade.config is not None:
        config = _to_congifuration(
            raw_values=before_upgrade.config.data, raw_attributes=before_upgrade.config.attributes
        )
        _restore_config_of_main_object(owner=owner, config_service=config_service, config=config)

    for group_name, group in before_upgrade.config_host_groups.items():
        config_host_group = ConfigHostGroup.objects.create(
            name=group_name,
            description="revert_upgrade",
            object_id=obj.pk,
            object_type=ContentType.objects.get_for_model(obj),
        )
        config_host_group.hosts.set(Host.objects.filter(fqdn__in=group.hosts))

        if group.config:
            config = _to_congifuration(raw_values=group.config.data, raw_attributes=group.config.attributes)
            _restore_config_of_host_group(
                owner=owner, config_service=config_service, config=config, group_id=config_host_group.pk
            )


def _to_congifuration(raw_values: dict, raw_attributes: dict) -> core.config.Configuration:
    meta_attributes = convert_attr_to_adcm_meta(raw_attributes)
    attributes = {
        key: core.config.Attributes(is_active=value.get("isActive"), is_synced=value.get("isSynchronized"))
        for key, value in meta_attributes.items()
    }
    return core.config.Configuration(values=raw_values, attributes=attributes)


def _restore_config_of_main_object(
    owner: CoreObjectDescriptor, config_service: core.config.ConfigService, config: core.config.Configuration
):
    description = "revert_upgrade"

    specification, _ = config_service.retrieve_specification(owner=owner)

    config_service.create_new_configuration_by_descriptor(configuration=config, description=description, owner=owner)
    configs_of_host_groups = config_service.retrieve_host_group_configurations(owner=owner)
    updated_host_group_configs = config_service.prepare_updated_configurations_of_host_groups(
        main=config, groups=configs_of_host_groups
    )
    for owner_group, updated_configuration in updated_host_group_configs.items():
        config_service.create_new_configuration_by_descriptor(
            configuration=updated_configuration, description=description, owner=owner_group
        )
    prepare_files = partial(
        config_service.prepare_file_parameter_values_on_fs,
        specification=specification,
    )

    # since we have no "fallback" mechanism for write failures, have to write files within transaction
    prepare_files(configuration=config, owner_prefix=core.config.files.build_config_prefix(owner))

    for owner_group, updated_configuration in updated_host_group_configs.items():
        group_file_prefix = core.config.files.build_config_host_group_prefix(owner=owner, group_id=owner_group.id)
        # since we have no "fallback" mechanism for write failures, have to write files within transaction
        prepare_files(configuration=updated_configuration, owner_prefix=group_file_prefix)


def _restore_config_of_host_group(
    owner: CoreObjectDescriptor,
    config_service: core.config.ConfigService,
    config: core.config.Configuration,
    group_id: int,
):
    description = "revert_upgrade"
    file_owner_prefix = core.config.files.build_config_host_group_prefix(owner=owner, group_id=group_id)

    specification, _ = config_service.retrieve_specification(owner=owner)
    owner_config = config_service.retrieve_current_configuration(owner=owner)

    # sync with changes from main config
    updated_configuration = config_service.prepare_updated_configurations_of_host_groups(
        main=owner_config, groups={0: config}
    )[0]

    config_service.create_new_configuration_by_descriptor(
        configuration=updated_configuration, description=description, owner=owner
    )

    config_service.prepare_file_parameter_values_on_fs(
        configuration=updated_configuration,
        specification=specification,
        owner_prefix=file_owner_prefix,
    )


def switch_config(
    obj: Cluster | Service | Component | Provider | Host,
    new_prototype: Prototype,
    old_prototype: Prototype,
    config_service: core.config.ConfigService,
):
    # todo cover case when new object has configuration
    #  ADCM-7319
    if not obj.config:
        return

    owner = orm_object_to_core_descriptor(obj)

    configuration = config_service.retrieve_current_configuration(owner=owner)

    specs_and_defaults = config_service.retrieve_specifications_by_prototypes_with_defaults(
        prototypes=(new_prototype.pk, old_prototype.pk)
    )

    old_spec, old_defaults = specs_and_defaults[old_prototype.pk]
    new_spec, new_defaults = specs_and_defaults[new_prototype.pk]

    result = core.config.operations.adapt_configuration_for_new_specification(
        configuration=configuration,
        specification=old_spec,
        defaults=old_defaults,
        new_specification=new_spec,
        new_defaults=new_defaults,
    )

    config = result.value

    config_service.create_new_configuration_by_descriptor(configuration=config, description="upgrade", owner=owner)
    configs_of_host_groups = config_service.retrieve_host_group_configurations(owner=owner)
    updated_host_group_configs = config_service.prepare_updated_configurations_of_host_groups(
        main=config, groups=configs_of_host_groups
    )
    for owner_group, updated_configuration in updated_host_group_configs.items():
        config_service.create_new_configuration_by_descriptor(
            configuration=updated_configuration, description="upgrade", owner=owner_group
        )
    prepare_files = partial(
        config_service.prepare_file_parameter_values_on_fs,
        specification=new_spec,
    )

    # since we have no "fallback" mechanism for write failures, have to write files within transaction
    prepare_files(configuration=config, owner_prefix=core.config.files.build_config_prefix(owner))

    for owner_group, updated_configuration in updated_host_group_configs.items():
        group_file_prefix = core.config.files.build_config_host_group_prefix(owner=owner, group_id=owner_group.id)
        # since we have no "fallback" mechanism for write failures, have to write files within transaction
        prepare_files(configuration=updated_configuration, owner_prefix=group_file_prefix)
