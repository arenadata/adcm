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
from typing import Callable, Collection

from cm.models import LogStorage
from core.types import CoreObjectDescriptor
from django.db.transaction import atomic
from pydantic import model_validator
from typing_extensions import Self

from ansible_plugin.base import (
    ADCMAnsiblePluginExecutor,
    ArgumentsConfig,
    BaseStrictModel,
    CallResult,
    PluginExecutorConfig,
    RuntimeEnvironment,
)
from ansible_plugin.utils import assign_view_logstorage_permissions_by_job


class CustomLogArguments(BaseStrictModel):
    name: str
    format: str
    path: Path | None = None
    content: str | None = None

    @model_validator(mode="after")
    def check_either_is_specified(self) -> Self:
        if self.path is None and self.content is None:
            message = "either `path` or `content` has to be specified"
            raise ValueError(message)

        return self


class ADCMCustomLogPluginExecutor(ADCMAnsiblePluginExecutor[CustomLogArguments, None], ABC):
    _config = PluginExecutorConfig(
        arguments=ArgumentsConfig(represent_as=CustomLogArguments),
    )

    def __call__(
        self,
        targets: Collection[CoreObjectDescriptor],
        arguments: CustomLogArguments,
        runtime: RuntimeEnvironment,
    ) -> CallResult[None]:
        _ = targets

        body = arguments.content
        if arguments.path:
            body = self.retrieve_from_path(arguments.path)

        with atomic():
            log = LogStorage.objects.create(
                job_id=runtime.vars.job.id, name=arguments.name, type="custom", format=arguments.format, body=body
            )
            assign_view_logstorage_permissions_by_job(log_storage=log)

        return CallResult(value=None, changed=False, error=None)

    def __class_getitem__(cls, item: Callable[[Self, Path], str]):
        class ConfiguredADCMCustomLogPluginExecutor(cls):
            def retrieve_from_path(self, path: Path) -> str:
                return item(self, path)

        return ConfiguredADCMCustomLogPluginExecutor

    @abstractmethod
    def retrieve_from_path(self, path: Path) -> str:
        """
        This function will be called if `path` is specified in arguments
        in priority to `content` either it's specified or not.

        Executor implementations can be either subclassed and implemented
        or build with `ADCMCustomLogPluginExecutor[retrieve_from_path_implementation]`
        """
