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
from typing import Callable, Iterable, TypeAlias

from api_v2.host.utils import create_host
from api_v2.service.utils import bulk_add_services_to_cluster
from core.cluster.types import HostComponentEntry
from core.types import (
    BundleID,
    ClusterID,
    ComponentName,
    HostID,
    HostName,
    ProviderID,
    ProviderName,
    ServiceName,
)
from django.contrib.contenttypes.models import ContentType
from django.db.models import F

from cm.api import add_cluster, add_host_provider, update_obj_config
from cm.models import (
    AnsibleConfig,
    Bundle,
    Cluster,
    Component,
    ConfigHostGroup,
    Host,
    MaintenanceMode,
    ObjectType,
    Prototype,
    Provider,
    Service,
)
from cm.services.cluster import perform_host_to_cluster_map
from cm.services.mapping import change_host_component_mapping
from cm.services.status import notify
from cm.services.transition.types import (
    BundleHash,
    ClusterInfo,
    ConfigHostGroupInfo,
    HostInfo,
    ProviderInfo,
    RestorableCondition,
    TransitionPayload,
)

BundleHashIDMap: TypeAlias = dict[BundleHash, BundleID]
ProviderNameIDsMap: TypeAlias = dict[ProviderName, tuple[ProviderID, BundleID]]
HostNameIDMap: TypeAlias = dict[HostName, HostID]


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

    report("Host Providers discovery/creation")
    providers = discover_providers(providers={entry.name: entry.bundle for entry in data.providers})
    if providers:
        report(f"Some Host Providers exist, they will be used to create hosts from them: {', '.join(providers)}")

    if len(providers) != len(data.providers):
        missing_providers = tuple(entry for entry in data.providers if entry.name not in providers)
        report(f"Host Providers will be created: {', '.join(hp.name for hp in missing_providers)}")

        providers |= create_new_providers(providers=missing_providers, bundles=bundles)

    report("Hosts creation")
    hosts = create_new_hosts(hosts=data.hosts, providers=providers)

    report("Cluster creation")
    return create_cluster(cluster=data.cluster, bundles=bundles, hosts=hosts)


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


def create_new_providers(providers: Iterable[ProviderInfo], bundles: BundleHashIDMap) -> ProviderNameIDsMap:
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
        result[provider_info.name] = (new_provider.id, bundle_id)
        _restore_state(target=new_provider, condition=provider_info.condition)

    return result


def create_new_hosts(hosts: Iterable[HostInfo], providers: ProviderNameIDsMap) -> HostNameIDMap:
    result = {}

    hosts_in_mm = deque()

    for host_info in hosts:
        provider_id, bundle_id = providers[host_info.provider]
        host = create_host(bundle_id=bundle_id, provider_id=provider_id, fqdn=host_info.name, cluster=None)
        result[host_info.name] = host.id
        _restore_state(target=host, condition=host_info.condition)
        if host_info.maintenance_mode == "on":
            hosts_in_mm.append(host.id)

    if hosts_in_mm:
        Host.objects.filter(id__in=hosts_in_mm).update(maintenance_mode=MaintenanceMode.ON)

    return result


def create_cluster(cluster: ClusterInfo, bundles: BundleHashIDMap, hosts: HostNameIDMap) -> ClusterID:
    bundle_id = bundles[cluster.bundle]
    cluster_prototype = Prototype.objects.get(bundle_id=bundle_id, type=ObjectType.CLUSTER)

    cluster_object = add_cluster(prototype=cluster_prototype, name=cluster.name, description=cluster.description)
    AnsibleConfig.objects.filter(
        object_id=cluster_object.id, object_type=ContentType.objects.get_for_model(Cluster)
    ).update(value=cluster.ansible_config)
    services_to_add = Prototype.objects.filter(
        bundle_id=bundle_id, type=ObjectType.SERVICE, name__in=(service.name for service in cluster.services.values())
    )
    bulk_add_services_to_cluster(cluster=cluster_object, prototypes=services_to_add)
    perform_host_to_cluster_map(cluster_id=cluster_object.id, hosts=hosts.values(), status_service=notify)

    _restore_state(target=cluster_object, condition=cluster.condition)

    config_host_groups: deque[tuple[Cluster | Service | Component, ConfigHostGroupInfo]] = deque(
        (cluster_object, group) for group in cluster.host_groups
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
        _restore_state(target=service_object, condition=service_info.condition)
        config_host_groups.extend((service_object, group) for group in service_info.host_groups)
        if service_info.maintenance_mode == "on":
            services_in_mm.append(service_object.id)

        for component_info in service_info.components.values():
            component_object = component_object_mapping[component_info.name]
            _restore_state(target=component_object, condition=component_info.condition)
            config_host_groups.extend((component_object, group) for group in component_info.host_groups)
            if component_info.maintenance_mode == "on":
                components_in_mm.append(component_object.id)

    if services_in_mm:
        Service.objects.filter(id__in=services_in_mm).update(_maintenance_mode=MaintenanceMode.ON)

    if components_in_mm:
        Component.objects.filter(id__in=components_in_mm).update(_maintenance_mode=MaintenanceMode.ON)

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

        change_host_component_mapping(cluster_id=cluster_object.id, bundle_id=bundle_id, flat_mapping=mapping)

    if config_host_groups:
        for owner, group in config_host_groups:
            _create_group_config(owner=owner, group=group, hosts=hosts)

    return cluster_object.id


def _restore_state(target: Provider | Host | Cluster | Service | Component, condition: RestorableCondition) -> None:
    if condition.config:
        update_obj_config(
            obj_conf=target.config, config=condition.config, attr=condition.attr, description="Restored configuration"
        )

    target.set_state(condition.state)
    for multi_state in condition.multi_state:
        target.set_multi_state(multi_state)


def _create_group_config(
    owner: Cluster | Service | Component, group: ConfigHostGroupInfo, hosts: HostNameIDMap
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

    # groups without configs shouldn't be created (according to API v2 rules)
    update_obj_config(
        obj_conf=host_group.config, config=group.config, attr=group.attr, description="Restored configuration"
    )
