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
from typing import Final
import hashlib
import tarfile

from core.bundle._errors import BundleProcessingError

_VALID_SUFFIXES: Final = {".yaml", ".yml"}
_TAR_READ_CHUNK_SIZE: Final = 16384


def get_config_files(path: Path) -> tuple[Path, ...]:
    config_files = tuple(filter(_is_config_file, path.rglob("config.y*ml")))

    if not config_files:
        raise BundleProcessingError(f'No config files in stack directory "{path}"')

    return config_files


def untar_safe(to: Path, tar_from: Path) -> Path:
    try:
        with tarfile.open(tar_from) as tar:
            safe_root = to.resolve()
            for member in tar.getmembers():
                member_path = (safe_root / member.name).resolve()
                if not _is_path_safe(member_path, safe_root):
                    raise BundleProcessingError("Incorrect paths were found in the file")

                _check_member_symlink(member, member_path, safe_root)

                tar.extract(member, path=to, set_attrs=True)

    except tarfile.ReadError as e:
        raise BundleProcessingError(f"Can't open bundle tar file: {tar_from}") from e

    return to


def get_hash_safe(path: Path) -> str:
    sha1 = hashlib.sha1()  # noqa: S324
    with open(path, mode="rb") as f:
        for data in iter(lambda: f.read(_TAR_READ_CHUNK_SIZE), b""):
            sha1.update(data)

    return sha1.hexdigest()


def _is_config_file(path: Path) -> bool:
    return path.is_file() and path.suffix in _VALID_SUFFIXES


def _is_path_safe(member_path: Path, safe_root: Path) -> bool:
    return member_path.is_relative_to(safe_root)


def _check_member_symlink(member: tarfile.TarInfo, target_path: Path, safe_root: Path) -> None:
    if not member.issym():
        return

    try:
        abs_link_target = (target_path.parent / member.linkname).resolve()
    except RuntimeError as e:
        raise BundleProcessingError(f"Failed to resolve symlink target for {member.name}: {e}") from e

    if not _is_path_safe(abs_link_target, safe_root):
        raise BundleProcessingError(f"Symlink `{member.name}` points outside the extraction directory!")
