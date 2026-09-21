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
from typing import Any, Final, Literal, TypeAlias
from unittest import TestCase

from pydantic import TypeAdapter
import yaml

from core.action import ScriptType
from core.action.types import (
    AnsibleScript,
    AnsibleScriptParams,
    ExecutionStyle,
    GroupSpec,
    JobDetails,
    JobSpecV1,
    ScriptSpec,
    SimpleInternalScript,
)
from core.bundle._definitions import DefinitionsMap
from core.bundle._errors import BundleParsingError, BundleValidationError
from core.bundle._parsing import v_2_1
from core.bundle._parsing.types import RootEntry
from core.bundle._parsing.v_2_1.scripts import ClusterEntry, detect_entry_kind
from core.bundle._validate import check_actions, check_upgrades
from core.spec.types import FullSpecKey
from core.types import Names

BUNDLE_ROOT: Final = Path(__file__).parent
FILE_IN_ROOT: Final = BUNDLE_ROOT / "config.yaml"

ContractVersion: TypeAlias = Literal["2.1"]
ScriptsMode: TypeAlias = Literal["action", "upgrade", "wizard"]
# places groups restrictions are checked in, restrictions don't depend on object type
Place: TypeAlias = Literal["cluster action", "static upgrade", "rendered upgrade"]

ACTION_NAME: Final = "grouped"
UPGRADE_NAME: Final = "grouped_upgrade"

# expected parts of messages, script name goes before this one
BUNDLE_CHANGING_SCRIPT_IN_GROUP_ERROR: Final = "script isn't allowed inside groups"
ALTERNATION_ERROR: Final = "Nested groups must alternate execution style"
DEPTH_ERROR: Final = "levels of groups at most"
# group key goes before this one, required amount after it
TOO_FEW_ENTRIES_ERROR: Final = "has to contain at least"

# Templates

# root object of any type without contract version and actions, those are added by `with_*` functions
OBJECT: Final = """
type: {type}
name: {name}
version: "2"
venv: "2.21"
"""

GROUPED_SCRIPTS: Final = """
- name: pre_check
  display_name: "Pre-check"
  script_type: ansible
  script: ansible/pre_check.yaml

- group: parallel
  name: shards
  display_name: "Shards"
  scripts:
    - group: sequential
      name: shard_a
      display_name: "Shard A"
      scripts:
        - name: stop_a
          script_type: ansible
          script: ansible/stop.yaml
        - name: reconfigure_a
          script_type: ansible
          script: ansible/cfg.yaml
        - name: start_a
          script_type: ansible
          script: ansible/start.yaml

    - group: sequential
      name: shard_b
      display_name: "Shard B"
      scripts:
        - name: stop_b
          script_type: ansible
          script: ansible/stop.yaml
        - name: reconfigure_b
          script_type: ansible
          script: ansible/cfg.yaml
        - name: start_b
          script_type: ansible
          script: ansible/start.yaml

- name: finalize
  display_name: "Finalize"
  script_type: ansible
  script: ansible/finalize.yaml
"""

# upgrades require exactly one `bundle_switch`, which isn't allowed inside groups
UPGRADE_SWITCH_SCRIPT: Final = """
name: switch
script_type: internal
script: bundle_switch
"""

SIMPLE_SCRIPT: Final = """
name: simple
script_type: ansible
script: simple.yaml
"""

# the shape groups had before ADCM-8467 flattened them, kept here to prove it's rejected outright
NESTED_GROUP: Final = """
- group:
    type: parallel
    name: shards
    scripts:
      - name: simple
        script_type: ansible
        script: simple.yaml
"""


# Definitions building


def load(template: str) -> Any:
    return yaml.safe_load(template)


def build_object(type_: Literal["cluster", "service", "provider", "host", "adcm"], name: str) -> dict:
    return load(OBJECT.format(type=type_, name=name))


def build_group(name: str, scripts: list[dict], type_: str = "parallel") -> dict:
    return {"group": type_, "name": name, "scripts": scripts}


def grouped_scripts() -> list[dict]:
    return load(GROUPED_SCRIPTS)


def grouped_upgrade_scripts() -> list[dict]:
    return [*grouped_scripts(), load(UPGRADE_SWITCH_SCRIPT)]


