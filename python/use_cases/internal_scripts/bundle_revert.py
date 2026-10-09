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

from dataclasses import dataclass
from functools import partial
import traceback

from cm.converters import orm_object_to_core_descriptor
from cm.errors import AdcmEx
from cm.impl.config.convert import convert_attr_to_adcm_meta
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.concern import create_issue, retrieve_issue
from cm.legacy.services.concern.cases import object_imports_has_issue
from cm.legacy.services.concern.distribution import redistribute_issues_and_flags
from cm.legacy.services.job.run.executors import InternalScriptResult
from cm.legacy.services.mapping import check_nothing, set_host_component_mapping
from cm.legacy.upgrade.before_upgrade_schemas import (
    ClusterBeforeUpgrade,
    DeletedObjectBeforeUpgrade,
    DeletedServiceBeforeUpgrade,
    ProviderBeforeUpgrade,
)
from cm.logger import logger
from cm.models import (
    ActionHostGroup,
    Bundle,
    Cluster,
    Component,
    ConcernCause,
    ConfigHostGroup,
    Host,
    MainObject,
    ObjectType,
    Prototype,
    Provider,
    Service,
    TaskLog,
)
from cm.transition.status import StatusScenarios
from core.action import Task
from core.action.types import SimpleInternalScript
from core.cluster import ClusterService
from core.config import (
    Attributes,
    ConfigOperationError,
    ConfigService,
    Configuration,
    ConfigurationExtraInfo,
    Defaults,
    files,
    operations,
    spec,
)
from core.config.constants import SYSTEM_CONFIG_CREATOR
from core.legacy.cluster.types import HostComponentEntry
from core.result import Fail
from core.scenarios.cluster import BeforeUpgradeScenarios
from core.scenarios.config import ConfigScenarios, SpecWithDefaults
from core.types import (
    ADCMCoreType,
    ADCMHostGroupType,
    BundleID,
    ClusterHierarchyBeforeUpgradeBinds,
    ConfigHostGroupID,
    ConfigID,
    CoreObjectDescriptor,
    Descriptor,
    HostGroupDescriptor,
    JobID,
)
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.transaction import atomic
from rbac.roles import re_apply_policy_for_jobs

from use_cases.internal_scripts.common import build_result_message
from use_cases.transition.cluster.create import CreateServicesFromPrototypes

REVERT_DESCRIPTION = "revert_upgrade"


