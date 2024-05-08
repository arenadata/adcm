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

from itertools import chain
from pathlib import Path
from typing import Callable, TypeAlias
import os
import sys
import argparse

LICENSE = [
    'Licensed under the Apache License, Version 2.0 (the "License");',
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
]


IsLicensePresent: TypeAlias = bool
# amount of lines in header that are correct from checker perspective
CorrectHeaderLines: TypeAlias = int


class LicenseChecker:
    def __init__(self, comment_literal: str, on_absence: Callable):
        self._comment = comment_literal
        self._license_lines = [f"{f'{self._comment} {line}'.rstrip()}\n" for line in LICENSE]
        self._on_absence = on_absence

    def process(self, target: Path) -> IsLicensePresent:
        offset, missing_license_part = self._detect_missing_license_line(file=target)
        if not missing_license_part:
            return True

        self._on_absence(file=target, missing_part=missing_license_part, skip_lines=offset)

        return False

    def _detect_missing_license_line(self, file: Path) -> tuple[CorrectHeaderLines, list[str]]:
        with file.open(mode="r", encoding="utf-8") as unread_lines:
            offset_line = 0
            line = next(unread_lines, None)
            if not line:
                return offset_line, self._license_lines

            if line.startswith("#!"):
                # then it's a shebang, expect next comment to be license
                offset_line += 1
                line = next(unread_lines, None)
                if line is None:
                    # insert right after shebang
                    return offset_line, self._license_lines

                if line.strip() in ("", self._comment):
                    # if it's an empty line we'll just skip it
                    offset_line += 1
                    line = next(unread_lines, None)
                    if not line:
                        return offset_line, self._license_lines

            if line != self._license_lines[0]:
                return offset_line, self._license_lines + ["\n"]

            offset_line += 1

            lines_to_match = iter(self._license_lines[1:])
            for expected_line in lines_to_match:
                line = next(unread_lines, None)
                if line != expected_line:
                    return offset_line, [expected_line] + list(lines_to_match) + ["\n"]

                offset_line += 1

            last_line = next(unread_lines, None)
            if last_line in ("\n", None):
                return 0, []

            # This most likely mean there's no newline at the end of file.
            # It'll most likely "move" last line without newline at the end.
            # Unlikely scenario, but quite visible.
            return offset_line, ["\n"]


def do_nothing(*_, **__) -> None:
    return


def insert_missing_license(file: Path, missing_part: list[str], skip_lines: CorrectHeaderLines) -> None:
    # to get full correct path of header
    split_by = skip_lines
    with file.open(mode="r+", encoding="utf-8") as f:
        lines = f.readlines()
        f.seek(0)
        f.writelines(lines[:split_by] + missing_part + lines[split_by:])


def main():
    parser = argparse.ArgumentParser(description="Checker for licence existing and fix it if need")
    parser.add_argument(
        "--fix",
        nargs="?",
        const=True,
        default=False,
        help="Flag to fix absent license in file (default will only find it)",
    )
    parser.add_argument("--folders", nargs="+", help="Folders to check", type=Path)

    args = parser.parse_args()

    error_template = "License is absent in {} files."
    error_exit_code, on_absence_func = 0, do_nothing

    if args.fix:
        error_template = "License was updated in {} files."
        error_exit_code, on_absence_func = 1, insert_missing_license

    python_checker = LicenseChecker(comment_literal="#", on_absence=on_absence_func)
    go_checker = LicenseChecker(comment_literal="//", on_absence=on_absence_func)

    missing_license_counter = 0

    for checker, files in (
        (python_checker, chain.from_iterable(folder.rglob("**/*.py") for folder in args.folders)),
        (
            go_checker,
            chain.from_iterable(chain(folder.rglob("**/*.go"), folder.rglob("**/go.mod")) for folder in args.folders),
        ),
    ):
        for file in files:
            if not checker.process(file):
                sys.stdout.write(f"{file}:0 has no license or incomplete one{os.linesep}")
                missing_license_counter += 1

    if missing_license_counter == 0:
        sys.stdout.write(f"Licence is present in all python and go files {os.linesep}")
        sys.exit(0)

    sys.stdout.write(f"{error_template.format(missing_license_counter)}{os.linesep}")
    sys.exit(error_exit_code)


if __name__ == "__main__":
    main()
