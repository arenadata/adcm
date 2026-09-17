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

from unittest import TestCase

from core.action.types import (
    AnsibleScript,
    AnsibleScriptParams,
    ExecutionStyle,
    GroupSpec,
    JobHierarchyLevel,
    JobSpecV1,
    ScriptSpec,
    ScriptType,
)
from core.spec.errors import DuplicateSpecEntryError
from core.spec.keys import level_key_from_full_key
from core.spec.types import FullSpecKey, LevelSpecKey
from core.types import Names

SEQUENTIAL = ExecutionStyle.SEQUENTIAL
PARALLEL = ExecutionStyle.PARALLEL


def make_script(key: str) -> ScriptSpec:
    name = level_key_from_full_key(FullSpecKey(key))

    return ScriptSpec(
        key=FullSpecKey(key),
        names=Names(internal=name, display=name),
        script=AnsibleScript(type=ScriptType.ANSIBLE, path="a.yaml", params=AnsibleScriptParams()),
    )


def make_group(key: str, type_: ExecutionStyle, name: str | None = None) -> GroupSpec:
    name = name or level_key_from_full_key(FullSpecKey(key))

    return GroupSpec(key=FullSpecKey(key), names=Names(internal=name, display=name), type=type_)


def make_level(rule: ExecutionStyle, fields: list[str], **children: JobHierarchyLevel) -> JobHierarchyLevel:
    return JobHierarchyLevel(
        rule=rule,
        fields=[LevelSpecKey(field) for field in fields],
        child_groups={LevelSpecKey(key): child for key, child in children.items()},
    )


