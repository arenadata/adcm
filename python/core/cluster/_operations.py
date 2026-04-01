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

from itertools import chain
from typing import Iterable

from core.cluster._types import ClusterTopology
from core.types import ADCMCoreType, ClusterObjectDesc, ComponentDesc, Descriptor, HostDesc, ServiceDesc


def find_children_excluding_hosts(
    target: ClusterObjectDesc, topology: ClusterTopology
) -> Iterable[ServiceDesc | ComponentDesc]:
    return (desc for desc in find_children(target=target, topology=topology) if desc.type != ADCMCoreType.HOST)


def find_children(
    target: ClusterObjectDesc, topology: ClusterTopology
) -> Iterable[ServiceDesc | ComponentDesc | HostDesc]:
    match target:
        case Descriptor(type=ADCMCoreType.CLUSTER):
            services: Iterable[ServiceDesc] = (
                Descriptor(id=id_, type=ADCMCoreType.SERVICE) for id_ in topology.services
            )
            components: Iterable[ComponentDesc] = (
                Descriptor(id=id_, type=ADCMCoreType.COMPONENT) for id_ in topology.component_ids
            )
            hosts: Iterable[HostDesc] = (Descriptor(id=id_, type=ADCMCoreType.HOST) for id_ in topology.hosts)

            return chain.from_iterable((services, components, hosts))

        case Descriptor(id=service_id, type=ADCMCoreType.SERVICE):
            service_topology = topology.services[service_id]
            components: Iterable[ComponentDesc] = (
                Descriptor(id=id_, type=ADCMCoreType.COMPONENT) for id_ in service_topology.components
            )
            hosts: Iterable[HostDesc] = (
                Descriptor(id=id_, type=ADCMCoreType.HOST) for id_ in service_topology.host_ids
            )

            return chain.from_iterable((components, hosts))

        case Descriptor(type=ADCMCoreType.COMPONENT):
            component = topology.get_component(component_id=target.id)
            hosts: Iterable[HostDesc] = (Descriptor(id=id_, type=ADCMCoreType.HOST) for id_ in component.hosts)

            return hosts
