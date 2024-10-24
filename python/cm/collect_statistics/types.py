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

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Collection, Generic, Protocol, TypedDict, TypeVar

T = TypeVar("T")


class Collector(Protocol):
    def __call__(self) -> T:
        pass


class Storage(Generic[T], ABC):
    @abstractmethod
    def add(self, data: T) -> None:
        pass

    @abstractmethod
    def gather(self) -> Path:
        pass


class Sender(Generic[T], ABC):
    @abstractmethod
    def send(self, targets: Collection[T]) -> None:
        pass


class Encoder(Generic[T], ABC):
    @abstractmethod
    def encode(self, data: T) -> T:
        pass

    @abstractmethod
    def decode(self, data: T) -> T:
        pass


# Host Facts Section


class HostDeviceFacts(TypedDict):
    name: str
    removable: bool
    rotational: bool
    size: str
    description: str


class HostOSFacts(TypedDict):
    distribution: str
    version: str
    family: str


class HostFacts(TypedDict):
    cpu_vcores: int
    os: HostOSFacts
    ram: int
    devices: list[HostDeviceFacts]
