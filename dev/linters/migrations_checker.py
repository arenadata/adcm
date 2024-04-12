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

from enum import Enum
from pathlib import Path
from typing import Iterable, NamedTuple
import os
import ast
import sys
import argparse

ALLOWED_IMPORTS = (
    "ansible",
    "datetime",
    "django",
    "hashlib",
    "json",
    "operator",
    "os",
    "pathlib",
    "typing",
    "uuid",
)


class Outcome(Enum):
    OK = "ok"
    ERROR = "error"


class CheckResult(NamedTuple):
    file: Path
    outcome: Outcome
    comment: str


def find_migration_files(root: Path) -> Iterable[Path]:
    return filter(Path.is_file, root.rglob("**/migrations/*.py"))


def check_files(migration_files: Iterable[Path]) -> Iterable[CheckResult]:
    for file in migration_files:
        parsed = ast.parse(file.read_text())
        errors = tuple(check_imports(module=parsed))
        if not errors:
            yield CheckResult(file=file, outcome=Outcome.OK, comment="")
            continue

        for incorrect_node, disallowed_imports in errors:
            line_info = f"{file}:{incorrect_node.lineno}"
            yield CheckResult(
                file=file,
                outcome=Outcome.ERROR,
                comment=f"{line_info} - Not allowed imports: {', '.join(disallowed_imports)}",
            )


def check_imports(module: ast.Module) -> Iterable[tuple[ast.Import | ast.ImportFrom, tuple[str, ...]]]:
    for import_node in filter(lambda node: isinstance(node, (ast.Import, ast.ImportFrom)), ast.walk(module)):
        if isinstance(import_node, ast.Import):
            roots = (import_.name.split(".")[0] for import_ in import_node.names)
        else:
            roots = (import_node.module.split(".")[0],)

        disallowed_imports = tuple(root for root in roots if root not in ALLOWED_IMPORTS)
        if disallowed_imports:
            yield import_node, disallowed_imports


def main():
    parser = argparse.ArgumentParser(description='Checker for migrations ("foreign" imports)')
    parser.add_argument("root", help="Directory to search from", type=Path)
    args = parser.parse_args()

    if not args.root.is_dir():
        sys.stdout.write(f"Not a directory: {args.root}")
        sys.exit(2)

    fails = list(
        filter(
            lambda result: result.outcome == Outcome.ERROR,
            check_files(migration_files=find_migration_files(root=args.root)),
        )
    )

    if fails:
        sys.stdout.write(f"Some files [{len(fails)}] contain foreign foreign imports:{os.linesep}")
        sys.stdout.write(os.linesep.join(result.comment for result in fails))
        sys.stdout.write(os.linesep)
        sys.exit(1)


if __name__ == "__main__":
    main()
