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

from core.action.operations import flatten_execution_plan, to_rich_job, to_rich_jobs
from core.action.types import (
    AnsibleScript,
    AnsibleScriptParams,
    ExecutionStatus,
    ExecutionStyle,
    JobHierarchyLevel,
    JobShortInfo,
    JobSpecV1,
    ScriptSpec,
    ScriptType,
    WorkerInfo,
)
from core.spec.types import FullSpecKey
from core.types import Names

SEQUENTIAL = ExecutionStyle.SEQUENTIAL
PARALLEL = ExecutionStyle.PARALLEL


def make_script(key: str) -> ScriptSpec:
    return ScriptSpec(
        key=FullSpecKey(key),
        names=Names(internal=key),
        script=AnsibleScript(type=ScriptType.ANSIBLE, path="a.yaml", params=AnsibleScriptParams()),
    )


def make_level(rule: ExecutionStyle, fields: list[str], **children: JobHierarchyLevel) -> JobHierarchyLevel:
    return JobHierarchyLevel(rule=rule, fields=fields, child_groups=dict(children))


class TestFlattenExecutionPlan(TestCase):
    """
    Keys in here are deliberately not in any sortable order:
    what comes out is what the hierarchy declares, nothing else.
    """

    def test_empty_plan(self):
        self.assertEqual(flatten_execution_plan(JobSpecV1()), ())

    def test_order_follows_declaration_not_key_order(self):
        spec = JobSpecV1(
            hierarchy=make_level(SEQUENTIAL, ["zeta", "alpha", "mid"]),
            scripts={key: make_script(key) for key in ("/zeta", "/alpha", "/mid")},
        )

        self.assertEqual(flatten_execution_plan(spec), ("/zeta", "/alpha", "/mid"))

    def test_group_is_walked_where_it_is_declared(self):
        # the group sits between two scripts, so its own scripts come out between them
        spec = JobSpecV1(
            hierarchy=make_level(
                SEQUENTIAL,
                ["last", "group", "first"],
                group=make_level(PARALLEL, ["b", "a"]),
            ),
            scripts={key: make_script(key) for key in ("/last", "/group/b", "/group/a", "/first")},
        )

        self.assertEqual(flatten_execution_plan(spec), ("/last", "/group/b", "/group/a", "/first"))

    def test_deeply_nested_groups(self):
        spec = JobSpecV1(
            hierarchy=make_level(
                SEQUENTIAL,
                ["outer"],
                outer=make_level(PARALLEL, ["inner"], inner=make_level(SEQUENTIAL, ["z", "y"])),
            ),
            scripts={key: make_script(key) for key in ("/outer/inner/z", "/outer/inner/y")},
        )

        self.assertEqual(flatten_execution_plan(spec), ("/outer/inner/z", "/outer/inner/y"))


def make_job(job_id: int, spec_key: str) -> JobShortInfo:
    return JobShortInfo(
        id=job_id,
        task_id=1,
        spec_key=FullSpecKey(spec_key),
        finish_date=None,
        worker=WorkerInfo(),
        status=ExecutionStatus.CREATED,
    )


class TestToRichJobs(TestCase):
    def setUp(self) -> None:
        self.spec = JobSpecV1.from_entries(make_script("/beta"), make_script("/alpha"))

    def test_job_is_paired_with_its_node(self):
        rich = to_rich_job(spec=self.spec, job=make_job(7, "/alpha"))

        self.assertEqual(rich.runtime.id, 7)
        self.assertEqual(rich.spec, self.spec.scripts["/alpha"])

    def test_jobs_are_keyed_the_way_the_plan_keys_them(self):
        rich = to_rich_jobs(spec=self.spec, jobs=[make_job(7, "/alpha"), make_job(8, "/beta")])

        self.assertEqual(sorted(rich), ["/alpha", "/beta"])
        self.assertEqual(rich["/alpha"].runtime.id, 7)
        self.assertEqual(rich["/beta"].runtime.id, 8)

    def test_no_jobs_at_all(self):
        self.assertEqual(to_rich_jobs(spec=self.spec, jobs=[]), {})

    def test_job_of_a_node_the_plan_lacks_fail(self):
        with self.assertRaises(KeyError) as err:
            to_rich_jobs(spec=self.spec, jobs=[make_job(7, "/alpha"), make_job(9, "/gone")])

        self.assertIn("/gone", str(err.exception))

    def test_nodes_without_jobs_are_not_invented(self):
        # matching says nothing about a plan node no job was created for
        rich = to_rich_jobs(spec=self.spec, jobs=[make_job(7, "/alpha")])

        self.assertEqual(list(rich), ["/alpha"])