@dataclass(slots=True)
class RevertUpgrade:
    """Reverts cluster/provider (with its whole hierarchy) to the bundle it was upgraded from"""

    config_service: ConfigService
    config_scenarios: ConfigScenarios
    cluster_service: ClusterService
    before_upgrade_scenarios: BeforeUpgradeScenarios
    create_services: CreateServicesFromPrototypes

    def do(self, target: Cluster | Provider) -> None:
        old_bundle_id: BundleID
        old_prototype: Prototype

        with atomic():
            match target:
                case Cluster():
                    # `before_upgrade` (with binds) and upgraded bundle are captured before anything is reverted,
                    # because reverting an object resets its `before_upgrade` and prototype
                    before_upgrade, before_upgrade_binds = self._retrieve_cluster_before_upgrade(cluster=target)
                    old_bundle_id = before_upgrade.bundle_id
                    old_prototype = _retrieve_prototype_before_upgrade(
                        bundle_id=old_bundle_id, type_=ObjectType.CLUSTER
                    )
                    revert_children = partial(
                        self._revert_cluster_children,
                        cluster=target,
                        upgraded_bundle=target.prototype.bundle,
                        before_upgrade=before_upgrade,
                        before_upgrade_binds=before_upgrade_binds,
                    )
                case Provider():
                    old_bundle_id = ProviderBeforeUpgrade(**target.before_upgrade).bundle_id
                    old_prototype = _retrieve_prototype_before_upgrade(
                        bundle_id=old_bundle_id, type_=ObjectType.PROVIDER
                    )
                    revert_children = partial(self._revert_hosts, provider=target)

            self._revert_object(obj=target, old_prototype=old_prototype)
            revert_children(old_bundle_id=old_bundle_id)

    def _revert_object(self, obj: MainObject, old_prototype: Prototype) -> None:
        """Switches `obj` back to `old_prototype`, restores its state, config and CHGs from `before_upgrade`"""

        if obj.prototype == old_prototype:
            return

        previous_prototype_id = obj.prototype_id  # pyright: ignore[reportAttributeAccessIssue]
        new_prototype_id = old_prototype.pk

        obj.prototype = old_prototype
        obj.state = obj.before_upgrade["state"]
        obj.save(update_fields=["prototype", "state"])

        if "config_id" in obj.before_upgrade and (config_id := obj.before_upgrade["config_id"]):
            owner = orm_object_to_core_descriptor(obj)
            config = self.config_service.retrieve_configurations_by_id(configurations=(config_id,))[config_id]
            specs = self.config_service.retrieve_specifications_by_prototypes_with_defaults(
                prototypes=(previous_prototype_id, new_prototype_id)
            )
            # it is expected to be present since config_id is specified
            new_spec = specs[new_prototype_id]

            try:
                previous_spec = specs[previous_prototype_id]
            except KeyError:
                previous_spec = (spec.FullSpec(), Defaults())

            # Restore CHGs, collect existing before_upgrade configs in `before_upgrade_host_group_configs` and
            #   CHG descriptors to init a new config in `config_host_groups_to_initialize`
            chg_bu_config_map = _restore_config_host_groups(obj=obj)
            configs_by_id = self.config_service.retrieve_configurations_by_id(configurations=chg_bu_config_map.values())

            config_host_groups_to_initialize: list[HostGroupDescriptor] = []
            before_upgrade_host_group_configs: dict[HostGroupDescriptor, Configuration] = {}
            for chg_id, bu_config_id in chg_bu_config_map.items():
                chg_desc = HostGroupDescriptor(id=chg_id, type=ADCMHostGroupType.CONFIG)
                if bu_config_id in configs_by_id:
                    before_upgrade_host_group_configs[chg_desc] = configs_by_id[bu_config_id]
                else:
                    config_host_groups_to_initialize.append(chg_desc)

            self._restore_config_of_main_object_and_update_host_groups(
                owner=owner,
                config=config,
                new=new_spec,
                old=previous_spec,
                config_host_groups_to_initialize=config_host_groups_to_initialize,
                before_upgrade_host_group_configs=before_upgrade_host_group_configs,
            )

        obj.before_upgrade = {"state": None}
        obj.save(update_fields=["before_upgrade"])

    def _restore_deleted_objects(
        self,
        obj: Service | Component,
        before_upgrade: DeletedObjectBeforeUpgrade | DeletedServiceBeforeUpgrade,
    ) -> None:
        """Restores state, config, CHGs and AHGs of object deleted by switch and re-created by revert"""

        obj.state = before_upgrade.state
        obj.save(update_fields=["state"])

        owner = orm_object_to_core_descriptor(obj)

        if before_upgrade.config is not None:
            config = _to_configuration(
                raw_values=before_upgrade.config.data, raw_attributes=before_upgrade.config.attributes
            )
            self._restore_config_of_main_object(owner=owner, config=config)

        for group_name, group in before_upgrade.config_host_groups.items():
            config_host_group = ConfigHostGroup.objects.create(
                name=group_name,
                description=REVERT_DESCRIPTION,
                object_id=obj.pk,
                object_type=ContentType.objects.get_for_model(obj),
            )
            config_host_group.hosts.set(Host.objects.filter(fqdn__in=group.hosts))

            if group.config:
                config = _to_configuration(raw_values=group.config.data, raw_attributes=group.config.attributes)
                self._restore_config_of_host_group(owner=owner, config=config, group_id=config_host_group.pk)
            else:
                self.config_service.create_initial_configuration_of_host_group(
                    group=Descriptor(id=config_host_group.pk, type=ADCMHostGroupType.CONFIG),
                    owner=owner,
                )

        for group_name, group in before_upgrade.action_host_groups.items():
            # Here you need to use the service layer.
            # But the current implementation is not ready. Since we have a lot of checks, as well as
            # the order in which the objects are prepared, it matters.
            action_host_group = ActionHostGroup.objects.create(
                name=group_name,
                description=REVERT_DESCRIPTION,
                object_id=obj.pk,
                object_type=ContentType.objects.get_for_model(obj),
            )
            action_host_group.hosts.set(Host.objects.filter(fqdn__in=group.hosts))

    def _restore_config_of_main_object_and_update_host_groups(
        self,
        owner: CoreObjectDescriptor,
        config: Configuration,
        old: SpecWithDefaults,
        new: SpecWithDefaults,
        config_host_groups_to_initialize: list[HostGroupDescriptor],
        before_upgrade_host_group_configs: dict[HostGroupDescriptor, Configuration],
    ) -> None:
        old_spec, old_defaults = old
        new_spec, new_defaults = new
        update_for_new_spec = partial(
            operations.adapt_configuration_for_new_specification,
            specification=old_spec,
            defaults=old_defaults,
            new_specification=new_spec,
            new_defaults=new_defaults,
        )

        # CHGs without a usable `before_upgrade` config (recreated deleted groups, or groups whose
        # `before_upgrade` ConfigLog is gone): create a new initial config, then adapt it to the
        # specification being reverted to.
        initial_config_ids_of_host_groups = {
            group: self.config_service.create_initial_configuration_of_host_group(
                group=Descriptor(id=group.id, type=ADCMHostGroupType.CONFIG), owner=owner
            )
            for group in config_host_groups_to_initialize
        }
        initial_configs_of_host_groups = self.config_service.retrieve_configurations_by_id(
            configurations=initial_config_ids_of_host_groups.values()
        )
        adaptation_results = {
            group: update_for_new_spec(
                configuration=initial_configs_of_host_groups[config_id], include_synchronization=True
            )
            for group, config_id in initial_config_ids_of_host_groups.items()
        }
        adapted_configs_of_host_groups: dict[HostGroupDescriptor, Configuration] = {}
        for group, result in adaptation_results.items():
            if isinstance(result, Fail):
                raise ConfigOperationError(f"Failed to adapt configs of host groups: {str(result.value)}")

            adapted_configs_of_host_groups[group] = result.value

        # `before_upgrade` CHG configs are already stored against the specification we revert to,
        # so they need no adaptation.
        adapted_configs_of_host_groups.update(before_upgrade_host_group_configs)

        self.config_scenarios.save_encrypted_config_with_host_groups(
            owner=owner,
            encrypted_main_config=config,
            specification=new_spec,
            config_extra_info=ConfigurationExtraInfo(description=REVERT_DESCRIPTION, created_by=SYSTEM_CONFIG_CREATOR),
            host_group_configs=adapted_configs_of_host_groups,
        )

    def _restore_config_of_main_object(self, owner: CoreObjectDescriptor, config: Configuration) -> None:
        # create main config based on input
        self.config_service.create_new_configuration_by_descriptor(
            configuration=config,
            configuration_extra_info=ConfigurationExtraInfo(
                description=REVERT_DESCRIPTION, created_by=SYSTEM_CONFIG_CREATOR
            ),
            owner=owner,
        )

        specification = self.config_service.retrieve_specification(owner=owner)

        # since we have no "fallback" mechanism for write failures, have to write files within transaction
        self.config_service.prepare_file_parameter_values_on_fs(
            configuration=config, specification=specification, owner_prefix=files.build_config_prefix(owner)
        )

    def _restore_config_of_host_group(self, owner: CoreObjectDescriptor, config: Configuration, group_id: int) -> None:
        file_owner_prefix = files.build_config_host_group_prefix(owner=owner, group_id=group_id)

        specification = self.config_service.retrieve_specification(owner=owner)
        owner_config = self.config_service.retrieve_current_configuration(owner=owner)

        # sync with changes from main config
        updated_configuration = self.config_service.prepare_updated_configurations_of_host_groups(
            main=owner_config, groups={0: config}, specification=specification
        )[0]

        self.config_service.create_new_configuration_by_descriptor(
            configuration=updated_configuration,
            configuration_extra_info=ConfigurationExtraInfo(
                description=REVERT_DESCRIPTION, created_by=SYSTEM_CONFIG_CREATOR
            ),
            owner=Descriptor(id=group_id, type=ADCMHostGroupType.CONFIG),
        )

        self.config_service.prepare_file_parameter_values_on_fs(
            configuration=updated_configuration,
            specification=specification,
            owner_prefix=file_owner_prefix,
        )

    # Cluster

    def _retrieve_cluster_before_upgrade(
        self, cluster: Cluster
    ) -> tuple[ClusterBeforeUpgrade, ClusterHierarchyBeforeUpgradeBinds]:
        before_upgrade = ClusterBeforeUpgrade(**cluster.before_upgrade)
        before_upgrade_binds = self.cluster_service.repo.retrieve_hierarchy_before_upgrade_binds(cluster_id=cluster.pk)

        return before_upgrade, before_upgrade_binds

    def _revert_cluster_children(
        self,
        cluster: Cluster,
        old_bundle_id: BundleID,
        upgraded_bundle: Bundle,
        before_upgrade: ClusterBeforeUpgrade,
        before_upgrade_binds: ClusterHierarchyBeforeUpgradeBinds,
    ) -> None:
        self._revert_services(cluster=cluster, old_bundle_id=old_bundle_id, before_upgrade=before_upgrade)
        _delete_objects_of_upgraded_bundle(cluster=cluster, upgraded_bundle=upgraded_bundle)
        self._restore_services_deleted_by_switch(
            cluster=cluster, old_bundle_id=old_bundle_id, before_upgrade=before_upgrade
        )
        self._restore_hostcomponent(cluster=cluster, old_bundle_id=old_bundle_id, before_upgrade=before_upgrade)

        self.before_upgrade_scenarios.restore_binds(
            cluster=Descriptor(id=cluster.pk, type=ADCMCoreType.CLUSTER),
            before_upgrade_binds=before_upgrade_binds,
            prototype_imports=self.before_upgrade_scenarios.bundle_service.retrieve_prototype_imports(
                bundle_id=old_bundle_id
            ),
        )
        _add_import_issues(cluster=cluster)

    def _revert_services(self, cluster: Cluster, old_bundle_id: BundleID, before_upgrade: ClusterBeforeUpgrade) -> None:
        """
        Reverts services and components that exist in both bundles,
        re-creates components deleted by switch from services that are kept
        """

        for service_prototype in Prototype.objects.filter(bundle_id=old_bundle_id, type=ObjectType.SERVICE):
            service = Service.objects.filter(cluster=cluster, prototype__name=service_prototype.name).first()
            if not service:
                continue

            self._revert_object(obj=service, old_prototype=service_prototype)
            for component_prototype in Prototype.objects.filter(
                bundle_id=old_bundle_id, parent=service_prototype, type=ObjectType.COMPONENT
            ):
                component = Component.objects.filter(
                    cluster=cluster,
                    service=service,
                    prototype__name=component_prototype.name,
                ).first()

                if component:
                    self._revert_object(obj=component, old_prototype=component_prototype)
                    continue

                component = Component.objects.create(
                    cluster_id=service.cluster_id,  # pyright: ignore[reportAttributeAccessIssue]
                    service=service,
                    prototype=component_prototype,
                )
                self.config_service.create_initial_configuration_if_required(
                    owner=orm_object_to_core_descriptor(component)
                )
                self._restore_deleted_objects(
                    obj=component,
                    before_upgrade=before_upgrade.service_deleted_components[service_prototype.name][
                        component_prototype.name
                    ],
                )

    def _restore_services_deleted_by_switch(
        self, cluster: Cluster, old_bundle_id: BundleID, before_upgrade: ClusterBeforeUpgrade
    ) -> None:
        for service_name in before_upgrade.services:
            is_deleted_from_bundle = service_name in before_upgrade.deleted_services
            prototype = Prototype.objects.get(bundle_id=old_bundle_id, name=service_name, type=ObjectType.SERVICE)

            if Service.objects.filter(prototype=prototype, cluster=cluster).exists():
                continue

            if not is_deleted_from_bundle:
                # Services may be removed after upgrade and can't be recovered from before_upgrade (ADCM-8315)
                logger.warning("Service %s wasn't restored", service_name)
                continue

            service, *_ = self.create_services.do(cluster=cluster, prototype_ids=(prototype.pk,))
            deleted_service = before_upgrade.deleted_services[service_name]
            self._restore_deleted_objects(obj=service, before_upgrade=deleted_service)

            for component in Component.objects.filter(service=service):
                self._restore_deleted_objects(obj=component, before_upgrade=deleted_service.components[component.name])

    def _restore_hostcomponent(
        self, cluster: Cluster, old_bundle_id: BundleID, before_upgrade: ClusterBeforeUpgrade
    ) -> None:
        new_mapping: list[HostComponentEntry] = []
        for entry in before_upgrade.hc:
            host = Host.objects.get(fqdn=entry.host, cluster=cluster)
            service = Service.objects.get(prototype__name=entry.service, cluster=cluster)
            component = Component.objects.get(prototype__name=entry.component, cluster=cluster, service=service)
            new_mapping.append(HostComponentEntry(host_id=host.pk, component_id=component.pk))

        set_host_component_mapping(
            cluster_id=cluster.pk,
            bundle_id=old_bundle_id,
            new_mapping=new_mapping,
            cluster_service=self.cluster_service,
            checks_func=check_nothing,
        )

    # Provider

    def _revert_hosts(self, provider: Provider, old_bundle_id: BundleID) -> None:
        for host in Host.objects.filter(provider=provider):
            old_host_prototype = Prototype.objects.get(
                bundle_id=old_bundle_id,
                type=ObjectType.HOST,
                name=host.prototype.name,
            )
            self._revert_object(obj=host, old_prototype=old_host_prototype)


