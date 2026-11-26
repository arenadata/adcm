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

from collections import defaultdict
from collections.abc import Iterable

from core.cluster import ClusterTopology, ComponentTopology, ServiceTopology
from core.types import ClusterID, ComponentID, HostID, ServiceID, ShortObjectInfo


def build_cluster_topology(
    cluster_id: ClusterID,
    mapping: Iterable[tuple[ServiceID, ComponentID, HostID]] = (),
    unmapped_components: Iterable[tuple[ServiceID, ComponentID]] = (),
    unmapped_hosts: Iterable[HostID] = (),
) -> ClusterTopology:
    """
    Build a `ClusterTopology` from a flat description, for tests that only care about the shape
    of the topology, not where it came from.

    `mapping` entries are `(service_id, component_id, host_id)` triplets, one per mapped host —
    the same shape as a `HostComponent` record. `unmapped_components` lists components that exist
    but have no hosts mapped to them; `unmapped_hosts` lists hosts that belong to the cluster but
    aren't mapped to anything. Names are derived from ids (e.g. `"service_1"`), since nothing here
    needs to assert on them.
    """
    services: dict[ServiceID, dict[ComponentID, dict[HostID, ShortObjectInfo]]] = defaultdict(lambda: defaultdict(dict))
    hosts: dict[HostID, ShortObjectInfo] = {}

    for service_id, component_id, host_id in mapping:
        hosts[host_id] = ShortObjectInfo(id=host_id, name=f"host_{host_id}")
        services[service_id][component_id][host_id] = hosts[host_id]

    for service_id, component_id in unmapped_components:
        services[service_id][component_id]  # noqa: B018 — touch to register the component with no hosts

    for host_id in unmapped_hosts:
        hosts[host_id] = ShortObjectInfo(id=host_id, name=f"host_{host_id}")

    return ClusterTopology(
        cluster_id=cluster_id,
        hosts=hosts,
        services={
            service_id: ServiceTopology(
                info=ShortObjectInfo(id=service_id, name=f"service_{service_id}"),
                components={
                    component_id: ComponentTopology(
                        info=ShortObjectInfo(id=component_id, name=f"component_{component_id}"),
                        hosts=component_hosts,
                    )
                    for component_id, component_hosts in components.items()
                },
            )
            for service_id, components in services.items()
        },
    )