def with_contract_version(entry: dict, contract_version: ContractVersion) -> dict:
    return entry | {"contract_version": contract_version}


def with_action(entry: dict, scripts: list[dict], **action_fields: Any) -> dict:
    actions = entry.get("actions") or {}
    return entry | {"actions": actions | {ACTION_NAME: {"scripts": scripts, **action_fields}}}


def with_upgrade(entry: dict, scripts: list[dict]) -> dict:
    upgrade = {
        "name": UPGRADE_NAME,
        "versions": {"min": "0", "max": "1"},
        "states": {"available": "any"},
        "scripts": scripts,
    }
    return entry | {"upgrade": [*(entry.get("upgrade") or ()), upgrade]}


def with_component(service: dict, name: str, component: dict) -> dict:
    components = service.get("components") or {}
    return service | {"components": components | {name: component}}


def build_bundles(contract_version: ContractVersion) -> dict[str, list[dict]]:
    """Bundles with grouped scripts in every place scripts can be declared at"""

    cluster = with_contract_version(build_object("cluster", "cluster"), contract_version)
    cluster = with_action(cluster, grouped_scripts())
    cluster = with_upgrade(cluster, grouped_upgrade_scripts())

    service = with_action(build_object("service", "service"), grouped_scripts())
    service = with_component(service, name="component", component=with_action({}, grouped_scripts()))

    provider = with_contract_version(build_object("provider", "provider"), contract_version)
    provider = with_action(provider, grouped_scripts())
    provider = with_upgrade(provider, grouped_upgrade_scripts())

    host = with_action(build_object("host", "host"), grouped_scripts())

    adcm = with_contract_version(build_object("adcm", "adcm"), contract_version)
    adcm = with_action(adcm, grouped_scripts())

    return {"cluster": [cluster, service], "provider": [provider, host], "adcm": [adcm]}


def to_root_entries(bundle: list[dict]) -> list[RootEntry]:
    return [RootEntry(data=entry, full_path_to_file=FILE_IN_ROOT) for entry in bundle]


def collect_scripts_specs(definitions: DefinitionsMap) -> dict[str, JobSpecV1]:
    """Scripts of every action and upgrade, keyed like `<definition key>/<section>/<name>`"""

    result = {}

    for key, definition in definitions.items():
        prefix = "/".join(key)

        for action in definition.actions:
            if action.scripts is not None:
                result[f"{prefix}/actions/{action.name}"] = action.scripts

        for upgrade in definition.upgrades:
            if upgrade.action is not None and upgrade.action.scripts is not None:
                result[f"{prefix}/upgrade/{upgrade.name}"] = upgrade.action.scripts

    return result


# Expected specs


def build_expected_spec(*, terminatable: bool = False, with_bundle_switch: bool = False) -> JobSpecV1:
    """Spec `GROUPED_SCRIPTS` are expected to be parsed to"""

    # absent display names are expected to be filled with names on conversion
    def ansible(key: str, name: str, path: str, display_name: str | None = None) -> ScriptSpec:
        return ScriptSpec(
            key=FullSpecKey(key),
            names=Names(internal=name, display=display_name or name),
            script=AnsibleScript(type=ScriptType.ANSIBLE, path=path, params=AnsibleScriptParams()),
            details=JobDetails(terminatable=terminatable),
        )

    def group(key: str, name: str, display_name: str, type_: ExecutionStyle) -> GroupSpec:
        return GroupSpec(key=FullSpecKey(key), names=Names(internal=name, display=display_name), type=type_)

    entries: list[ScriptSpec | GroupSpec] = [
        ansible("/0", "pre_check", "ansible/pre_check.yaml", "Pre-check"),
        group("/shards", "shards", "Shards", ExecutionStyle.PARALLEL),
        group("/shards/shard_a", "shard_a", "Shard A", ExecutionStyle.SEQUENTIAL),
        ansible("/shards/shard_a/0", "stop_a", "ansible/stop.yaml"),
        ansible("/shards/shard_a/1", "reconfigure_a", "ansible/cfg.yaml"),
        ansible("/shards/shard_a/2", "start_a", "ansible/start.yaml"),
        group("/shards/shard_b", "shard_b", "Shard B", ExecutionStyle.SEQUENTIAL),
        ansible("/shards/shard_b/0", "stop_b", "ansible/stop.yaml"),
        ansible("/shards/shard_b/1", "reconfigure_b", "ansible/cfg.yaml"),
        ansible("/shards/shard_b/2", "start_b", "ansible/start.yaml"),
        ansible("/2", "finalize", "ansible/finalize.yaml", "Finalize"),
    ]

    if with_bundle_switch:
        entries.append(
            ScriptSpec(
                key=FullSpecKey("/3"),
                names=Names(internal="switch", display="switch"),
                script=SimpleInternalScript(type=ScriptType.INTERNAL, path="bundle_switch", params=None),
                # internal scripts are never terminatable
                details=JobDetails(terminatable=False),
            )
        )

    return JobSpecV1.from_entries(*entries)


