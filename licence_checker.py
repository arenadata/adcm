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

import sys
import os
import argparse
from pathlib import Path

APACHE_LICENCE = ['Licensed under the Apache License, Version 2.0 (the "License");',
                  "you may not use this file except in compliance with the License.",
                  "You may obtain a copy of the License at",
                  "",
                  "     http://www.apache.org/licenses/LICENSE-2.0",
                  "",
                  "Unless required by applicable law or agreed to in writing, software",
                  'distributed under the License is distributed on an "AS IS" BASIS,',
                  "WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.",
                  "See the License for the specific language governing permissions and",
                  "limitations under the License.",
                  "\n"]


def check_licence(file, fix) -> bool:
    """Return False in case of empty licence"""
    try:
        with open(file, "r+", encoding="utf-8") as f:
            lines = f.readlines()
    except PermissionError:
        sys.stdout.write(f"file {file} unreachable \n")
        return False
    if len(lines) < 10:
        return False
    if (lines[0].find(APACHE_LICENCE[0]) != -1) or (lines[1].find(APACHE_LICENCE[0]) != -1):
        if (lines[10].find(APACHE_LICENCE[10]) != -1) \
                or (lines[11].find(APACHE_LICENCE[10]) != -1):
            return True
    if fix:
        update_files(file, lines)
    return False


def read_files(fix: bool, root: str = "") -> list:
    root_path = Path(root)
    result = []
    for path in os.listdir(root_path):
        path = os.path.join(root_path, path)
        if os.path.isdir(path):
            result.extend(read_files(fix, path))
        if os.path.isfile(path) and (
                path.endswith(".py") or path.endswith(".go") or path.endswith("go.mod")
        ):
            if not check_licence(path, fix):
                result.append(path)
    return result


def update_files(file: str, lines: list):
    new_line = "\n"
    separator = "# " if file.endswith(".py") else "// "
    with open(file, "w", encoding="utf-8") as f:
        lines.insert(0, f'{separator}{f"{new_line}{separator}".join(APACHE_LICENCE)}{new_line}')
        f.writelines(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Checker for licence existing and fix it if need")
    parser.add_argument("--fix", nargs="?", const=True, default=False,
                        help="Flag to fix absent license in file (default will only find it)")
    parser.add_argument("--folders", nargs="+", help="Folders to check")
    args = parser.parse_args()
    empty_licence = []
    for folder in args.folders:
        empty_licence.extend(read_files(args.fix, folder))
    if empty_licence:
        sys.stdout.write(
            f"Licence not detected in the following files: {', '.join(empty_licence)} \n"
        )
        if args.fix:
            sys.stdout.write(f"{len(empty_licence)} was updated with the licence. \n")
        sys.exit(1)
    else:
        sys.stdout.write("Licence is present in all python and go files \n")
        sys.exit(0)
