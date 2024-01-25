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

from contextlib import suppress
from typing import TypeAlias

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
)
from requests import JSONDecodeError

from cm.status_api import api_request

TypeIDPair: TypeAlias = tuple[str, int]
RawStatus: TypeAlias = int

StringID: TypeAlias = str
IntegerID: TypeAlias = int

# pylint: enable=invalid-name


class _StatusEntry(BaseModel):
    status: RawStatus


class _HostComponentStatusEntry(_StatusEntry):
    host: IntegerID
    component: IntegerID


class _ServiceStatusEntry(_StatusEntry):
    components: dict[StringID, _StatusEntry]
    details: list[_HostComponentStatusEntry]


class _ClusterStatusEntry(_StatusEntry):
    services: dict[StringID, _ServiceStatusEntry]
    hosts: dict[StringID, _StatusEntry]


class FullStatusMap(BaseModel):
    clusters: dict[StringID, _ClusterStatusEntry] = Field(default_factory=dict)
    hosts: dict[StringID, _StatusEntry] = Field(default_factory=dict)

    def get_for_cluster(self, cluster_id: IntegerID) -> RawStatus | None:
        with suppress(KeyError):
            return self.clusters[str(cluster_id)].status

        return None

    def get_for_service(self, cluster_id: IntegerID, service_id: IntegerID) -> RawStatus | None:
        with suppress(KeyError):
            return self.clusters[str(cluster_id)].services[str(service_id)].status

        return None

    def get_for_component(
        self, cluster_id: IntegerID, service_id: IntegerID, component_id: IntegerID
    ) -> RawStatus | None:
        with suppress(KeyError):
            return self.clusters[str(cluster_id)].services[str(service_id)].components[str(component_id)].status

        return None

    def get_for_host(self, host_id: IntegerID) -> RawStatus | None:
        with suppress(KeyError):
            return self.hosts[str(host_id)].status

        return None

    def get_for_host_component(
        self, cluster_id: IntegerID, service_id: IntegerID, component_id: IntegerID, host_id: IntegerID
    ) -> RawStatus | None:
        try:
            components = self.clusters[str(cluster_id)].services[str(service_id)].details
        except KeyError:
            return None

        return next(
            (entry.status for entry in components if entry.host == host_id and entry.component == component_id), None
        )


def retrieve_status_map() -> FullStatusMap:
    response = api_request(method="get", url="all/")
    if not response:
        return FullStatusMap()

    try:
        body = response.json()
    except JSONDecodeError:
        return FullStatusMap()

    if not isinstance(body, dict):
        return FullStatusMap()

    try:
        return FullStatusMap(**body)
    except ValidationError:
        return FullStatusMap()
