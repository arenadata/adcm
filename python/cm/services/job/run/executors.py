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

from pathlib import Path
from typing import Callable

from core.job.executors import (
    BundleExecutorConfig,
    ExecutionResult,
    Executor,
    ExecutorConfig,
    ProcessExecutor,
    WithErrOutLogsMixin,
)
from typing_extensions import Self

from cm.errors import AdcmEx
from cm.utils import get_env_with_venv_path


class AnsibleExecutorConfig(BundleExecutorConfig):
    ansible_secret_script: Path
    tags: str
    verbose: bool
    venv: str


class AnsibleProcessExecutor(ProcessExecutor):
    script_type = "ansible"

    _config: AnsibleExecutorConfig

    def __init__(self, config: AnsibleExecutorConfig):
        super().__init__(config=config)

    def _prepare_command(self) -> list[str]:
        playbook = self._config.script_file
        cmd = [
            "ansible-playbook",
            "--vault-password-file",
            str(self._config.ansible_secret_script),
            "-e",
            f"@{self._config.work_dir}/config.json",
            "-i",
            f"{self._config.work_dir}/inventory.json",
            playbook,
        ]

        if self._config.tags:
            cmd.append(f"--tags={self._config.tags}")

        if self._config.verbose:
            cmd.append("-vvvv")

        return cmd

    def _get_environment_variables(self) -> dict:
        env = super()._get_environment_variables()

        env = get_env_with_venv_path(venv=self._config.venv, existing_env=env)

        # This condition is intended to support compatibility.
        # Since older bundle versions may contain their own ansible.cfg
        if not Path(self._config.bundle_root, "ansible.cfg").is_file():
            env["ANSIBLE_CONFIG"] = str(self._config.work_dir / "ansible.cfg")

        return env


class PythonProcessExecutor(ProcessExecutor):
    script_type = "python"

    def _prepare_command(self) -> list[str]:
        return ["python", self._config.script_file]


class InternalExecutor(Executor, WithErrOutLogsMixin):
    script_type = "internal"

    def __init__(self, config: ExecutorConfig, script: Callable[[], int]):
        super().__init__(config=config)
        self._script = script

    def execute(self) -> Self:
        self._open_logs(log_dir=self._config.work_dir, log_prefix=self.script_type)

        try:
            return_code = self._script()
        except AdcmEx as err:
            self._err_log.write(err.msg)
            return_code = 1

        self._result = ExecutionResult(code=return_code)

        return self

    def wait_finished(self) -> Self:
        return self