class TestJobSpecFromEntries(TestCase):
    def test_no_entries_build_empty_spec(self) -> None:
        self.assertEqual(JobSpecV1.from_entries(), JobSpecV1())

    def test_all_fields_are_set_explicitly(self) -> None:
        spec = JobSpecV1.from_entries(make_script("/0"))

        self.assertEqual(spec.model_fields_set, {"hierarchy", "groups", "scripts"})

    def test_root_scripts_follow_declaration_order(self) -> None:
        # keys are deliberately not in sortable order: only declaration defines it
        scripts = (make_script("/zeta"), make_script("/alpha"), make_script("/mid"))

        spec = JobSpecV1.from_entries(*scripts)

        self.assertEqual(spec.hierarchy, make_level(SEQUENTIAL, ["zeta", "alpha", "mid"]))
        self.assertEqual(spec.scripts, {script.key: script for script in scripts})
        self.assertEqual(spec.groups, {})

    def test_group_takes_its_place_among_scripts(self) -> None:
        group = make_group("/g", PARALLEL)
        entries = (make_script("/0"), group, make_script("/g/0"), make_script("/g/1"), make_script("/1"))

        spec = JobSpecV1.from_entries(*entries)

        self.assertEqual(
            spec.hierarchy,
            make_level(SEQUENTIAL, ["0", "g", "1"], g=make_level(PARALLEL, ["0", "1"])),
        )
        self.assertEqual(spec.groups, {group.key: group})
        self.assertEqual(list(spec.scripts), ["/0", "/g/0", "/g/1", "/1"])

    def test_nested_groups_keep_own_types(self) -> None:
        entries = (
            make_group("/outer", PARALLEL),
            make_group("/outer/inner", SEQUENTIAL),
            make_script("/outer/inner/0"),
            make_script("/outer/inner/1"),
            make_group("/outer/other", SEQUENTIAL),
            make_script("/outer/other/0"),
        )

        spec = JobSpecV1.from_entries(*entries)

        self.assertEqual(
            spec.hierarchy,
            make_level(
                SEQUENTIAL,
                ["outer"],
                outer=make_level(
                    PARALLEL,
                    ["inner", "other"],
                    inner=make_level(SEQUENTIAL, ["0", "1"]),
                    other=make_level(SEQUENTIAL, ["0"]),
                ),
            ),
        )
        self.assertEqual(list(spec.groups), ["/outer", "/outer/inner", "/outer/other"])

    def test_sibling_groups_may_have_same_script_positions(self) -> None:
        # scripts are keyed by position, so it's the group that makes them distinct
        entries = (
            make_group("/a", SEQUENTIAL),
            make_script("/a/0"),
            make_group("/b", SEQUENTIAL),
            make_script("/b/0"),
        )

        spec = JobSpecV1.from_entries(*entries)

        self.assertEqual(list(spec.scripts), ["/a/0", "/b/0"])
        self.assertEqual(
            spec.hierarchy,
            make_level(SEQUENTIAL, ["a", "b"], a=make_level(SEQUENTIAL, ["0"]), b=make_level(SEQUENTIAL, ["0"])),
        )

    def test_group_without_entries_is_still_present(self) -> None:
        group = make_group("/empty", PARALLEL)

        spec = JobSpecV1.from_entries(make_script("/0"), group)

        self.assertEqual(spec.hierarchy, make_level(SEQUENTIAL, ["0", "empty"], empty=make_level(PARALLEL, [])))
        self.assertEqual(spec.groups, {group.key: group})

    def test_same_script_name_in_different_places_success(self) -> None:
        # only group names are required to be unique, scripts are told apart by their keys
        entries = (make_group("/g", PARALLEL), make_script("/g/0"), make_script("/0"))

        spec = JobSpecV1.from_entries(*entries)

        self.assertEqual(list(spec.scripts), ["/g/0", "/0"])

    def test_duplicate_key_fail(self) -> None:
        for case, entries, expected in (
            (
                "script",
                (make_script("/0"), make_script("/1"), make_script("/0")),
                '"/0" is declared more than once: as script, then as script',
            ),
            (
                "group",
                (make_group("/g", PARALLEL), make_script("/g/0"), make_group("/g", SEQUENTIAL)),
                '"/g" is declared more than once: as group, then as group',
            ),
            (
                "script then group",
                (make_script("/0"), make_group("/0", PARALLEL)),
                '"/0" is declared more than once: as script, then as group',
            ),
            (
                "group then script",
                (make_group("/0", PARALLEL), make_script("/0")),
                '"/0" is declared more than once: as group, then as script',
            ),
        ):
            with self.subTest(case), self.assertRaises(DuplicateSpecEntryError) as err:
                JobSpecV1.from_entries(*entries)

            self.assertIn(expected, str(err.exception))

    def test_group_after_its_entries_fail(self) -> None:
        # the entry has already placed the group into hierarchy, so the group can't take its place
        with self.assertRaises(DuplicateSpecEntryError) as err:
            JobSpecV1.from_entries(make_script("/g/0"), make_group("/g", PARALLEL))

        self.assertIn('"/g" is already placed by entries declared before it', str(err.exception))

    def test_group_name_used_by_several_groups_fail(self) -> None:
        for case, entries, expected in (
            (
                "different levels",
                (make_group("/a", SEQUENTIAL), make_group("/a/a", PARALLEL), make_script("/a/a/0")),
                'group name "a" is used by more than one group: "/a", "/a/a"',
            ),
            (
                "different parents",
                (
                    make_group("/a", SEQUENTIAL, name="first"),
                    make_group("/a/x", PARALLEL),
                    make_group("/b", SEQUENTIAL, name="second"),
                    make_group("/b/x", PARALLEL),
                ),
                'group name "x" is used by more than one group: "/a/x", "/b/x"',
            ),
            (
                "names not matching keys",
                (make_group("/a", SEQUENTIAL, name="same"), make_group("/b", SEQUENTIAL, name="same")),
                'group name "same" is used by more than one group: "/a", "/b"',
            ),
        ):
            with self.subTest(case), self.assertRaises(DuplicateSpecEntryError) as err:
                JobSpecV1.from_entries(*entries)

            self.assertIn(expected, str(err.exception))

    def test_all_conflicts_are_reported_at_once_fail(self) -> None:
        entries = (
            make_script("/0"),
            make_script("/0"),
            make_script("/late/0"),
            make_group("/late", PARALLEL),
            make_group("/a", SEQUENTIAL, name="twin"),
            make_group("/b", SEQUENTIAL, name="twin"),
        )

        with self.assertRaises(DuplicateSpecEntryError) as err:
            JobSpecV1.from_entries(*entries)

        self.assertEqual(
            str(err.exception),
            "Entries of execution plan conflict with each other:\n"
            '- "/0" is declared more than once: as script, then as script\n'
            '- "/late" is already placed by entries declared before it\n'
            '- group name "twin" is used by more than one group: "/a", "/b"',
        )
