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

from typing import TypeAlias

from adcm.dependencies import prepare_container
from core.config._secrets import decrypt_if_possible
from core.types import (
    BundleID,
    ClusterID,
    ComponentID,
    ComponentNameKey,
    ConfigID,
    HostID,
    HostName,
    ObjectID,
    ProviderID,
    ServiceID,
    ServiceNameKey,
)
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Q
import core

from cm.legacy.services.transition.types import (
    ActionHostGroupInfo,
    BundleExtraInfo,
    BundleHash,
    ClusterInfo,
    ComponentInfo,
    ConfigHostGroupInfo,
    HostInfo,
    NamedMappingEntry,
    ProviderInfo,
    RestorableCondition,
    ServiceInfo,
    TransitionPayload,
)
from cm.models import (
    ActionHostGroup,
    AnsibleConfig,
    Bundle,
    Cluster,
    Component,
    ConfigHostGroup,
    Host,
    HostComponent,
    MaintenanceMode,
    Provider,
    Service,
)

# store to this dict conditions that should be updated based on config
ConfigUpdateAcc: TypeAlias = dict[ConfigID, RestorableCondition | ConfigHostGroupInfo]


def dump(cluster_id: ClusterID) -> TransitionPayload:
    configs_to_set: ConfigUpdateAcc = {}

    hosts, provider_ids = retrieve_hosts(cluster_id=cluster_id, config_acc=configs_to_set)
    providers, bundles = retrieve_providers(providers=provider_ids, config_acc=configs_to_set)
    cluster, cluster_bundle_id = retrieve_cluster(
        cluster_id=cluster_id, hosts={host_id: host.name for host_id, host in hosts.items()}, config_acc=configs_to_set
    )
    bundles.add(cluster_bundle_id)
    bundles_info = retrieve_bundles_info(ids=bundles)

    # this whole function is actually a Use Case, yet for a time being I directly use container building
    di_container = prepare_container()
    with di_container() as container:
        fill_configurations(config_acc=configs_to_set, config_service=container.get(core.config.ConfigService))

    return TransitionPayload(
        adcm_version=settings.ADCM_VERSION,
        bundles=bundles_info,
        providers=providers,
        hosts=list(hosts.values()),
        cluster=cluster,
    )


def retrieve_hosts(
    cluster_id: ClusterID, config_acc: ConfigUpdateAcc
) -> tuple[dict[HostID, HostInfo], set[ProviderID]]:
    providers = set()

    hosts: dict[HostID, HostInfo] = {}

    for entry in Host.objects.filter(cluster_id=cluster_id).annotate(
        current_config_id=F("config__current"), provider_name=F("provider__name")
    ):
        if entry.maintenance_mode not in (MaintenanceMode.ON, MaintenanceMode.OFF):
            message = f"Host {entry.fqdn} has unserializable Maintenance Mode state: {entry.maintenance_mode}"
            raise ValueError(message)

        providers.add(entry.provider_id)

        current_condition = RestorableCondition(state=entry.state, multi_state=entry.multi_state)

        if entry.current_config_id:
            config_acc[entry.current_config_id] = current_condition

        hosts[entry.id] = HostInfo(
            name=entry.fqdn,
            provider=entry.provider_name,
            condition=current_condition,
            maintenance_mode=str(entry.maintenance_mode).lower(),
        )

    return hosts, providers


def retrieve_providers(
    providers: set[ProviderID], config_acc: ConfigUpdateAcc
) -> tuple[list[ProviderInfo], set[BundleID]]:
    bundles = set()

    result = []

    for entry in Provider.objects.filter(id__in=providers).annotate(
        current_config_id=F("config__current"),
        bundle_id_value=F("prototype__bundle_id"),
        bundle_hash=F("prototype__bundle__hash"),
    ):
        bundles.add(entry.bundle_id_value)

        current_condition = RestorableCondition(state=entry.state, multi_state=entry.multi_state)

        if entry.current_config_id:
            config_acc[entry.current_config_id] = current_condition

        result.append(
            ProviderInfo(
                bundle=entry.bundle_hash, name=entry.name, description=entry.description, condition=current_condition
            )
        )

    return result, bundles


