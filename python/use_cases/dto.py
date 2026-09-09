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

from dataclasses import dataclass, field
from typing import Generic, Protocol, TypeVar

from core.legacy.cluster.types import HostComponentEntry
import core

from use_cases.errors import UseCaseError

T = TypeVar("T", contravariant=True)


class InputConfigConverter(Protocol[T]):
    def __call__(self, configuration: T, specification: core.config.spec.FullSpec, /) -> core.config.Configuration:
        ...


# Action related


@dataclass(slots=True)
class ConfigurationDTO(Generic[T]):
    convert: InputConfigConverter[T]
    input_config: T


@dataclass(slots=True)
class _CommonActionDTO:
    configuration: ConfigurationDTO | None = None
    mapping: set[HostComponentEntry] | None = None
    launch: core.action.job.LaunchOptions = field(default_factory=core.action.job.LaunchOptions)


@dataclass(slots=True)
class RunActionDTO(_CommonActionDTO):
    process: core.action.AssociatedProcess | None = None
    description: str = ""


@dataclass(slots=True)
class UpgradeActionDTO(_CommonActionDTO):
    def __post_init__(self) -> None:
        if not self.launch.is_blocking:
            message = "Upgrade action can only be blocking"
            raise UseCaseError(message)

    def to_run_action_dto(self) -> RunActionDTO:
        return RunActionDTO(
            configuration=self.configuration,
            mapping=self.mapping,
            launch=self.launch,
        )
