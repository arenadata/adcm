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

from collections import deque
from typing import Callable, Iterable, Literal, TypeAlias

from adcm.dependencies import prepare_container
from api_v2.host.utils import create_host
from core.legacy.cluster.types import HostComponentEntry
from core.types import (
    ADCMHostGroupType,
    BundleID,
    ClusterID,
    ComponentName,
    Descriptor,
    HostID,
    HostName,
    ProviderID,
    ProviderName,
    ServiceName,
)
from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from rbac.roles import apply_policy_for_new_config
from use_cases.transition.cluster.create import CreateCluster, CreateServicesFromPrototypes
import core

from cm import converters
from cm.legacy.api import add_host_provider
from cm.legacy.services.action_host_group import ActionHostGroupService, CreateDTO
from cm.legacy.services.cluster import perform_host_to_cluster_map, retrieve_cluster_topology
from cm.legacy.services.concern import delete_issue
from cm.legacy.services.concern.checks import object_configuration_has_issue
from cm.legacy.services.concern.distribution import redistribute_issues_and_flags
from cm.legacy.services.mapping import set_host_component_mapping
from cm.legacy.services.status import notify
from cm.legacy.services.transition.types import (
    ActionHostGroupInfo,
    BundleHash,
    ClusterInfo,
    ConfigHostGroupInfo,
    HostInfo,
    ProviderInfo,
    RestorableCondition,
    TransitionPayload,
)
from cm.models import (
    AnsibleConfig,
    Bundle,
    Cluster,
    Component,
    ConcernCause,
    ConfigHostGroup,
    ConfigLog,
    Host,
    MaintenanceMode,
    ObjectType,
    Prototype,
    Provider,
    Service,
)

# IMPORTANT
#
# At first "load" functionality tried to use "business" functions to restore entities in most natural way.
# Now more and more cases are asked for that need to ignore check or two,
# meaning increased risk of things working not as they'd normally do.
# For example, extra concern checks may be required or RBAC permissions recalculated.

BundleHashIDMap: TypeAlias = dict[BundleHash, BundleID]
ProviderNameIDsMap: TypeAlias = dict[ProviderName, tuple[ProviderID, BundleID]]
HostNameIDMap: TypeAlias = dict[HostName, HostID]
HostsInMM: TypeAlias = deque[HostID]


def load(data: TransitionPayload, report: Callable[[str], None] = print) -> ClusterID:
    report("Load started...")

    report("Bundles discovery")
    bundles = discover_bundles(data.bundles.keys())
    if len(bundles) != len(data.bundles):
        missing_bundles = "\n".join(
            str(data.bundles[missing_bundle_hash]) for missing_bundle_hash in set(data.bundles).difference(bundles)
        )
        report(f"Not all bundles are installed.\nMissing:\n{missing_bundles}")
        message = "Bundles are missing in this ADCM"
        raise RuntimeError(message)

    # this whole function is actually a Use Case, yet for a time being I directly use container building
    di_container = prepare_container()
    with di_container() as container:
        config_service = container.get(core.config.ConfigService)

        report("Host Providers discovery/creation")
        providers = discover_providers(providers={entry.name: entry.bundle for entry in data.providers})
        if providers:
            report(f"Some Host Providers exist, they will be used to create hosts from them: {', '.join(providers)}")

        if len(providers) != len(data.providers):
            missing_providers = tuple(entry for entry in data.providers if entry.name not in providers)
            report(f"Host Providers will be created: {', '.join(hp.name for hp in missing_providers)}")

            providers |= create_new_providers(
                providers=missing_providers,
                bundles=bundles,
                config_service=config_service,
            )

        report("Hosts creation")
        hosts, hosts_in_mm = create_new_hosts(
            hosts=data.hosts,
            providers=providers,
            config_service=config_service,
        )

        report("Cluster creation")
        cluster_id = create_cluster(
            cluster=data.cluster,
            bundles=bundles,
            hosts=hosts,
            config_service=config_service,
            ahg_service=container.get(ActionHostGroupService),
            create_cluster_use_case=container.get(CreateCluster),
            add_services_use_case=container.get(CreateServicesFromPrototypes),
        )

        if hosts_in_mm:
            # need to do it after mapping set to not interfere with it
            report("Restore MM for hosts")
            restore_mm_for_hosts(hosts_in_mm)

        return cluster_id


def discover_bundles(required_bundles: Iterable[BundleHash]) -> BundleHashIDMap:
    return dict(Bundle.objects.values_list("hash", "id").filter(hash__in=required_bundles))


def discover_providers(providers: dict[ProviderName, BundleHash]) -> ProviderNameIDsMap:
    result = {}

    for id_, name, bundle_id, bundle_hash in Provider.objects.values_list(
        "id", "name", "prototype__bundle_id", "prototype__bundle__hash"
    ).filter(name__in=providers):
        if bundle_hash == providers[name]:
            result[name] = (id_, bundle_id)

    return result