def retrieve_cluster(
    cluster_id: ClusterID, hosts: dict[HostID, HostName], config_acc: ConfigUpdateAcc
) -> tuple[ClusterInfo, BundleID]:
    cluster = Cluster.objects.annotate(
        current_config_id=F("config__current"),
        bundle_id_value=F("prototype__bundle_id"),
        bundle_hash=F("prototype__bundle__hash"),
    ).get(id=cluster_id)

    current_condition = RestorableCondition(state=cluster.state, multi_state=cluster.multi_state)

    if cluster.current_config_id:
        config_acc[cluster.current_config_id] = current_condition

    cluster_info = ClusterInfo(
        bundle=cluster.bundle_hash, name=cluster.name, description=cluster.description, condition=current_condition
    )

    cluster_info.ansible_config = AnsibleConfig.objects.values_list("value", flat=True).get(
        object_id=cluster.id, object_type=ContentType.objects.get_for_model(Cluster)
    )

    service_id_name_map: dict[ServiceID, ServiceNameKey] = {}
    component_id_name_map: dict[ComponentID, ComponentNameKey] = {}

    for service in Service.objects.filter(cluster_id=cluster_id).annotate(
        current_config_id=F("config__current"), service_name=F("prototype__name")
    ):
        name = ServiceNameKey(service=service.service_name)
        mm = service.maintenance_mode_attr
        if mm not in (MaintenanceMode.ON, MaintenanceMode.OFF):
            message = f"{str(name).capitalize()} has unserializable Maintenance Mode state: {mm}"
            raise ValueError(message)

        service_id_name_map[service.id] = name

        condition = RestorableCondition(state=service.state, multi_state=service.multi_state)

        if service.current_config_id:
            config_acc[service.current_config_id] = condition

        cluster_info.services[name.service] = ServiceInfo(
            name=name.service, condition=condition, maintenance_mode=str(mm).lower()
        )

    for component in Component.objects.filter(cluster_id=cluster_id).annotate(
        current_config_id=F("config__current"),
        component_name=F("prototype__name"),
        service_name=F("prototype__parent__name"),
    ):
        name = ComponentNameKey(service=component.service_name, component=component.component_name)
        mm = component.maintenance_mode_attr
        if mm not in (MaintenanceMode.ON, MaintenanceMode.OFF):
            message = f"{str(name).capitalize()} has unserializable Maintenance Mode state: {mm}"
            raise ValueError(message)

        component_id_name_map[component.id] = name

        condition = RestorableCondition(state=component.state, multi_state=component.multi_state)

        if component.current_config_id:
            config_acc[component.current_config_id] = condition

        cluster_info.services[name.service].components[name.component] = ComponentInfo(
            name=name.component, condition=condition, maintenance_mode=str(mm).lower()
        )

    for host_id, component_id in HostComponent.objects.values_list("host_id", "component_id").filter(
        cluster_id=cluster_id
    ):
        key = component_id_name_map[component_id]
        cluster_info.mapping.append(
            NamedMappingEntry(host=hosts[host_id], service=key.service, component=key.component)
        )

    cluster_ct = ContentType.objects.get_for_model(Cluster)
    service_ct = ContentType.objects.get_for_model(Service)
    component_ct = ContentType.objects.get_for_model(Component)

    object_filter = (
        Q(object_type=cluster_ct, object_id=cluster_id)
        | Q(object_type=service_ct, object_id__in=service_id_name_map)
        | Q(object_type=component_ct, object_id__in=component_id_name_map)
    )

    host_groups: dict[ObjectID, ConfigHostGroupInfo] = {}

    for group in (
        ConfigHostGroup.objects.filter(object_filter)
        .annotate(current_config_id=F("config__current"))
        .select_related("object_type")
    ):
        group_info = ConfigHostGroupInfo(name=group.name, description=group.description)

        host_groups[group.id] = group_info
        config_acc[group.current_config_id] = group_info

        if group.object_type == cluster_ct:
            cluster_info.config_host_groups.append(group_info)
        elif group.object_type == service_ct:
            cluster_info.services[service_id_name_map[group.object_id].service].config_host_groups.append(group_info)
        else:
            key = component_id_name_map[group.object_id]
            cluster_info.services[key.service].components[key.component].config_host_groups.append(group_info)

    for group_id, host_id in ConfigHostGroup.hosts.through.objects.filter(
        confighostgroup_id__in=host_groups
    ).values_list("confighostgroup_id", "host_id"):
        host_groups[group_id].hosts.append(hosts[host_id])

    action_host_groups: dict[ObjectID, ActionHostGroupInfo] = {}

    for group in ActionHostGroup.objects.filter(object_filter).select_related("object_type"):
        group_info = ActionHostGroupInfo(name=group.name, description=group.description)

        action_host_groups[group.pk] = group_info

        if group.object_type == cluster_ct:
            cluster_info.action_host_groups.append(group_info)
        elif group.object_type == service_ct:
            cluster_info.services[service_id_name_map[group.object_id].service].action_host_groups.append(group_info)
        else:
            key = component_id_name_map[group.object_id]
            cluster_info.services[key.service].components[key.component].action_host_groups.append(group_info)

    for group_id, host_id in ActionHostGroup.hosts.through.objects.filter(
        actionhostgroup_id__in=action_host_groups
    ).values_list("actionhostgroup_id", "host_id"):
        action_host_groups[group_id].hosts.append(hosts[host_id])

    return cluster_info, cluster.bundle_id_value


def retrieve_bundles_info(ids: set[BundleID]) -> dict[BundleHash, BundleExtraInfo]:
    return {
        hash_: BundleExtraInfo(name=name, version=version, edition=edition)
        for name, version, edition, hash_ in Bundle.objects.filter(id__in=ids).values_list(
            "name", "version", "edition", "hash"
        )
    }


def fill_configurations(config_acc: ConfigUpdateAcc, config_service: core.config.ConfigService) -> None:
    configurations = config_service.retrieve_configurations_by_id(config_acc)
    for config_id, config in configurations.items():
        # literal decryption for simplicity purposes, better rework
        config.values = decrypt_if_possible(value=config.values, decryptor=config_service.secrets.decrypt)
        target = config_acc[config_id]
        target.config = config