# Tests


class TestEntryKindDiscrimination(TestCase):
    """
    `detect_entry_kind` is the sole gatekeeper between groups and scripts:
    script dataclasses don't forbid extra keys, so they can't reject a misrouted entry themselves.
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.adapter: TypeAdapter[Any] = TypeAdapter(ClusterEntry)

    def test_raw_entries_discriminated_success(self) -> None:
        cases: tuple[tuple[str, dict, Literal["group", "script"]], ...] = (
            ("group", build_group(name="shards", scripts=[load(SIMPLE_SCRIPT)]), "group"),
            ("script", load(SIMPLE_SCRIPT), "script"),
        )

        for case, entry, expected in cases:
            with self.subTest(case):
                self.assertEqual(detect_entry_kind(entry), expected)

    def test_parsed_entries_discriminated_success(self) -> None:
        cases: tuple[tuple[str, dict, Literal["group", "script"]], ...] = (
            ("group", build_group(name="shards", scripts=[load(SIMPLE_SCRIPT)]), "group"),
            ("script", load(SIMPLE_SCRIPT), "script"),
        )

        for case, entry, expected in cases:
            with self.subTest(case):
                self.assertEqual(detect_entry_kind(self.adapter.validate_python(entry)), expected)

    def test_entries_sharing_names_with_groups_discriminated_success(self) -> None:
        """`name` and `display_name` are siblings of `group` now, so neither can tell a group from a script"""

        cases: tuple[tuple[str, dict, Literal["group", "script"]], ...] = (
            (
                "group",
                build_group(name="shards", scripts=[load(SIMPLE_SCRIPT)]) | {"display_name": "Shards"},
                "group",
            ),
            (
                "script carrying the same names",
                load(SIMPLE_SCRIPT) | {"name": "shards", "display_name": "Shards"},
                "script",
            ),
            (
                "group named after a sibling script's position",
                build_group(name="0", scripts=[load(SIMPLE_SCRIPT)]),
                "group",
            ),
        )

        for case, entry, expected in cases:
            with self.subTest(case):
                self.assertEqual(detect_entry_kind(entry), expected)
                self.assertEqual(detect_entry_kind(self.adapter.validate_python(entry)), expected)


class TestScriptGroupsParsing(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.parser = v_2_1.Parser()

        cls.action_spec = build_expected_spec()
        cls.upgrade_spec = build_expected_spec(with_bundle_switch=True)

    def parse_action_scripts(self, scripts: list[dict]) -> JobSpecV1:
        return self.parser.parse_scripts(
            scripts, template_path=FILE_IN_ROOT, action_allow_to_terminate=False, mode="action"
        )

    def test_groups_in_root_entries_success(self) -> None:
        expected = {
            f"cluster/actions/{ACTION_NAME}": self.action_spec,
            f"cluster/upgrade/{UPGRADE_NAME}": self.upgrade_spec,
            f"service/service/actions/{ACTION_NAME}": self.action_spec,
            f"component/service/component/actions/{ACTION_NAME}": self.action_spec,
            f"provider/actions/{ACTION_NAME}": self.action_spec,
            f"provider/upgrade/{UPGRADE_NAME}": self.upgrade_spec,
            f"host/actions/{ACTION_NAME}": self.action_spec,
            f"adcm/actions/{ACTION_NAME}": self.action_spec,
        }

        specs = {}
        for bundle in build_bundles(contract_version="2.1").values():
            definitions = self.parser.parse_root_entries(to_root_entries(bundle), bundle_root=BUNDLE_ROOT)
            specs |= collect_scripts_specs(definitions)

        self.assertDictEqual(specs, expected)

    def test_groups_in_dynamic_scripts_success(self) -> None:
        cases: tuple[tuple[ScriptsMode, list[dict], JobSpecV1], ...] = (
            ("action", grouped_scripts(), self.action_spec),
            ("wizard", grouped_scripts(), self.action_spec),
            ("upgrade", grouped_upgrade_scripts(), self.upgrade_spec),
        )

        for mode, scripts, expected in cases:
            with self.subTest(mode):
                spec = self.parser.parse_scripts(
                    scripts, template_path=FILE_IN_ROOT, action_allow_to_terminate=False, mode=mode
                )

                self.assertEqual(spec, expected)

    def test_action_allow_to_terminate_propagates_into_groups_success(self) -> None:
        expected = build_expected_spec(terminatable=True)

        # rendered scripts
        spec = self.parser.parse_scripts(
            grouped_scripts(), template_path=FILE_IN_ROOT, action_allow_to_terminate=True, mode="action"
        )
        self.assertEqual(spec, expected)

        # statically declared scripts
        cluster = with_contract_version(build_object("cluster", "cluster"), "2.1")
        cluster = with_action(cluster, grouped_scripts(), allow_to_terminate=True)
        definitions = self.parser.parse_root_entries(to_root_entries([cluster]), bundle_root=BUNDLE_ROOT)
        self.assertEqual(collect_scripts_specs(definitions), {f"cluster/actions/{ACTION_NAME}": expected})

    def test_script_keys_keep_positions_among_groups_success(self) -> None:
        # a group takes its position among entries of its level too,
        # so keys of scripts declared around it skip that position
        scripts = [
            load(SIMPLE_SCRIPT),
            build_group(
                name="outer",
                scripts=[
                    load(SIMPLE_SCRIPT),
                    build_group(name="inner", scripts=[load(SIMPLE_SCRIPT)], type_="sequential"),
                    load(SIMPLE_SCRIPT),
                ],
            ),
            load(SIMPLE_SCRIPT),
        ]

        spec = self.parse_action_scripts(scripts)

        self.assertEqual(list(spec.scripts), ["/0", "/outer/0", "/outer/inner/0", "/outer/2", "/2"])
        self.assertEqual(spec.hierarchy.fields, ["0", "outer", "2"])
        self.assertEqual(spec.hierarchy.child_groups["outer"].fields, ["0", "inner", "2"])

    def test_group_display_name_defaults_to_its_name_success(self) -> None:
        spec = self.parse_action_scripts(
            [build_group(name="nameless", scripts=[load(SIMPLE_SCRIPT)], type_="sequential")]
        )

        self.assertEqual(spec.groups[FullSpecKey("/nameless")].names.display, "nameless")

    def test_nested_group_form_rejected_fail(self) -> None:
        # `group` holding the whole body is the replaced form: it gets a mapping where an execution style is required
        with self.assertRaises(BundleParsingError) as err:
            self.parse_action_scripts(load(NESTED_GROUP))

        message = err.exception.message
        self.assertIn("enum: Input should be 'sequential' or 'parallel'", message)
        # the body's fields are expected as siblings of `group`, so they read as missing
        self.assertIn("name\n    | missing", message)
        self.assertIn("scripts\n    | missing", message)

    def test_group_without_scripts_fail(self) -> None:
        with self.assertRaises(BundleParsingError) as err:
            self.parse_action_scripts([build_group(name="empty", scripts=[])])

        self.assertIn("too_short: List should have at least 1 item", err.exception.message)

    def test_group_name_used_more_than_once_fail(self) -> None:
        for case, scripts, conflict in (
            (
                "same level",
                [build_group(name="twin", scripts=[load(SIMPLE_SCRIPT)]) for _ in range(2)],
                '"/twin" is declared more than once',
            ),
            (
                "different levels",
                [
                    build_group(
                        name="twin",
                        scripts=[build_group(name="twin", scripts=[load(SIMPLE_SCRIPT)], type_="sequential")],
                    )
                ],
                'group name "twin" is used by more than one group: "/twin", "/twin/twin"',
            ),
        ):
            with self.subTest(case), self.assertRaises(BundleParsingError) as err:
                self.parse_action_scripts(scripts)

            self.assertIn("Jobs are defined incorrectly: Entries of execution plan conflict", err.exception.message)
            self.assertIn(conflict, err.exception.message)

    def test_group_named_after_script_position_fail(self) -> None:
        # the script takes key "0" by its position, the group takes the same one by its name
        scripts = [load(SIMPLE_SCRIPT), build_group(name="0", scripts=[load(SIMPLE_SCRIPT)])]

        with self.assertRaises(BundleParsingError) as err:
            self.parse_action_scripts(scripts)

        self.assertIn("Jobs are defined incorrectly", err.exception.message)
        self.assertIn('"/0" is declared more than once: as script, then as group', err.exception.message)


class TestScriptGroupsValidation(TestCase):
    """
    Restrictions of groups are checked on different stages (schema, spec checks),
    so declared scripts are parsed and then checked the way bundle upload / rendering does it.
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.parser = v_2_1.Parser()

    def parse_and_validate(self, place: Place, scripts: list[dict]) -> None:
        switch = load(UPGRADE_SWITCH_SCRIPT)
        cluster = with_contract_version(build_object("cluster", "cluster"), "2.1")

        match place:
            case "rendered upgrade":
                # rendered scripts are checked right after parsing
                self.parser.parse_scripts(
                    [*scripts, switch], template_path=FILE_IN_ROOT, action_allow_to_terminate=False, mode="upgrade"
                )
                return
            case "cluster action":
                cluster = with_action(cluster, scripts)
            case "static upgrade":
                cluster = with_upgrade(cluster, [*scripts, switch])

        definitions = self.parser.parse_root_entries(to_root_entries([cluster]), bundle_root=BUNDLE_ROOT)
        definition = definitions[("cluster",)]
        check_actions(
            actions=definition.actions, definitions=definitions, definition_type="cluster", bundle_root=BUNDLE_ROOT
        )
        check_upgrades(upgrades=definition.upgrades, definitions=definitions, bundle_root=BUNDLE_ROOT)

    def parse_root_entry(self, object_type: Literal["cluster", "provider", "adcm"], scripts: list[dict]) -> None:
        entry = with_action(with_contract_version(build_object(object_type, object_type), "2.1"), scripts)
        self.parser.parse_root_entries(to_root_entries([entry]), bundle_root=BUNDLE_ROOT)

    # NB: parallel groups below always contain at least 2 entries, since fewer isn't allowed for them

    def test_alternating_execution_styles_success(self) -> None:
        simple = load(SIMPLE_SCRIPT)
        cases: tuple[tuple[Place, str, list[dict]], ...] = (
            ("cluster action", "sequential", [build_group(name="outer", type_="sequential", scripts=[simple])]),
            (
                "static upgrade",
                "sequential -> parallel",
                [
                    build_group(
                        name="outer",
                        type_="sequential",
                        scripts=[build_group(name="inner", type_="parallel", scripts=[simple, simple])],
                    )
                ],
            ),
            (
                "rendered upgrade",
                "parallel -> sequential",
                [
                    build_group(
                        name="outer",
                        type_="parallel",
                        scripts=[build_group(name="inner", type_="sequential", scripts=[simple]), simple],
                    )
                ],
            ),
        )

        for place, styles, scripts in cases:
            with self.subTest(f"{place}: {styles}"):
                self.parse_and_validate(place, scripts)

    def test_incorrect_nesting_of_groups_fail(self) -> None:
        simple = load(SIMPLE_SCRIPT)
        cases: tuple[tuple[Place, str, list[dict], str], ...] = (
            (
                "cluster action",
                "sequential -> sequential",
                [
                    build_group(
                        name="outer",
                        type_="sequential",
                        scripts=[build_group(name="inner", type_="sequential", scripts=[simple])],
                    )
                ],
                ALTERNATION_ERROR,
            ),
            (
                "static upgrade",
                "parallel -> parallel",
                [
                    build_group(
                        name="outer",
                        type_="parallel",
                        scripts=[build_group(name="inner", type_="parallel", scripts=[simple, simple]), simple],
                    )
                ],
                ALTERNATION_ERROR,
            ),
            (
                "rendered upgrade",
                "sequential -> parallel -> sequential",
                [
                    build_group(
                        name="outer",
                        type_="sequential",
                        scripts=[
                            build_group(
                                name="middle",
                                type_="parallel",
                                scripts=[build_group(name="inner", type_="sequential", scripts=[simple]), simple],
                            )
                        ],
                    )
                ],
                DEPTH_ERROR,
            ),
        )

        for place, styles, scripts, error in cases:
            with self.subTest(f"{place}: {styles}"), self.assertRaises(BundleValidationError) as err:
                self.parse_and_validate(place, scripts)

            self.assertIn(error, err.exception.message)

    def test_bundle_changing_scripts_inside_groups_fail(self) -> None:
        simple = load(SIMPLE_SCRIPT)
        switch = {"name": "forbidden", "script_type": "internal", "script": "bundle_switch"}
        revert = {"name": "forbidden", "script_type": "internal", "script": "bundle_revert"}

        # upgrades don't allow `bundle_revert` at all, so it's checked for action only
        cases: tuple[tuple[Place, str, list[dict]], ...] = (
            (
                "cluster action",
                "bundle_switch",
                [build_group(name="outer", type_="parallel", scripts=[switch, simple])],
            ),
            (
                "cluster action",
                "bundle_revert",
                [
                    build_group(
                        name="outer",
                        type_="parallel",
                        scripts=[build_group(name="inner", type_="sequential", scripts=[revert]), simple],
                    )
                ],
            ),
            (
                "static upgrade",
                "bundle_switch",
                [
                    build_group(
                        name="outer",
                        type_="sequential",
                        scripts=[build_group(name="inner", type_="parallel", scripts=[switch, simple])],
                    )
                ],
            ),
            (
                "rendered upgrade",
                "bundle_switch",
                [
                    build_group(
                        name="outer",
                        type_="parallel",
                        scripts=[build_group(name="inner", type_="sequential", scripts=[switch]), simple],
                    )
                ],
            ),
        )

        for place, script, scripts in cases:
            with self.subTest(f"{place}: {script}"), self.assertRaises(BundleValidationError) as err:
                self.parse_and_validate(place, scripts)

            self.assertIn(f'"{script}" {BUNDLE_CHANGING_SCRIPT_IN_GROUP_ERROR}', err.exception.message)

    def test_parallel_group_with_one_entry_fail(self) -> None:
        # groups can't be empty in DSL, so it's parallel group only that may have too few entries
        places: tuple[Place, ...] = ("cluster action", "rendered upgrade")
        scripts = [build_group(name="lonely", scripts=[load(SIMPLE_SCRIPT)], type_="parallel")]

        for place in places:
            with self.subTest(place), self.assertRaises(BundleValidationError) as err:
                self.parse_and_validate(place, scripts)

            self.assertIn(f'"/lonely" {TOO_FEW_ENTRIES_ERROR} 2 entries', err.exception.message)

    def test_scripts_allowed_inside_groups_depend_on_object_type(self) -> None:
        # services and hosts share sets of scripts with clusters and providers correspondingly
        hc_apply = {"name": "apply", "script_type": "internal", "script": "hc_apply"}
        clean = {"name": "clean", "script_type": "internal", "script": "before_upgrade_clean"}

        for object_type, script in (("cluster", hc_apply), ("provider", clean), ("adcm", load(SIMPLE_SCRIPT))):
            with self.subTest(f"{object_type} accepts {script['script']}"):
                self.parse_root_entry(object_type, [build_group(name="group", scripts=[script])])

        for object_type, script, error in (
            ("provider", hc_apply, "Input tag 'hc_apply' found using 'script' does not match any of the expected tags"),
            ("adcm", clean, "does not match any of the expected tags: 'ansible', 'python'"),
        ):
            with self.subTest(f"{object_type} rejects {script['script']}"), self.assertRaises(
                BundleParsingError
            ) as err:
                self.parse_root_entry(object_type, [build_group(name="group", scripts=[script])])

            self.assertIn(error, err.exception.message)
