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

from dataclasses import dataclass
import os
import signal

from core.result import Fail, Success


@dataclass(slots=True)
class TaskRunnerTerminator:
    """
    Wrapper for sending correct termination signals for task runner process
    """

    def terminate(self, pid: int) -> Success[None] | Fail[str]:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as e:
            return Fail(f"failed to terminate process: {e}")

        return Success(None)


@dataclass(slots=True)
class ExecutorTerminator:
    """
    Wrapper for sending correct termination signals for ansible/python executor process
    """

    def terminate(self, pid: int) -> Success[None] | Fail[str]:
        try:
            pgroup = os.getpgid(pid)
            os.killpg(pgroup, signal.SIGTERM)
        except OSError as e:
            return Fail(f"failed to terminate process: {e}")

        return Success(None)
