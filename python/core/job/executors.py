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
from typing import Any, NamedTuple, TextIO
import os
import subprocess

from pydantic import BaseModel
from typing_extensions import Self


class ExecutionResult(NamedTuple):
    code: int


class WithErrOutLogsMixin:
    _out_log: TextIO | None = None
    _err_log: TextIO | None = None

    def _open_logs(self, log_dir: Path, log_prefix: str) -> None:
        self._out_log = (log_dir / f"{log_prefix}-stdout.txt").open(mode="a+", encoding="utf-8")
        self._err_log = (log_dir / f"{log_prefix}-stderr.txt").open(mode="a+", encoding="utf-8")

    def _close_logs(self) -> None:
        if self._out_log:
            self._out_log.close()

        if self._err_log:
            self._err_log.close()


class ExecutorConfig(BaseModel):
    work_dir: Path


class BundleExecutorConfig(ExecutorConfig):
    script_file: Path
    bundle_root: Path


class Executor(ABC):
    _config: ExecutorConfig
    _result: ExecutionResult | None
    _process: Any | None

    @property
    @abstractmethod
    def script_type(self) -> str:
        raise NotImplementedError()

    @property
    def result(self) -> ExecutionResult | None:
        return self._result

    @property
    def process(self):
        return self._process

    def __init__(self, config: ExecutorConfig):
        self._config = config
        self._result = None
        self._process = None

    @abstractmethod
    def execute(self) -> Self:
        raise NotImplementedError()

    @abstractmethod
    def wait_finished(self) -> Self:
        raise NotImplementedError()


class ProcessExecutor(Executor, WithErrOutLogsMixin, ABC):
    _config: BundleExecutorConfig
    _process: subprocess.Popen | None

    def __init__(self, config: BundleExecutorConfig) -> None:
        super().__init__(config=config)

        self._process = None

    def execute(self) -> Self:
        command = self._prepare_command()
        environment = self._get_environment_variables()

        self._open_logs(log_dir=self._config.work_dir, log_prefix=self.script_type)

        os.chdir(self._config.bundle_root)
        self._process = subprocess.Popen(
            command,  # noqa S603
            env=environment,
            stdout=self._out_log,
            stderr=self._err_log,
        )

        return self

    def wait_finished(self) -> Self:
        return_code = self._process.wait()
        self._result = ExecutionResult(code=return_code)

        self._close_logs()

        return self

    @abstractmethod
    def _prepare_command(self) -> list[str]:
        raise NotImplementedError()

    def _get_environment_variables(self) -> dict:
        env = os.environ.copy()
        env["PYTHONPATH"] = f"./pmod:{self._config.bundle_root}/pmod:{env.get('PYTHONPATH', '')}".rstrip(":")

        return env
