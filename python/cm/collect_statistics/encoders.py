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

from cm.collect_statistics.types import Encoder


class TarFileEncoder(Encoder[Path]):
    """Encode and decode a file in place"""

    __slots__ = ("suffix",)

    def __init__(self, suffix: str) -> None:
        if suffix and not suffix.startswith(".") or suffix == ".":
            raise ValueError(f"Invalid suffix '{suffix}'")

        self.suffix = suffix

    def encode(self, path_file: Path) -> Path:
        encoded_data = bytearray((byte + 1) % 256 for byte in path_file.read_bytes())
        encoded_file = path_file.rename(path_file.parent / f"{path_file.name}{self.suffix}")
        encoded_file.write_bytes(encoded_data)
        return encoded_file

    def decode(self, path_file: Path) -> Path:
        if not path_file.name.endswith(self.suffix):
            raise ValueError(f"The file name must end with '{self.suffix}'")

        decoded_data = bytearray((byte - 1) % 256 for byte in path_file.read_bytes())
        decoded_file = path_file.rename(path_file.parent / path_file.name[: -len(self.suffix)])
        decoded_file.write_bytes(decoded_data)
        return decoded_file
