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


def detect_path_for_file_in_bundle(bundle_root: Path, config_yaml_dir: str | Path, file: str) -> Path:
    """
    Detect path to file within bundle directory

    :param bundle_root: Path to bundle root directory (like */adcm/data/bundle/somebundlehash/*)
    :param config_yaml_dir: Directory containing *config.yaml* file with definition
                            of the object that file belongs to.
                            It is used when filename is specified in a "relative to config.yaml way":
                            staring with *"./"*.
                            May also be `""`, `"."`, `Path(".")`, `Path("")`
                            (which will be considered the same as for `Path` rules).
                            Those "empty" paths will make result equal for `file="./some.file"` and `file="some.file"`.
    :param file: Filename string as it's specified in object definition in bundle.

    >>> from pathlib import Path
    >>> bundle_root_dir = Path("/adcm/data/bundle") / "bundle-hash"
    >>> this = detect_path_for_file_in_bundle
    >>> str(this(bundle_root_dir, "", "./script.yaml")) == str((bundle_root_dir / "script.yaml").resolve())
    True
    >>> res = str(this(bundle_root_dir, ".", "./some/script.yaml"))
    >>> exp = str((bundle_root_dir / "some" /"script.yaml").resolve())
    >>> res == exp
    True
    >>> str(this(bundle_root_dir, Path(""), "script.yaml")) == str((bundle_root_dir / "script.yaml").resolve())
    True
    >>> res = str(this(bundle_root_dir, Path("inner"), "atroot/script.yaml"))
    >>> exp = str((bundle_root_dir / "atroot" / "script.yaml").resolve())
    >>> res == exp
    True
    >>> res = str(this(bundle_root_dir, Path("inner"), "./script.yaml"))
    >>> exp = str((bundle_root_dir / "inner" / "script.yaml").resolve())
    >>> res == exp
    True
    >>> res = str(this(bundle_root_dir, Path("inner"), "./alongside/script.yaml"))
    >>> exp = str((bundle_root_dir / "inner" / "alongside" / "script.yaml").resolve())
    >>> res == exp
    True
    """
    if file.startswith("./"):
        return (bundle_root / config_yaml_dir / file).resolve()

    return (bundle_root / file).resolve()
