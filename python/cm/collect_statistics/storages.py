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

from pydantic import BaseModel

from cm.collect_statistics.types import Storage


class JSONFile(BaseModel):
    filename: str
    data: dict


class TarFileWithJSONFileStorage(Storage[JSONFile]):
    def add(self, data: JSONFile) -> None:
        pass

    def gather(self) -> Path:
        pass


class TarFileWithTarFileStorage(Storage[Path]):
    def add(self, data: Path) -> None:
        pass

    def gather(self) -> Path:
        pass
