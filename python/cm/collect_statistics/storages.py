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
from tempfile import mkdtemp
import io
import json
import tarfile
import datetime

from pydantic import BaseModel

from cm.collect_statistics.errors import StorageError
from cm.collect_statistics.types import Storage


class JSONFile(BaseModel):
    filename: str
    data: dict


class TarFileWithJSONFileStorage(Storage[JSONFile]):
    def __init__(self, compresslevel=9, timeformat="%Y-%m-%d"):
        self.json_files = []
        self.tmp_dir = Path(mkdtemp()).absolute()
        self.compresslevel = compresslevel
        self.timeformat = timeformat

    def add(self, data: JSONFile) -> None:
        """
        Adds a JSON file to the storage.

        Args:
            data (JSONFile): The JSON file to add.
        """
        if not isinstance(data, JSONFile):
            raise StorageError(f"Expected JSONFile, got {type(data)}")

        if len(data.data) == 0:
            return

        self.json_files.append(data)

    def gather(self) -> Path:
        """
        Generates a tarball archive containing JSON files.

        This function creates a tarball archive named "{today_date}_statistics_full.tgz"
        using the current date. It iterates over the JSON files stored in the `json_files`
        list and adds each file to the tarball. The file name and size are set using the
        `tarfile.TarInfo` object. The contents of each JSON file are encoded as UTF-8 and
        added to the tarball using `tarfile.addfile`.

        Returns:
            Path: The path to the generated tarball archive.
        """
        if not self:
            raise StorageError("No JSON files to gather")

        today_date = datetime.datetime.now(tz=datetime.timezone.utc).strftime(self.timeformat)
        archive_name = self.tmp_dir / f"{today_date}_statistics_full.tgz"
        archive_path = Path(archive_name)

        with tarfile.open(archive_name, "w:gz", compresslevel=self.compresslevel) as tar:
            for json_file in self:
                data = json.dumps(obj=json_file.data).encode("utf8")
                tgz_info = tarfile.TarInfo(name=json_file.filename)
                tgz_info.size = len(data)
                tar.addfile(tgz_info, io.BytesIO(data))

        return archive_path

    def clear(self) -> None:
        self.json_files = []

    def __bool__(self) -> bool:
        return bool(self.json_files)

    def __len__(self) -> int:
        return len(self.json_files)

    def __iter__(self) -> iter:
        return iter(self.json_files)
