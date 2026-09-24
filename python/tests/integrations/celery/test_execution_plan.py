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

from typing import Any
from unittest import TestCase

from core.action import ExecutionStatus
from core.action.types import (
    AnsibleScript,
    AnsibleScriptParams,
    ExecutionStyle,
    GroupSpec,
    JobShortInfo,
    JobSpecV1,
    RichJob,
    ScriptSpec,
    ScriptType,
    WorkerInfo,
)
from core.spec.keys import level_key_from_full_key
from core.spec.types import FullSpecKey
from core.types import Names
from integrations.celery.tasks import (
    COMPLETE_TASK_TASK_NAME,
    GROUP_FINISHED_TASK_NAME,
    RUN_JOB_TASK_NAME,
    SET_TASK_TO_BROKEN_TASK_NAME,
    prepare_execution_plan,
)

from celery import chord, group
from celery.canvas import Signature

TASK_ID = 4

SEQUENTIAL = ExecutionStyle.SEQUENTIAL
PARALLEL = ExecutionStyle.PARALLEL

# markers of task finalization attached to a canvas node
ON_ERROR = "finalize-on-error"
ON_SUCCESS = "finalize-on-success"


def make_script(key: str) -> ScriptSpec:
    name = level_key_from_full_key(FullSpecKey(key))

    return ScriptSpec(
        key=FullSpecKey(key),
        names=Names(internal=name, display=name),
        script=AnsibleScript(type=ScriptType.ANSIBLE, path="a.yaml", params=AnsibleScriptParams()),
    )


def make_group(key: str, type_: ExecutionStyle) -> GroupSpec:
    name = level_key_from_full_key(FullSpecKey(key))

    return GroupSpec(key=FullSpecKey(key), names=Names(internal=name, display=name), type=type_)


def make_jobs(plan: JobSpecV1) -> dict[FullSpecKey, RichJob]:
    # ids are deliberately not the same as positions of scripts
    return {
        key: RichJob(
            spec=script,
            runtime=JobShortInfo(
                id=100 + i,
                task_id=TASK_ID,
                spec_key=key,
                finish_date=None,
                worker=WorkerInfo(),
                status=ExecutionStatus.CREATED,
            ),
        )
        for i, (key, script) in enumerate(plan.scripts.items())
    }


def finalization_markers(sig: Signature) -> tuple[str, ...]:
    def is_finalizer(callback: Any) -> bool:
        return callback["task"] == COMPLETE_TASK_TASK_NAME

    markers = []
    if any(map(is_finalizer, sig.options.get("link_error", []))):
        markers.append(ON_ERROR)
    if any(map(is_finalizer, sig.options.get("link", []))):
        markers.append(ON_SUCCESS)

    return tuple(markers)


def describe_canvas(sig: Signature) -> tuple:
    """
    Represent canvas as nested tuples, so its structure and attached finalization can be compared as a whole:
    - job: ("job", <job id>, <markers>);
    - chord's callback: ("group-finished", <group key>, <markers>);
    - chain: ("chain", <markers>, [<steps>]);
    - chord: ("chord", <markers>, [<header entries>], <body>).
    """

    markers = finalization_markers(sig)

    if isinstance(sig, chord):
        header = sig.tasks.tasks if isinstance(sig.tasks, group) else sig.tasks
        return "chord", markers, [describe_canvas(entry) for entry in header], describe_canvas(sig.body)

    # chains built with `|` are instances of private `_chain`, not of public `chain`
    if sig.subtask_type == "chain":
        return "chain", markers, [describe_canvas(step) for step in sig.tasks]

    if sig.task == RUN_JOB_TASK_NAME:
        return "job", sig.kwargs["job_id"], markers

    if sig.task == GROUP_FINISHED_TASK_NAME:
        return "group-finished", sig.kwargs["group_key"], markers

    raise AssertionError(f"Unexpected signature in canvas: {sig!r}")


