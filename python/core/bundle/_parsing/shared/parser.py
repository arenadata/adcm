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

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, Iterable, TypeAlias, TypeVar

from pydantic import BaseModel

from core.bundle._definitions import DefinitionsMap
from core.bundle._errors import BundleParsingError, convert_validation_to_bundle_error
from core.bundle._parsing.types import BundleParser, RootEntry
from core.bundle._representation import repr_from_raw
from core.bundle._types import BundleDefinitionKey
from core.errors import localize_error

_RelativePath: TypeAlias = str

RootT = TypeVar("RootT", bound=BaseModel)
ObjectT = TypeVar("ObjectT", bound=BaseModel)


class PydanticParser(BundleParser, ABC, Generic[RootT, ObjectT]):
    @abstractmethod
    def _get_schema_mapping(self) -> dict[str, type[RootT]]:
        ...

    @abstractmethod
    def _flatten_definitions(self, definition: RootT) -> Iterable[tuple[BundleDefinitionKey, ObjectT]]:
        ...

    @abstractmethod
    def _convert_objects(
        self,
        definitions: dict[BundleDefinitionKey, ObjectT],
        relative_definition_paths: dict[BundleDefinitionKey, _RelativePath],
        bundle_root: Path,
    ) -> DefinitionsMap:
        ...

    # Implementation

    def parse_root_entries(
        self,
        entries: Iterable[RootEntry],
        bundle_root: Path,
    ) -> DefinitionsMap:
        parsed_definitions_map, definition_path_map = self._parse_objects(entries, bundle_root=bundle_root)
        return self._convert_objects(
            definitions=parsed_definitions_map, relative_definition_paths=definition_path_map, bundle_root=bundle_root
        )

    # Steps

    def _parse_objects(self, definition_path_pairs: Iterable[RootEntry], bundle_root: Path):
        definitions_map = {}
        paths_map = {}

        # ensure it's re-entrable
        pairs = tuple(definition_path_pairs)

        for pair in pairs:
            raw_definition = pair.data
            path_to_source = pair.full_path_to_file
            # todo add convertion func for localize_error
            with localize_error(f"In file: {path_to_source.relative_to(bundle_root)}", repr_from_raw(raw_definition)):
                root_level_definition = parse_root_entry(raw_definition, schema_map=self._get_schema_mapping())
                for key, parsed_definition in self._flatten_definitions(root_level_definition):
                    _check_is_not_duplicate(key, definitions_map)
                    definitions_map[key] = parsed_definition
                    paths_map[key] = str(path_to_source.relative_to(bundle_root).parent)

        return definitions_map, paths_map


@convert_validation_to_bundle_error
def parse_root_entry(definition: dict, schema_map: dict[str, type[RootT]]) -> RootT:
    try:
        def_type = definition["type"]
    except KeyError as e:
        raise BundleParsingError("Field `type` is missing: can't parse definition") from e

    try:
        core_model = schema_map[def_type]
    except KeyError as e:
        raise BundleParsingError(f'Value "{def_type}" is not allowed') from e

    return core_model.model_validate(definition, strict=True)


def _check_is_not_duplicate(key: BundleDefinitionKey, existing_entries: Iterable[BundleDefinitionKey]) -> None:
    if key in existing_entries:
        raise BundleParsingError(f"Duplicate definition of {key}")
