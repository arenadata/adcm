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
from typing import Protocol


class BasicLogInfo(Protocol):
    job_id: int
    name: str
    type: str
    format: str


def extract_log_content_from_fs(jobs_dir: Path, log_info: BasicLogInfo) -> str | None:
    logfile = jobs_dir / f"{log_info.job_id}" / f"{log_info.name}-{log_info.type}.{log_info.format}"
    if logfile.exists():
        return logfile.read_text(encoding="utf-8")

    return None