class TestPrepareExecutionPlan(TestCase):
    def test_finalizer_is_marked_broken_on_error(self) -> None:
        plan = JobSpecV1.from_entries(make_script("/0"))

        result = prepare_execution_plan(task_id=TASK_ID, plan=plan, jobs=make_jobs(plan))

        (finalizer,) = result.tasks[0].options["link"]
        self.assertEqual(finalizer["kwargs"], {"task_id": TASK_ID})
        self.assertTrue(finalizer["immutable"])
        self.assertEqual(
            [(errback["task"], errback["kwargs"]) for errback in finalizer["options"]["link_error"]],
            [(SET_TASK_TO_BROKEN_TASK_NAME, {"task_id": TASK_ID})],
        )

    def test_root_scripts(self) -> None:
        plan = JobSpecV1.from_entries(make_script("/0"), make_script("/1"))

        result = prepare_execution_plan(task_id=TASK_ID, plan=plan, jobs=make_jobs(plan))

        self.assertEqual(
            describe_canvas(result),
            ("chain", (), [("job", 100, (ON_ERROR,)), ("job", 101, (ON_ERROR, ON_SUCCESS))]),
        )

    def test_sequential_group_is_merged_into_root(self) -> None:
        plan = JobSpecV1.from_entries(
            make_script("/0"), make_group("/s", SEQUENTIAL), make_script("/s/0"), make_script("/s/1")
        )

        result = prepare_execution_plan(task_id=TASK_ID, plan=plan, jobs=make_jobs(plan))

        self.assertEqual(
            describe_canvas(result),
            (
                "chain",
                (),
                [("job", 100, (ON_ERROR,)), ("job", 101, (ON_ERROR,)), ("job", 102, (ON_ERROR, ON_SUCCESS))],
            ),
        )

    def test_single_sequential_group_is_merged_into_root(self) -> None:
        plan = JobSpecV1.from_entries(make_group("/s", SEQUENTIAL), make_script("/s/0"), make_script("/s/1"))

        result = prepare_execution_plan(task_id=TASK_ID, plan=plan, jobs=make_jobs(plan))

        self.assertEqual(
            describe_canvas(result),
            ("chain", (), [("job", 100, (ON_ERROR,)), ("job", 101, (ON_ERROR, ON_SUCCESS))]),
        )

    def test_last_parallel_group_finalizes_task_from_body(self) -> None:
        plan = JobSpecV1.from_entries(
            make_script("/0"), make_group("/p", PARALLEL), make_script("/p/0"), make_script("/p/1")
        )

        result = prepare_execution_plan(task_id=TASK_ID, plan=plan, jobs=make_jobs(plan))

        self.assertEqual(
            describe_canvas(result),
            (
                "chain",
                (),
                [
                    ("job", 100, (ON_ERROR,)),
                    (
                        "chord",
                        (),
                        [("job", 101, ()), ("job", 102, ())],
                        ("group-finished", "/p", (ON_ERROR, ON_SUCCESS)),
                    ),
                ],
            ),
        )

    def test_steps_after_parallel_group_are_merged_into_its_body(self) -> None:
        plan = JobSpecV1.from_entries(
            make_group("/p", PARALLEL),
            make_script("/p/0"),
            make_script("/p/1"),
            make_group("/s", SEQUENTIAL),
            make_script("/s/0"),
            make_script("/s/1"),
        )

        result = prepare_execution_plan(task_id=TASK_ID, plan=plan, jobs=make_jobs(plan))

        # errback of body chain is passed to its steps by celery when body is run
        self.assertEqual(
            describe_canvas(result),
            (
                "chain",
                (),
                [
                    (
                        "chord",
                        (),
                        [("job", 100, ()), ("job", 101, ())],
                        (
                            "chain",
                            (ON_ERROR, ON_SUCCESS),
                            [("group-finished", "/p", ()), ("job", 102, ()), ("job", 103, ())],
                        ),
                    ),
                ],
            ),
        )

    def test_parallel_groups_in_a_row_are_separate_steps(self) -> None:
        plan = JobSpecV1.from_entries(
            make_group("/p1", PARALLEL),
            make_script("/p1/0"),
            make_script("/p1/1"),
            make_group("/p2", PARALLEL),
            make_script("/p2/0"),
            make_script("/p2/1"),
        )

        result = prepare_execution_plan(task_id=TASK_ID, plan=plan, jobs=make_jobs(plan))

        self.assertEqual(
            describe_canvas(result),
            (
                "chain",
                (),
                [
                    (
                        "chord",
                        (),
                        [("job", 100, ()), ("job", 101, ())],
                        ("group-finished", "/p1", (ON_ERROR,)),
                    ),
                    (
                        "chord",
                        (),
                        [("job", 102, ()), ("job", 103, ())],
                        ("group-finished", "/p2", (ON_ERROR, ON_SUCCESS)),
                    ),
                ],
            ),
        )

    def test_sequential_group_within_parallel_one_does_not_finalize_task(self) -> None:
        plan = JobSpecV1.from_entries(
            make_group("/p", PARALLEL),
            make_group("/p/s", SEQUENTIAL),
            make_script("/p/s/0"),
            make_script("/p/s/1"),
            make_script("/p/0"),
            make_script("/0"),
        )

        result = prepare_execution_plan(task_id=TASK_ID, plan=plan, jobs=make_jobs(plan))

        self.assertEqual(
            describe_canvas(result),
            (
                "chain",
                (),
                [
                    (
                        "chord",
                        (),
                        [("chain", (), [("job", 100, ()), ("job", 101, ())]), ("job", 102, ())],
                        ("chain", (ON_ERROR, ON_SUCCESS), [("group-finished", "/p", ()), ("job", 103, ())]),
                    ),
                ],
            ),
        )

    def test_parallel_group_within_sequential_one_is_merged_into_root(self) -> None:
        plan = JobSpecV1.from_entries(
            make_script("/0"),
            make_group("/s", SEQUENTIAL),
            make_group("/s/p", PARALLEL),
            make_script("/s/p/0"),
            make_script("/s/p/1"),
            make_script("/s/0"),
        )

        result = prepare_execution_plan(task_id=TASK_ID, plan=plan, jobs=make_jobs(plan))

        self.assertEqual(
            describe_canvas(result),
            (
                "chain",
                (),
                [
                    ("job", 100, (ON_ERROR,)),
                    (
                        "chord",
                        (),
                        [("job", 101, ()), ("job", 102, ())],
                        ("chain", (ON_ERROR, ON_SUCCESS), [("group-finished", "/s/p", ()), ("job", 103, ())]),
                    ),
                ],
            ),
        )
