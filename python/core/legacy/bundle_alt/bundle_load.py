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
import hashlib
import tarfile

from core.legacy.bundle_alt.errors import BundleProcessingError, BundleValidationError


def get_config_files(path: Path) -> list[tuple[Path, Path]]:
    conf_list = []
    valid_suffixes = {".yaml", ".yml"}

    for item in path.rglob("config.y*ml"):
        if item.is_file() and item.suffix in valid_suffixes:
            conf_list.append((item.relative_to(path), item))

    if not conf_list:
        raise BundleValidationError(f'No config files in stack directory "{path}"')

    return conf_list


def untar_safe(to: Path, tar_from: Path) -> None:
    try:
        with tarfile.open(tar_from) as tar:
            resolved_to = to.resolve()
            for member in tar.getmembers():
                target_path = (resolved_to / member.name).resolve()
                if not str(target_path).startswith(str(resolved_to)):
                    raise BundleProcessingError("Incorrect paths were found in the file")

                if member.issym():
                    link_target = member.linkname

                    abs_link_target = (target_path.parent / link_target).resolve()
                    if not str(abs_link_target).startswith(str(resolved_to)):
                        raise BundleProcessingError("Incorrect paths were found in the file")

                tar.extract(member, path=to, set_attrs=True)
    except tarfile.ReadError as e:
        raise BundleProcessingError(f"Can't open bundle tar file: {tar_from}") from e


def get_hash_safe(path: Path) -> str:
    sha1 = hashlib.sha1()  # noqa: S324
    with open(path, mode="rb") as f:
        for data in iter(lambda: f.read(16384), b""):
            sha1.update(data)

    return sha1.hexdigest()