def create_new_providers(
    providers: Iterable[ProviderInfo], bundles: BundleHashIDMap, config_service: core.config.ConfigService
) -> ProviderNameIDsMap:
    provider_protos: dict[BundleHash, Prototype] = {}
    bundle_id_hash: dict[BundleID, BundleHash] = {v: k for k, v in bundles.items()}

    for prototype in Prototype.objects.filter(bundle_id__in=bundles.values(), type=ObjectType.PROVIDER):
        provider_protos[bundle_id_hash[prototype.bundle_id]] = prototype

    result = {}

    for provider_info in providers:
        bundle_id = bundles[provider_info.bundle]
        new_provider = add_host_provider(
            prototype=provider_protos[provider_info.bundle],
            name=provider_info.name,
            description=provider_info.description,
        )
        result[provider_info.name] = (new_provider.pk, bundle_id)
        _restore_state(target=new_provider, condition=provider_info.condition, config_service=config_service)

    return result


def create_new_hosts(
    hosts: Iterable[HostInfo], providers: ProviderNameIDsMap, config_service: core.config.ConfigService
) -> tuple[HostNameIDMap, HostsInMM]:
    result = {}

    hosts_in_mm = deque()

    for host_info in hosts:
        provider_id, bundle_id = providers[host_info.provider]
        host = create_host(bundle_id=bundle_id, provider_id=provider_id, fqdn=host_info.name, cluster=None)
        result[host_info.name] = host.id
        _restore_state(target=host, condition=host_info.condition, config_service=config_service)
        if host_info.maintenance_mode == "on":
            hosts_in_mm.append(host.id)

    return result, hosts_in_mm


def restore_mm_for_hosts(hosts: HostsInMM) -> None:
    Host.objects.filter(id__in=hosts).update(maintenance_mode=MaintenanceMode.ON)


def create_cluster(
    cluster: ClusterInfo,
    bundles: BundleHashIDMap,
    hosts: HostNameIDMap,
    create_cluster_use_case: CreateCluster,
    add_services_use_case: CreateServicesFromPrototypes,
    config_service: core.config.ConfigService,
    ahg_service: ActionHostGroupService,
) -> ClusterID:
    bundle_id = bundles[cluster.bundle]
    cluster_prototype = Prototype.objects.get(bundle_id=bundle_id, type=ObjectType.CLUSTER)

    cluster_id = create_cluster_use_case.do(
        prototype=cluster_prototype, name=cluster.name, description=cluster.description
    )
    cluster_object = Cluster.objects.get(id=cluster_id)

    AnsibleConfig.objects.filter(object_id=cluster_id, object_type=ContentType.objects.get_for_model(Cluster)).update(
        value=cluster.ansible_config
    )

    services_to_add = tuple(
        Prototype.objects.values_list("id", flat=True).filter(
            bundle_id=bundle_id,
            type=ObjectType.SERVICE,
            name__in=(service.name for service in cluster.services.values()),
        )
    )
    if services_to_add:
        add_services_use_case.do(cluster=cluster_object, prototype_ids=services_to_add)

    perform_host_to_cluster_map(cluster_id=cluster_object.id, hosts=hosts.values(), status_service=notify)

    _restore_state(target=cluster_object, condition=cluster.condition, config_service=config_service)

    config_host_groups: deque[tuple[Cluster | Service | Component, ConfigHostGroupInfo]] = deque(
        (cluster_object, group) for group in cluster.config_host_groups
    )
    action_host_groups: deque[tuple[Cluster | Service | Component, ActionHostGroupInfo]] = deque(
        (cluster_object, group) for group in cluster.action_host_groups
    )

    orm_objects: dict[ServiceName, tuple[Service, dict[ComponentName, Component]]] = {}

    for component in (
        Component.objects.filter(cluster_id=cluster_object.id)
        .select_related("service")
        .annotate(own_name=F("prototype__name"), parent_name=F("prototype__parent__name"))
    ):
        if component.parent_name in orm_objects:
            orm_objects[component.parent_name][1][component.own_name] = component
        else:
            orm_objects[component.parent_name] = (component.service, {component.own_name: component})

    services_in_mm = deque()
    components_in_mm = deque()

    for service_info in cluster.services.values():
        service_object, component_object_mapping = orm_objects[service_info.name]
        _restore_state(target=service_object, condition=service_info.condition, config_service=config_service)
        config_host_groups.extend((service_object, group) for group in service_info.config_host_groups)
        action_host_groups.extend((service_object, group) for group in service_info.action_host_groups)
        if service_info.maintenance_mode == "on":
            services_in_mm.append(service_object.id)

        for component_info in service_info.components.values():
            component_object = component_object_mapping[component_info.name]
            _restore_state(target=component_object, condition=component_info.condition, config_service=config_service)
            config_host_groups.extend((component_object, group) for group in component_info.config_host_groups)
            action_host_groups.extend((component_object, group) for group in component_info.action_host_groups)
            if component_info.maintenance_mode == "on":
                components_in_mm.append(component_object.id)

    if cluster.mapping:
        mapping = deque()
        for hc_entry in cluster.mapping:
            _, component_object_mapping = orm_objects[hc_entry.service]
            mapping.append(
                HostComponentEntry(
                    component_id=component_object_mapping[hc_entry.component].id,
                    host_id=hosts[hc_entry.host],
                )
            )

        set_host_component_mapping(cluster_id=cluster_object.id, bundle_id=bundle_id, new_mapping=mapping)

    if services_in_mm:
        Service.objects.filter(id__in=services_in_mm).update(_maintenance_mode=MaintenanceMode.ON)

    if components_in_mm:
        Component.objects.filter(id__in=components_in_mm).update(_maintenance_mode=MaintenanceMode.ON)

    if config_host_groups:
        for owner, group in config_host_groups:
            _create_group_config(owner=owner, group=group, hosts=hosts, config_service=config_service)

    if action_host_groups:
        for owner, group in action_host_groups:
            _create_action_host_group(owner=owner, group=group, hosts=hosts, service=ahg_service)

    topology = retrieve_cluster_topology(cluster_id)
    redistribute_issues_and_flags(topology=topology)

    return cluster_object.pk


