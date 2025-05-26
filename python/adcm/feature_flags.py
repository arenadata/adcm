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


FLAG_BUNDLE_UPLOAD = _Flag("feature-bundle-upload")
FLAG_CONFIG_SPEC = _Flag("feature-config-spec")
FLAG_JOB_SCHEDULER = _Flag("feature-job-scheduler")


def use_new_bundle_parsing_approach(env: Mapping[str, str], headers: Mapping[str, str]) -> bool:
    flag = headers.get(FLAG_BUNDLE_UPLOAD.header) or env.get(FLAG_BUNDLE_UPLOAD.env)
    return flag == "new"


def use_new_spec_format() -> bool:
    return os.environ.get(FLAG_CONFIG_SPEC.env) == "new"


def use_new_job_scheduler() -> bool:
    return os.environ.get(FLAG_JOB_SCHEDULER.env) == "new"
