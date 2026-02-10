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
from core.types import ADCMCoreType, ClusterObjectDesc, ComponentDesc, Descriptor, ServiceDesc


def find_children_excluding_hosts(
    target: ClusterObjectDesc, topology: ClusterTopology
) -> Iterable[ServiceDesc | ComponentDesc]:
    match target:
        case Descriptor(type=ADCMCoreType.CLUSTER):
            services: Iterable[ServiceDesc] = (
                Descriptor(id=id_, type=ADCMCoreType.SERVICE) for id_ in topology.services
            )
            components: Iterable[ComponentDesc] = (
                Descriptor(id=id_, type=ADCMCoreType.COMPONENT) for id_ in topology.component_ids
            )
            return chain.from_iterable((services, components))

        case Descriptor(id=service_id, type=ADCMCoreType.SERVICE):
            service_topology = topology.services[service_id]
            return (Descriptor(id=id_, type=ADCMCoreType.COMPONENT) for id_ in service_topology.components)

        case Descriptor(type=ADCMCoreType.COMPONENT):
            return ()
