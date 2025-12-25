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


from typing import Mapping
import os


class _Flag:
    __slots__ = ("header", "env")

    def __init__(self, flag: str) -> None:
        self.header = flag
        self.env = flag.replace("-", "_").upper()


FLAG_JOB_SCHEDULER = _Flag("feature-job-scheduler")
FLAG_CONFIG_PROCESSING = _Flag("feature-config-processing")


def use_new_spec_format(headers: Mapping | None = None) -> bool:
    return use_new_config_processing(headers=headers)


def use_new_job_scheduler() -> bool:
    return os.environ.get(FLAG_JOB_SCHEDULER.env) == "new"


def use_new_config_processing(headers: Mapping | None = None) -> bool:
    _ = headers
    return True
