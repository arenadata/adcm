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

from datetime import datetime, timedelta, timezone
from unittest import TestCase

from core.action.types import (
    AnsibleScript,
    AnsibleScriptParams,
    ExecutionStatus,
    ExecutionStyle,
    GroupSpec,
    JobDetails,
    JobShortInfo,
    JobSpecV1,
    RuntimeDates,
    ScriptSpec,
    ScriptType,
    WorkerInfo,
)
from core.spec.types import FullSpecKey
from core.types import Names

from api_v2.internal.serializers import GroupNode, JobNode, Node, TaskExecutionPlan, represent_execution_plan

SEQUENTIAL = ExecutionStyle.SEQUENTIAL
PARALLEL = ExecutionStyle.PARALLEL

ABORTED = ExecutionStatus.ABORTED
CREATED = ExecutionStatus.CREATED
FAILED = ExecutionStatus.FAILED
RUNNING = ExecutionStatus.RUNNING
SUCCESS = ExecutionStatus.SUCCESS

BASE = datetime(2026, 8, 12, 10, 31, tzinfo=timezone.utc)
NO_DATES = RuntimeDates()


def at(seconds: int) -> datetime:
    return BASE + timedelta(seconds=seconds)


def ran(start: int, finish: int | None = None) -> RuntimeDates:
    return RuntimeDates(start=at(start), finish=None if finish is None else at(finish))


def make_script(key: str, display: str = "", terminatable: bool = True) -> ScriptSpec:
    # scripts are keyed as "<position>-<name>" within their level, the same way parsing does it
    *_, level = key.split("/")
    _, name = level.split("-", maxsplit=1)

    return ScriptSpec(
        key=FullSpecKey(key),
        names=Names(internal=name, display=display),
        script=AnsibleScript(type=ScriptType.ANSIBLE, path="a.yaml", params=AnsibleScriptParams()),
        details=JobDetails(terminatable=terminatable),
    )


def make_group(key: str, type_: ExecutionStyle, display: str = "") -> GroupSpec:
    *_, name = key.split("/")

    return GroupSpec(key=FullSpecKey(key), names=Names(internal=name, display=display), type=type_)


def make_job(
    job_id: int, spec_key: str, status: ExecutionStatus = CREATED, dates: RuntimeDates = NO_DATES
) -> JobShortInfo:
    return JobShortInfo(
        id=job_id,
        task_id=1,
        spec_key=FullSpecKey(spec_key),
        dates=dates,
        worker=WorkerInfo(),
        status=status,
    )


def as_group(node: Node) -> GroupNode:
    if not isinstance(node, GroupNode):
        message = f"Group node is expected, got {node}"
        raise TypeError(message)

    return node


def as_job(node: Node) -> JobNode:
    if not isinstance(node, JobNode):
        message = f"Job node is expected, got {node}"
        raise TypeError(message)

    return node


def make_example_plan() -> JobSpecV1:
    """`job, parallel(seq(a, b, c), seq(d, e, f)), job`: a job, two parallel shards of three jobs each, a job"""

    return JobSpecV1.from_entries(
        make_script("/0-pre_check", display="Pre-check"),
        make_group("/shards", PARALLEL, display="Shards"),
        make_group("/shards/shard_a", SEQUENTIAL, display="Shard A"),
        make_script("/shards/shard_a/0-stop_a", display="Stop A"),
        make_script("/shards/shard_a/1-reconfigure_a", display="Reconfigure A"),
        make_script("/shards/shard_a/2-start_a", display="Start A"),
        make_group("/shards/shard_b", SEQUENTIAL, display="Shard B"),
        make_script("/shards/shard_b/0-stop_b", display="Stop B"),
        make_script("/shards/shard_b/1-reconfigure_b", display="Reconfigure B"),
        make_script("/shards/shard_b/2-start_b", display="Start B"),
        make_script("/2-finalize", display="Finalize"),
    )


def make_example_jobs() -> list[JobShortInfo]:
    """Pre-check and the first shard succeeded, the second shard is halfway through, finalize hasn't started"""

    return [
        make_job(101, "/0-pre_check", SUCCESS, ran(0, 12)),
        make_job(102, "/shards/shard_a/0-stop_a", SUCCESS, ran(12, 30)),
        make_job(103, "/shards/shard_a/1-reconfigure_a", SUCCESS, ran(30, 60)),
        make_job(104, "/shards/shard_a/2-start_a", SUCCESS, ran(60, 77)),
        make_job(105, "/shards/shard_b/0-stop_b", SUCCESS, ran(14, 40)),
        make_job(106, "/shards/shard_b/1-reconfigure_b", RUNNING, ran(40)),
        make_job(107, "/shards/shard_b/2-start_b"),
        make_job(108, "/2-finalize"),
    ]