@dataclass(slots=True)
class BundleRevertInternalScript:
    revert_upgrade: RevertUpgrade
    status_scenarios: StatusScenarios

    @atomic()
    def do(self, task: Task, script: SimpleInternalScript, job_id: JobID) -> InternalScriptResult:
        _ = script, job_id

        task_ = TaskLog.objects.get(id=task.id)

        target = task_.task_object
        if not isinstance(target, Cluster | Provider):
            message = f"Task object: was given {type(target).__name__}, expected Cluster or Provider"
            raise RuntimeError(message)  # noqa: TRY004

        try:
            self.revert_upgrade.do(target=target)
        except ObjectDoesNotExist as error:
            # This is a hack. We can do this, since all AdcmEx are intercepted in the Executer,
            # and a message is generated in the log there.
            raise AdcmEx(
                code="INTERNAL_SERVER_ERROR",
                msg=f"The configuration cannot be restored because the record was deleted.\n\n{traceback.format_exc()}",
            ) from error
        finally:
            # On failure the event carries the in-memory (already reverted) prototype of `target`,
            # while the DB changes are rolled back. Kept as is for now, should be fixed later.
            self.status_scenarios.send_prototype_and_state_update_event(object_=target)

        re_apply_policy_for_jobs(task=task_)

        result_message = build_result_message(
            script_name="bundle_revert",
            full_complete_message="prototype reverted",
            with_updates=True,
        )
        return InternalScriptResult(code=0, message=result_message)