def _restore_state(
    target: Provider | Host | Cluster | Service | Component,
    condition: RestorableCondition,
    config_service: core.config.ConfigService,
) -> core.config.spec.FullSpec | None:
    specification = None

    if condition.config:
        owner = converters.orm_object_to_core_descriptor(target)
        specification = config_service.retrieve_specification(owner=owner)
        # literal decryption for simplicity purposes, better rework
        core.config.operations.encrypt_secrets(
            values=condition.config.values,
            specification=specification,
            encrypt=config_service.secrets.encrypt,
            inplace=True,
        )
        config_log_id = config_service.create_new_configuration_by_descriptor(
            configuration=condition.config,
            configuration_extra_info=core.config.ConfigurationExtraInfo(
                description="Restored configuration", created_by="system"
            ),
            owner=owner,
        )
        config_log = ConfigLog.objects.get(id=config_log_id)
        apply_policy_for_new_config(config_object=target, config_log=config_log)
        owner_prefix = core.config.files.build_config_prefix(owner)
        config_service.prepare_file_parameter_values_on_fs(
            configuration=condition.config, specification=specification, owner_prefix=owner_prefix
        )
        if not object_configuration_has_issue(target):
            delete_issue(owner=owner, cause=ConcernCause.CONFIG)

    target.set_state(condition.state)
    for multi_state in condition.multi_state:
        target.set_multi_state(multi_state)

    return specification


def _create_group_config(
    owner: Cluster | Service | Component,
    group: ConfigHostGroupInfo,
    hosts: HostNameIDMap,
    config_service: core.config.ConfigService,
) -> None:
    # there's no business rule for that, but probably should be
    host_group = ConfigHostGroup.objects.create(
        object_type=ContentType.objects.get_for_model(model=owner),
        object_id=owner.pk,
        name=group.name,
        description=group.description,
    )

    if group.hosts:
        m2m = ConfigHostGroup.hosts.through
        m2m.objects.bulk_create(
            objs=(m2m(confighostgroup_id=host_group.id, host_id=hosts[host]) for host in group.hosts)
        )

    owner_desc = converters.orm_object_to_core_descriptor(owner)
    specification = config_service.retrieve_specification(owner=owner_desc)
    group_desc: Descriptor[Literal[ADCMHostGroupType.CONFIG]] = Descriptor(
        id=host_group.pk, type=ADCMHostGroupType.CONFIG
    )
    # literal decryption for simplicity purposes, better rework
    core.config.operations.encrypt_secrets(
        values=group.config.values, specification=specification, encrypt=config_service.secrets.encrypt, inplace=True
    )
    config_service.create_new_configuration_by_descriptor(
        configuration=group.config,
        configuration_extra_info=core.config.ConfigurationExtraInfo(
            description="Restored configuration", created_by="system"
        ),
        owner=group_desc,
    )

    group_file_prefix = core.config.files.build_config_host_group_prefix(owner=owner_desc, group_id=group_desc.id)
    config_service.prepare_file_parameter_values_on_fs(
        configuration=group.config, owner_prefix=group_file_prefix, specification=specification
    )


def _create_action_host_group(
    owner: Cluster | Service | Component,
    group: ActionHostGroupInfo,
    hosts: HostNameIDMap,
    service: ActionHostGroupService,
) -> None:
    descriptor = converters.orm_object_to_core_descriptor(owner)
    dto = CreateDTO(owner=descriptor, name=group.name, description=group.description)
    ahg_id = service.create(dto)
    if group.hosts:
        host_ids = [hosts[name] for name in group.hosts]
        service.add_hosts_to_group(group_id=ahg_id, hosts=host_ids)