class TestRepresentExecutionPlan(TestCase):
    def test_flat_plan_is_job_nodes_in_declaration_order(self) -> None:
        spec = JobSpecV1.from_entries(
            make_script("/0-zeta", display="Zeta"),
            make_script("/1-alpha", display="Alpha", terminatable=False),
            make_script("/2-mid"),
        )
        jobs = [
            make_job(1, "/0-zeta", SUCCESS, ran(0, 10)),
            make_job(2, "/1-alpha", RUNNING, ran(10)),
            make_job(3, "/2-mid"),
        ]

        plan = represent_execution_plan(spec=spec, jobs=jobs, version=1)

        self.assertEqual(
            plan,
            TaskExecutionPlan(
                version=1,
                children=(
                    JobNode(
                        id=1,
                        name="zeta",
                        display_name="Zeta",
                        status=SUCCESS,
                        start_time=at(0),
                        end_time=at(10),
                        duration=10,
                        is_terminatable=True,
                    ),
                    JobNode(
                        id=2,
                        name="alpha",
                        display_name="Alpha",
                        status=RUNNING,
                        start_time=at(10),
                        end_time=None,
                        duration=None,
                        is_terminatable=False,
                    ),
                    JobNode(
                        id=3,
                        name="mid",
                        display_name="mid",
                        status=CREATED,
                        start_time=None,
                        end_time=None,
                        duration=None,
                        is_terminatable=True,
                    ),
                ),
            ),
        )

    def test_nested_plan_shape(self) -> None:
        plan = represent_execution_plan(spec=make_example_plan(), jobs=make_example_jobs(), version=1)

        pre_check, shards, finalize = plan.children
        self.assertEqual(as_job(pre_check).name, "pre_check")
        self.assertEqual(as_job(finalize).name, "finalize")

        shards = as_group(shards)
        self.assertEqual((shards.kind, shards.name, shards.display_name), (PARALLEL, "shards", "Shards"))

        shard_a, shard_b = map(as_group, shards.children)
        self.assertEqual((shard_a.kind, shard_a.name, shard_a.display_name), (SEQUENTIAL, "shard_a", "Shard A"))
        self.assertEqual((shard_b.kind, shard_b.name, shard_b.display_name), (SEQUENTIAL, "shard_b", "Shard B"))

        self.assertEqual(
            [(job.id, job.name, job.display_name) for job in map(as_job, shard_a.children)],
            [(102, "stop_a", "Stop A"), (103, "reconfigure_a", "Reconfigure A"), (104, "start_a", "Start A")],
        )
        self.assertEqual(
            [(job.id, job.name, job.display_name) for job in map(as_job, shard_b.children)],
            [(105, "stop_b", "Stop B"), (106, "reconfigure_b", "Reconfigure B"), (107, "start_b", "Start B")],
        )

    def test_example_state(self) -> None:
        plan = represent_execution_plan(spec=make_example_plan(), jobs=make_example_jobs(), version=1)

        pre_check, shards, finalize = plan.children
        shards = as_group(shards)
        shard_a, shard_b = map(as_group, shards.children)

        self.assertEqual(plan.version, 1)
        self.assertEqual(as_job(pre_check).status, SUCCESS)
        self.assertEqual(as_job(pre_check).duration, 12)

        self.assertEqual(shards.status, RUNNING)
        self.assertEqual(shards.start_time, at(12))
        self.assertIsNone(shards.end_time)
        self.assertIsNone(shards.duration)

        self.assertEqual(shard_a.status, SUCCESS)
        self.assertEqual((shard_a.start_time, shard_a.end_time), (at(12), at(77)))
        self.assertEqual(shard_a.duration, 65)

        self.assertEqual(shard_b.status, RUNNING)
        self.assertEqual(shard_b.start_time, at(14))
        self.assertIsNone(shard_b.end_time)

        finalize = as_job(finalize)
        self.assertEqual(finalize.status, CREATED)
        self.assertEqual((finalize.start_time, finalize.end_time, finalize.duration), (None, None, None))

    def test_inner_group_status_propagates_to_parents(self) -> None:
        spec = JobSpecV1.from_entries(
            make_group("/outer", SEQUENTIAL),
            make_script("/outer/0-first"),
            make_group("/outer/middle", PARALLEL),
            make_script("/outer/middle/0-side"),
            make_group("/outer/middle/inner", SEQUENTIAL),
            make_script("/outer/middle/inner/0-breaks"),
        )
        jobs = [
            make_job(1, "/outer/0-first", SUCCESS, ran(0, 5)),
            make_job(2, "/outer/middle/0-side", SUCCESS, ran(5, 8)),
            make_job(3, "/outer/middle/inner/0-breaks", FAILED, ran(5, 20)),
        ]

        plan = represent_execution_plan(spec=spec, jobs=jobs, version=1)

        (outer,) = map(as_group, plan.children)
        _, middle = outer.children
        middle = as_group(middle)
        _, inner = middle.children
        inner = as_group(inner)

        self.assertEqual((inner.status, middle.status, outer.status), (FAILED, FAILED, FAILED))
        self.assertEqual((inner.start_time, inner.end_time), (at(5), at(20)))
        self.assertEqual((middle.start_time, middle.end_time), (at(5), at(20)))
        self.assertEqual((outer.start_time, outer.end_time, outer.duration), (at(0), at(20), 20))

    def test_partly_run_nested_group_is_running_up_the_tree(self) -> None:
        spec = JobSpecV1.from_entries(
            make_group("/outer", SEQUENTIAL),
            make_group("/outer/inner", SEQUENTIAL),
            make_script("/outer/inner/0-done"),
            make_script("/outer/inner/1-never"),
        )
        jobs = [make_job(1, "/outer/inner/0-done", SUCCESS, ran(0, 10)), make_job(2, "/outer/inner/1-never")]

        plan = represent_execution_plan(spec=spec, jobs=jobs, version=1)

        (outer,) = map(as_group, plan.children)
        (inner,) = map(as_group, outer.children)

        self.assertEqual(inner.status, RUNNING)
        self.assertEqual((inner.start_time, inner.end_time, inner.duration), (at(0), None, None))
        self.assertEqual(outer.status, RUNNING)
        self.assertEqual((outer.start_time, outer.end_time, outer.duration), (at(0), None, None))

    def test_group_is_terminatable_even_if_its_jobs_are_not(self) -> None:
        spec = JobSpecV1.from_entries(
            make_group("/group", SEQUENTIAL),
            make_script("/group/0-one", terminatable=False),
            make_script("/group/1-two", terminatable=False),
        )
        jobs = [make_job(1, "/group/0-one"), make_job(2, "/group/1-two")]

        plan = represent_execution_plan(spec=spec, jobs=jobs, version=1)

        (group,) = map(as_group, plan.children)
        self.assertTrue(group.is_terminatable)
        self.assertEqual([as_job(job).is_terminatable for job in group.children], [False, False])

    def test_partly_run_group_is_running(self) -> None:
        spec = JobSpecV1.from_entries(
            make_group("/group", SEQUENTIAL),
            make_script("/group/0-done"),
            make_script("/group/1-never"),
        )
        jobs = [make_job(1, "/group/0-done", SUCCESS, ran(0, 10)), make_job(2, "/group/1-never")]

        plan = represent_execution_plan(spec=spec, jobs=jobs, version=1)

        group = as_group(plan.children[0])
        self.assertEqual(group.status, RUNNING)
        self.assertEqual((group.start_time, group.end_time), (at(0), None))

    def test_settled_mix_group_status_depends_on_its_kind_and_last_child(self) -> None:
        spec = JobSpecV1.from_entries(
            make_group("/par", PARALLEL),
            make_script("/par/0-one"),
            make_script("/par/1-two"),
            make_group("/seq", SEQUENTIAL),
            make_script("/seq/0-one"),
            make_script("/seq/1-two"),
        )
        jobs = [
            make_job(1, "/par/0-one", SUCCESS, ran(0, 10)),
            make_job(2, "/par/1-two", ABORTED, ran(0, 10)),
            make_job(3, "/seq/0-one", ABORTED, ran(10, 20)),
            make_job(4, "/seq/1-two", SUCCESS, ran(20, 30)),
        ]

        plan = represent_execution_plan(spec=spec, jobs=jobs, version=1)

        parallel, sequential = map(as_group, plan.children)
        self.assertEqual(parallel.status, ABORTED)
        self.assertEqual(sequential.status, SUCCESS)

    def test_job_of_a_node_the_plan_lacks_fails(self) -> None:
        spec = JobSpecV1.from_entries(make_script("/0-one"))
        jobs = [make_job(1, "/0-one"), make_job(2, "/gone")]

        with self.assertRaises(KeyError) as err:
            represent_execution_plan(spec=spec, jobs=jobs, version=1)

        self.assertIn("/gone", str(err.exception))

    def test_script_without_a_job_fails(self) -> None:
        spec = JobSpecV1.from_entries(
            make_script("/0-one"), make_group("/group", PARALLEL), make_script("/group/0-lonely")
        )
        jobs = [make_job(1, "/0-one")]

        with self.assertRaises(KeyError) as err:
            represent_execution_plan(spec=spec, jobs=jobs, version=1)

        self.assertIn("/group/0-lonely", str(err.exception))

    def test_order_follows_declaration_not_job_ids(self) -> None:
        spec = JobSpecV1.from_entries(
            make_script("/0-first"),
            make_group("/group", PARALLEL),
            make_script("/group/0-a"),
            make_script("/group/1-b"),
            make_script("/2-last"),
        )
        jobs = [make_job(4, "/0-first"), make_job(3, "/group/0-a"), make_job(2, "/group/1-b"), make_job(1, "/2-last")]

        plan = represent_execution_plan(spec=spec, jobs=reversed(jobs), version=1)

        first, group, last = plan.children
        self.assertEqual(as_job(first).id, 4)
        self.assertEqual([as_job(job).id for job in as_group(group).children], [3, 2])
        self.assertEqual(as_job(last).id, 1)
