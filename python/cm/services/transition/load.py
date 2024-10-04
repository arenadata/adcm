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
from core.types import (
    BundleID,
    ClusterID,
    ComponentName,
    HostID,
    HostName,
    HostProviderID,
    HostProviderName,
    ServiceName,
)
from django.contrib.contenttypes.models import ContentType
from django.db.models import F

from cm.api import add_cluster, add_host_provider, update_obj_config
from cm.models import (
    Bundle,
    Cluster,
    ClusterObject,
    GroupConfig,
    Host,
    HostComponent,
    HostProvider,
    MaintenanceMode,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from cm.services.cluster import perform_host_to_cluster_map
from cm.services.status import notify
from cm.services.transition.types import (
    BundleHash,
    ClusterInfo,
    ConfigHostGroupInfo,
    HostInfo,
    HostProviderInfo,
    RestorableCondition,
    TransitionPayload,
)

BundleHashIDMap: TypeAlias = dict[BundleHash, BundleID]
HostProviderNameIDsMap: TypeAlias = dict[HostProviderName, tuple[HostProviderID, BundleID]]
HostNameIDMap: TypeAlias = dict[HostName, HostID]


def load(data: TransitionPayload, report: Callable[[str], None] = print) -> None:
    report("Load started...")

    report("Bundles discovery")
    bundles = discover_bundles(data.bundles)
    if len(bundles) != len(data.bundles):
        missing_bundles = [
            str(data.bundles[missing_bundle_hash]) for missing_bundle_hash in set(data.bundles).difference(bundles)
        ]
        report(f"Not all bundles are installed.\nMissing:\n{'\n'.join(missing_bundles)}")
        message = "Bundles are missing in this ADCM"
        raise RuntimeError(message)

    report("Host Providers discovery/creation")
    hostproviders = discover_hostproviders(hostproviders={entry.name: entry.bundle for entry in data.hostproviders})
    if hostproviders:
        report(f"Some Host Providers exist, they will be used to create hosts from them: {', '.join(hostproviders)}")

    if len(hostproviders) != len(data.hostproviders):
        report(f"Host Provider will be created: {', '.join(hp.name for hp in data.hostproviders)}")

        hostproviders |= create_new_hostproviders(
            hostproviders=(entry for entry in data.hostproviders if entry.name not in hostproviders), bundles=bundles
        )

    report("Hosts creation")
    hosts = create_new_hosts(hosts=data.hosts, hostproviders=hostproviders)

    report("Cluster creation")
    create_cluster(cluster=data.cluster, bundles=bundles, hosts=hosts)


def discover_bundles(required_bundles: BundleHash) -> BundleHashIDMap:
    return dict(Bundle.objects.values_list("hash", "id").filter(hash__in=required_bundles))


def discover_hostproviders(hostproviders: dict[HostProviderName, BundleHash]) -> HostProviderNameIDsMap:
    result = {}

    for id_, name, bundle_id, bundle_hash in HostProvider.objects.values_list(
        "id", "name", "bundle_id", "bundle__hash"
    ).filter(name__in=hostproviders):
        if bundle_hash == hostproviders[name]:
            result[name] = (id_, bundle_id)

    return result


def create_new_hostproviders(
    hostproviders: Iterable[HostProviderInfo], bundles: BundleHashIDMap
) -> HostProviderNameIDsMap:
    provider_protos: dict[BundleHash, Prototype] = {}
    bundle_id_hash: dict[BundleID, BundleHash] = {v: k for k, v in bundles.items()}

    for prototype in Prototype.objects.filter(bundle_id__in=bundles.values(), type=ObjectType.PROVIDER):
        provider_protos[bundle_id_hash[prototype.bundle_id]] = prototype

    result = {}

    for provider_info in hostproviders:
        bundle_id = bundles[provider_info.bundle]
        new_provider = add_host_provider(
            prototype=provider_protos[bundle_id], name=provider_info.name, description=provider_info.description
        )
        result[provider_info.name] = (new_provider.id, bundle_id)
        _restore_state(target=new_provider, condition=provider_info.state)

    return result


def create_new_hosts(hosts: Iterable[HostInfo], hostproviders: HostProviderNameIDsMap) -> HostNameIDMap:
    result = {}

    hosts_in_mm = deque()

    for host_info in hosts:
        provider_id, bundle_id = hostproviders[host_info.hostprovider]
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
    services_to_add = Prototype.objects.filter(
        bundle_id=bundle_id, type=ObjectType.SERVICE, name__in=(service.name for service in cluster.services)
    )
    bulk_add_services_to_cluster(cluster=cluster_object, prototypes=services_to_add)
    perform_host_to_cluster_map(cluster_id=cluster.pk, hosts=hosts.values(), status_service=notify)

    _restore_state(target=cluster, condition=cluster.condition)

    config_host_groups: deque[tuple[Cluster | ClusterObject | ServiceComponent, ConfigHostGroupInfo]] = deque(
        (cluster_object, group) for group in cluster.host_groups
    )

    orm_objects: dict[ServiceName, tuple[ClusterObject, dict[ComponentName, ServiceComponent]]] = {}

    for component in (
        ServiceComponent.objects.filter(cluster_id=cluster_object.id)
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
            component_object = component_object_mapping[component.name]
            _restore_state(target=component_object, condition=component_info.condition)
            config_host_groups.extend((component_object, group) for group in component_info.host_groups)
            if component_info.maintenance_mode == "on":
                components_in_mm.append(component_object.id)

    if services_in_mm:
        ClusterObject.objects.filter(id__in=services_in_mm).update(_maintenance_mode=MaintenanceMode.ON)

    if components_in_mm:
        ServiceComponent.objects.filter(id__in=components_in_mm).update(_maintenance_mode=MaintenanceMode.ON)

    if cluster.mapping:
        entries = deque()

        for hc_entry in cluster.mapping:
            service_object, component_object_mapping = orm_objects[hc_entry.service]
            component_object = component_object_mapping[hc_entry.component]
            entries.append(
                HostComponent(
                    cluster_id=cluster_object.id,
                    service_id=service_object.id,
                    component_id=component_object.id,
                    host_id=hosts[hc_entry.host],
                )
            )

        HostComponent.objects.bulk_create(objs=entries)

    if config_host_groups:
        for owner, group in config_host_groups:
            _create_group_config(owner=owner, group=group)


def _restore_state(
    target: HostProvider | Host | Cluster | ClusterObject | ServiceComponent, condition: RestorableCondition
) -> None:
    if condition.config:
        update_obj_config(
            obj_conf=target.config, config=condition.config, attr=condition.attr, description="Restored configuration"
        )

    target.set_state(condition.state)
    target.set_multi_state(condition.multi_state)


def _create_group_config(
    owner: Cluster | ClusterObject | ServiceComponent, group: ConfigHostGroupInfo, hosts: HostNameIDMap
) -> None:
    # there's no business rule for that, but probably should be
    host_group = GroupConfig.objects.create(
        object_type=ContentType.objects.get_for_model(model=owner),
        object_id=owner.pk,
        name=group.name,
        description=group.description,
    )

    if group.hosts:
        m2m = GroupConfig.hosts.through
        m2m.objects.bulk_create(objs=(m2m(groupconfig_id=host_group.id, host_id=hosts[host]) for host in group.hosts))

    # groups without configs shouldn't be created (according to API v2 rules)
    update_obj_config(
        obj_conf=host_group.config, config=group.config, attr=group.attr, description="Restored configuration"
    )
