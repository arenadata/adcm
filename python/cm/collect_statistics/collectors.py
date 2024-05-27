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

from pydantic import BaseModel

from cm.collect_statistics.types import Collector


class BundleData(BaseModel):
    name: str
    version: str
    edition: str
    date: str


class HostComponentData(BaseModel):
    host_name: str
    component_name: str
    service_name: str


class ClusterData(BaseModel):
    name: str
    host_count: int
    bundle: dict
    host_component_map: list[dict]


class HostProviderData(BaseModel):
    name: str
    host_count: int
    bundle: dict


class UserData(BaseModel):
    email: str
    date_joined: str


class RoleData(BaseModel):
    name: str
    built_in: bool


class ADCMEntities(BaseModel):
    clusters: list[ClusterData]
    bundles: list[BundleData]
    providers: list[HostProviderData]
    users: list[UserData]
    roles: list[RoleData]


class CommunityBundleCollector(Collector):
    def __call__(self) -> ADCMEntities:
        pass


class EnterpriseBundleCollector(Collector):
    def __call__(self) -> ADCMEntities:
        pass
