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

"""Storage format of an execution plan: how a spec is put into a JSON column and taken back"""

from typing import Any, Final

from core.action.types import JobSpecV1

STORED_VERSION: Final = 1
"""
Version of the stored format, not of the spec type.

It exists so that a plan written by an older ADCM can be recognized as such
instead of being fed to whatever `JobSpecV1` happens to look like today.
"""

_VERSION_KEY: Final = "version"


class UnsupportedExecutionPlanError(Exception):
    """Stored execution plan can't be read by this version of ADCM"""


def dump_execution_plan(spec: JobSpecV1) -> dict[str, Any]:
    return {_VERSION_KEY: STORED_VERSION, **spec.model_dump(mode="json")}


def parse_execution_plan(stored: dict[str, Any]) -> JobSpecV1:
    """Read a stored plan, refusing formats this version doesn't know"""

    version = stored.get(_VERSION_KEY)

    match version:
        case 1:
            # the version belongs to the envelope, not to the spec
            return JobSpecV1.model_validate({key: value for key, value in stored.items() if key != _VERSION_KEY})
        case _:
            message = f"Can't read execution plan of version {version!r}, {STORED_VERSION} is expected"
            raise UnsupportedExecutionPlanError(message)
