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
from typing import Any, Hashable
import warnings
import collections.abc

from ruyaml.error import ReusedAnchorWarning
import yaml

from core.bundle import parsing
from core.bundle._errors import BundleProcessingError


class FirstExplicitKeyLoader(yaml.SafeLoader):
    """
    Alternative Safe Loader that imitates ruyaml behavior
    in terms of overwritting keys, (when it's important for us)

    Code is copied from SafeLoader implementation with minor changes to ensure:
    1. First unique key in map stays, others are dropped silently
    2. Entries in mapping that came from anchors (<<: * syntax)
       have lower priority than "explicitly" defined.
       They are processed after "explicitly" defined
       => if they duplicate some key, they will be dropped.
    """

    def construct_mapping(self, node, deep: bool = False) -> dict[Hashable, Any]:
        if not isinstance(node, yaml.MappingNode):
            raise yaml.constructor.ConstructorError(
                None, None, "expected a mapping node, but found %s" % node.id, node.start_mark
            )

        self.flatten_mapping(node)

        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, collections.abc.Hashable):
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping", node.start_mark, "found unhashable key", key_node.start_mark
                )

            if key in mapping:
                continue

            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value

        return mapping

    def flatten_mapping(self, node):
        merge = []
        index = 0
        while index < len(node.value):
            key_node, value_node = node.value[index]
            if key_node.tag == "tag:yaml.org,2002:merge":
                del node.value[index]
                if isinstance(value_node, yaml.MappingNode):
                    self.flatten_mapping(value_node)
                    merge.extend(value_node.value)
                elif isinstance(value_node, yaml.SequenceNode):
                    submerge = []
                    for subnode in value_node.value:
                        if not isinstance(subnode, yaml.MappingNode):
                            raise yaml.constructor.ConstructorError(
                                "while constructing a mapping",
                                node.start_mark,
                                "expected a mapping for merging, but found %s" % subnode.id,
                                subnode.start_mark,
                            )
                        self.flatten_mapping(subnode)
                        submerge.append(subnode.value)
                    submerge.reverse()
                    for value in submerge:
                        merge.extend(value)
                else:
                    raise yaml.constructor.ConstructorError(
                        "while constructing a mapping",
                        node.start_mark,
                        "expected a mapping or list of mappings for merging, but found %s" % value_node.id,
                        value_node.start_mark,
                    )
            elif key_node.tag == "tag:yaml.org,2002:value":
                key_node.tag = "tag:yaml.org,2002:str"
                index += 1
            else:
                index += 1
        if merge:
            # the only changed line to change priority of anchors
            node.value += merge


def read_root_entries_from_yaml_file(path: Path) -> list[parsing.RootEntry]:
    content = _read_yaml_file(path)
    entries_data = _config_content_to_list(content)
    return [parsing.RootEntry(data=data, full_path_to_file=path) for data in entries_data]


def _read_yaml_file(path: Path) -> Any:
    warnings.simplefilter(action="error", category=ReusedAnchorWarning)
    content = path.read_text(encoding="utf-8")
    try:
        # Check is silenced, because Loader inherits from SafeLoader
        # and doesn't override important safe-related stuff
        return yaml.load(content, Loader=FirstExplicitKeyLoader)  # noqa: S506
    except yaml.error.YAMLError as e:
        message = f'Error during parsing yaml file at "{path}": {e}'
        raise BundleProcessingError(message) from e


def _config_content_to_list(config_file_content: Any) -> list[dict]:
    if isinstance(config_file_content, dict):
        return [config_file_content]

    if not isinstance(config_file_content, list):
        message = f"config.yaml contents are expected to be lists of dicts, not {type(config_file_content)}"
        raise BundleProcessingError(message)

    if not all(isinstance(e, dict) for e in config_file_content):
        message = "All entries in definitions list in config.yaml should be dictionaries"
        raise BundleProcessingError(message)

    return config_file_content
