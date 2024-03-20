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

from enum import Enum
from typing import NamedTuple, TypeAlias

ObjectID: TypeAlias = int
ClusterID: TypeAlias = ObjectID
ServiceID: TypeAlias = ObjectID
ComponentID: TypeAlias = ObjectID
HostID: TypeAlias = ObjectID
HostProviderID: TypeAlias = ObjectID

BundleID: TypeAlias = int
PrototypeID: TypeAlias = int
ActionID: TypeAlias = int

ConfigID: TypeAlias = int

HostName: TypeAlias = str


class ADCMCoreError(Exception):
    ...


class ADCMMessageError(ADCMCoreError):
    def __init__(self, message: str):
        super().__init__()

        self.message = message


class ADCMCoreType(Enum):
    CLUSTER = "cluster"
    SERVICE = "service"
    COMPONENT = "component"
    HOSTPROVIDER = "hostprovider"
    HOST = "host"


class ShortObjectInfo(NamedTuple):
    id: ObjectID
    name: str


class GeneralEntityDescriptor(NamedTuple):
    id: ObjectID
    type: str


class CoreObjectDescriptor(NamedTuple):
    id: ObjectID
    type: ADCMCoreType