def _retrieve_prototype_before_upgrade(bundle_id: BundleID, type_: ObjectType) -> Prototype:
    old_bundle = Bundle.objects.get(pk=bundle_id)
    return Prototype.objects.get(bundle=old_bundle, name=old_bundle.name, type=type_)


def _to_configuration(raw_values: dict, raw_attributes: dict) -> Configuration:
    meta_attributes = convert_attr_to_adcm_meta(raw_attributes)
    attributes = {
        key: Attributes(is_active=value.get("isActive"), is_synced=value.get("isSynchronized"))
        for key, value in meta_attributes.items()
    }
    return Configuration(values=raw_values, attributes=attributes)


def _restore_config_host_groups(obj: MainObject) -> dict[ConfigHostGroupID, ConfigID]:
    """
    Recreates CHGs that are listed in `before_upgrade` but currently absent, without creating configs for them yet.
    Returns a ``CHG_ID -> config_ID`` map for every `before_upgrade` entry.
    """
    chgs_before_upgrade: dict = obj.before_upgrade.get("config_host_groups", {})
    if not chgs_before_upgrade:
        return {}

    obj_ct = ContentType.objects.get_for_model(obj)
    name_to_id: dict[str, int] = dict(
        ConfigHostGroup.objects.filter(object_id=obj.pk, object_type=obj_ct).values_list("name", "id")
    )

    for chg_name, chg in chgs_before_upgrade.items():
        if chg_name in name_to_id:
            continue

        config_host_group = ConfigHostGroup.objects.create(
            name=chg_name,
            description=REVERT_DESCRIPTION,
            object_id=obj.pk,
            object_type=obj_ct,
        )
        config_host_group.hosts.set(Host.objects.filter(fqdn__in=chg.get("hosts", ())))
        name_to_id[chg_name] = config_host_group.pk

    return {
        name_to_id[chg_name]: chg_data.get("config_id")
        for chg_name, chg_data in chgs_before_upgrade.items()
        if chg_name in name_to_id
    }


# Cluster


def _delete_objects_of_upgraded_bundle(cluster: Cluster, upgraded_bundle: Bundle) -> None:
    Service.objects.filter(cluster=cluster, prototype__bundle=upgraded_bundle).delete()
    Component.objects.filter(cluster=cluster, prototype__bundle=upgraded_bundle).delete()


def _add_import_issues(cluster: Cluster) -> None:
    """Rechecks imports of potentially affected objects, since restored binds can violate import rules"""

    concerns_created = False
    for orm_object in (cluster, *Service.objects.filter(cluster=cluster)):
        owner = orm_object_to_core_descriptor(orm_object)
        if retrieve_issue(owner=owner, cause=ConcernCause.IMPORT) is None and object_imports_has_issue(
            target=orm_object
        ):  # TODO: make core-friendly, move into restore_binds()
            create_issue(owner=owner, cause=ConcernCause.IMPORT)
            concerns_created = True

    if concerns_created:
        redistribute_issues_and_flags(topology=retrieve_cluster_topology(cluster.pk))
