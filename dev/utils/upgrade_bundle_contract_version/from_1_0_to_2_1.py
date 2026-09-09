#!/usr/bin/env python3

from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Final, Hashable, TypeAlias
import collections.abc

import yaml

VALID_SUFFIXES: Final = {".yaml", ".yml"}
Successfully: TypeAlias = list[Path]
NotSuccessfully: TypeAlias = list[tuple[str, Path]]


class NotFoundConfigFileError(Exception):
    ...


class ParseConfigFileError(Exception):
    ...


class EmptyConfigFileError(Exception):
    ...


class ContractVersionIsDefinedError(Exception):
    ...


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


class IndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):  # noqa: ARG002
        return super().increase_indent(flow=flow, indentless=False)


def _is_config_file(path: Path) -> bool:
    return path.is_file() and path.suffix in VALID_SUFFIXES


def get_config_files(path: Path) -> tuple[Path, ...]:
    config_files = tuple(filter(_is_config_file, path.rglob("config.y*ml")))

    if not config_files:
        raise NotFoundConfigFileError(f'No config files in stack directory "{path}"')

    return config_files


def read_yaml_file(path: Path) -> Any:
    # warnings.simplefilter(action="error", category=ReusedAnchorWarning)
    content = path.read_text(encoding="utf-8")
    try:
        # Check is silenced, because Loader inherits from SafeLoader
        # and doesn't override important safe-related stuff
        return yaml.load(content, Loader=FirstExplicitKeyLoader)  # noqa: S506
    except yaml.error.YAMLError as e:
        message = f'Error during parsing yaml file at "{path}": {e}'
        raise ParseConfigFileError(message) from e


def pop_deprecate_action_field(action: dict) -> None:
    action.pop("log_files", None)
    action.pop("venv", None)


def replace_deprecate_action_field(action_name: str, action: dict) -> None:
    action_type = action.pop("type", None)

    if action_type == "job":
        script = action.pop("script")
        script_type = action.pop("script_type")
        params = action.pop("params", None)
        script_item = {
            "name": action_name,
            "script": script,
            "script_type": script_type,
        }

        if params is not None:
            script_item["params"] = params

        action["scripts"] = [script_item]

    if action_type == "task" and "params" in action:
        params = action.pop("params")
        for script_item in action.get("scripts", []):
            script_item["params"] = params

    config_jinja = action.pop("config_jinja", None)

    if config_jinja is not None:
        action["config_template"] = {"file": {"path": config_jinja}, "engine": {"type": "jinja2"}}

    scripts_jinja = action.pop("scripts_jinja", None)

    if scripts_jinja is not None:
        action["scripts_template"] = {"file": {"path": scripts_jinja}, "engine": {"type": "jinja2"}}


def upgrade_bundle_to_2_1_contract_version(config_file: Path, force: bool):
    content = read_yaml_file(config_file)

    if content is None:
        raise EmptyConfigFileError("config.yaml is empty")

    for item in content:
        if item["type"] in {"cluster", "provider", "adcm"}:
            if "contract_version" in item and not force:
                raise ContractVersionIsDefinedError(f"contract version is defined: {item['contract_version']}")

            item["contract_version"] = "2.1"
            item["venv"] = "2.16"

            for upgrade_item in item.get("upgrade", []):
                upgrade_item.pop("venv", None)

        for action_name, action in item.get("actions", {}).items():
            replace_deprecate_action_field(action_name, action)
            pop_deprecate_action_field(action)

            if item["type"] in {"provider", "host"}:
                action.pop("host_action", None)

        if item["type"] == "service":
            item.pop("shared", None)

            if "components" in item:
                for component in item["components"].values():
                    if component is not None:
                        component.pop("bound_to", None)
                        component.pop("params", None)
                        for component_action_name, component_action in component.get("actions", {}).items():
                            replace_deprecate_action_field(component_action_name, component_action)
                            pop_deprecate_action_field(component_action)

    with config_file.open("w", encoding="utf-8") as f:
        yaml.dump(content, f, sort_keys=False, explicit_start=True, Dumper=IndentDumper)


def upgrade_bundles(path: Path, force: bool) -> tuple[Successfully, NotSuccessfully]:
    config_files = get_config_files(path)

    successfully = []
    not_successfully = []

    for config_file in config_files:
        try:
            upgrade_bundle_to_2_1_contract_version(config_file, force)
        except (ParseConfigFileError, EmptyConfigFileError, ContractVersionIsDefinedError) as error:
            not_successfully.append((str(error), config_file))
        else:
            successfully.append(config_file)

    return successfully, not_successfully


def main():
    description = "Upgrade config.yaml from 1.0 to 2.1 contract_version"
    parser = ArgumentParser(description=description)
    parser.add_argument("directory", type=Path, help="directory with config.yaml files to upgrade.")
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        default=False,
        help="update even if contract_version is specified.",
    )

    args = parser.parse_args()
    directory = args.directory
    force = args.force

    successfully, not_successfully = upgrade_bundles(path=directory, force=force)
    msg_successfully = "\n    \u25AA ".join([str(path.absolute()) for path in successfully])
    print(f"  \u2705 Successfully upgraded bundles:\n    \u25AA {msg_successfully}")
    msg_not_successfully = "\n    \u25AA ".join(
        [f"{error} \u27A1 {str(path.absolute())}" for error, path in not_successfully]
    )
    print(f"  \u274C Not Successfully upgraded bundles:\n    \u25AA {msg_not_successfully}")


if __name__ == "__main__":
    main()
