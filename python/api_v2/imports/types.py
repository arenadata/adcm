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

from typing import TypedDict

from cm.models import Cluster, ClusterObject, PrototypeImport


class CommonImportCandidate(TypedDict):
    obj: Cluster | ClusterObject
    prototype_import: PrototypeImport


class ServiceImportCandidate(TypedDict):
    obj: ClusterObject
    prototype_import: PrototypeImport


class ClusterImportCandidate(TypedDict):
    obj: Cluster
    prototype_import: PrototypeImport | None
    services: list[ServiceImportCandidate]


class UICluster(TypedDict):
    id: int
    name: str
    status: str
    state: str


class UIImportCluster(TypedDict):
    id: int
    is_multi_bind: bool
    is_required: bool


class UIImportServices(TypedDict):
    id: int
    name: str
    display_name: str
    version: str
    is_required: bool
    is_multi_bind: bool


class UIBindSource(TypedDict):
    id: int
    type: str


class UIBind(TypedDict):
    id: int
    source: UIBindSource


class UIObjectImport(TypedDict):
    cluster: UICluster
    import_cluster: UIImportCluster | None
    import_services: list[UIImportServices] | None
    binds: list[UIBind]
