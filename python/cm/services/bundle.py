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

from abc import ABC
from pathlib import Path

from django.conf import settings


def detect_relative_path_to_bundle_root(source_file_dir: str | Path, raw_path: str) -> Path:
    """
    :param source_file_dir: Directory with file where given `path` is defined
    :param raw_path: Path to resolve

    >>> from pathlib import Path
    >>> this = detect_relative_path_to_bundle_root
    >>> this("", "./script.yaml") == Path("script.yaml")
    True
    >>> str(this(".", "./some/script.yaml")) == "some/script.yaml"
    True
    >>> str(this(Path(""), "script.yaml")) == "script.yaml"
    True
    >>> str(this(Path("inner"), "atroot/script.yaml")) == "atroot/script.yaml"
    True
    >>> str(this(Path("inner"), "./script.yaml")) == "inner/script.yaml"
    True
    >>> str(this(Path("inner"), "./alongside/script.yaml")) == "inner/alongside/script.yaml"
    True
    """
    if raw_path.startswith("./"):
        return Path(source_file_dir) / raw_path

    return Path(raw_path)


def is_path_correct(raw_path: str) -> bool:
    """
    Return whether given path meets ADCM path description requirements

    >>> this = is_path_correct
    >>> this("relative_to_bundle/path.yaml")
    True
    >>> this("./relative/to/file.yaml")
    True
    >>> this(".secret")
    True
    >>> this("../hack/system")
    False
    >>> this("/hack/system")
    False
    >>> this(".././hack/system")
    False
    >>> this("../../hack/system")
    False
    """
    return raw_path.startswith("./") or not raw_path.startswith(("..", "/"))


class PathResolver(ABC):
    __slots__ = ("_root",)

    _root: Path

    @property
    def bundle_root(self) -> Path:
        return self._root

    def resolve(self, path: str | Path) -> Path:
        return self._root / path


class BundlePathResolver(PathResolver):
    def __init__(self, bundle_hash: str):
        self._root = settings.BUNDLE_DIR / bundle_hash


class ADCMBundlePathResolver(PathResolver):
    def __init__(self):
        self._root = settings.BASE_DIR / "conf" / "adcm"
