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

"""
Serializers of the internal API, and the execution plan of a task in the shape that API exposes it.

The plan tree is built as plain typed nodes first, so the recursion and the job/group union stay
ordinary Python. Node fields are named after the API ones (in snake_case) so that the DRF
serializers over them -- which land with the endpoint that exposes the plan -- need no remapping,
only the renderer's camelization.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias

from core.action.job.operations import aggregate_group_dates, aggregate_group_status
from core.action.operations import to_rich_jobs
from core.action.types import (
    ExecutionStatus,
    ExecutionStyle,
    GroupSpec,
    JobHierarchyLevel,
    JobShortInfo,
    JobSpecV1,
    RichJob,
    RuntimeDates,
)
from core.spec.keys import level_keys_to_full_key
from core.spec.types import FullSpecKey, LevelSpecKey
from core.types import JobID
from rest_framework.serializers import (
    BooleanField,
    CharField,
    DateTimeField,
    FloatField,
    IntegerField,
    ReadOnlyField,
    Serializer,
    SerializerMethodField,
)


class StatusCheckerTokenSerializer(Serializer):
    token = CharField(read_only=True, help_text="Status server shared-secret token for status checker")


@dataclass(slots=True, frozen=True)
class JobNode:
    id: JobID
    name: str
    display_name: str
    status: ExecutionStatus
    start_time: datetime | None
    end_time: datetime | None
    duration: float | None
    is_terminatable: bool
    kind: Literal["job"] = "job"


@dataclass(slots=True, frozen=True)
class GroupNode:
    name: str
    display_name: str
    status: ExecutionStatus
    start_time: datetime | None
    end_time: datetime | None
    duration: float | None
    is_terminatable: bool
    kind: ExecutionStyle
    children: "tuple[Node, ...]"


Node: TypeAlias = JobNode | GroupNode


@dataclass(slots=True, frozen=True)
class TaskExecutionPlan:
    version: int
    children: tuple[Node, ...]


def represent_execution_plan(spec: JobSpecV1, jobs: Iterable[JobShortInfo], version: int) -> TaskExecutionPlan:
    """
    Turn a task's plan and its jobs into a tree of job and group nodes, in the plan's declaration order.

    Groups have no state of their own: it's derived from their children every time
    (see `aggregate_group_status` / `aggregate_group_dates`).

    `version` is the version of the stored plan envelope, passed in by the view that read it.

    Raises `KeyError` when the plan and the jobs don't match:
    either a job points at a node the plan lacks or a plan script has no job.
    """

    children = _convert_level(
        level=spec.hierarchy,
        group_levels=(),
        spec=spec,
        rich_jobs=to_rich_jobs(spec=spec, jobs=jobs),
    )

    return TaskExecutionPlan(version=version, children=tuple(node for node, *_ in children))


# A node together with the status and dates its parent aggregates from, so no parent re-derives a child's state.
_ConvertedNode: TypeAlias = tuple[Node, ExecutionStatus, RuntimeDates]


def _convert_level(
    level: JobHierarchyLevel,
    group_levels: tuple[LevelSpecKey, ...],
    spec: JobSpecV1,
    rich_jobs: dict[FullSpecKey, RichJob],
) -> list[_ConvertedNode]:
    converted = []

    for level_key in level.fields:
        own_levels = (*group_levels, level_key)
        full_key = level_keys_to_full_key(own_levels)
        child_level = level.child_groups.get(level_key)

        if child_level is None:
            converted.append(_convert_job(rich_job=rich_jobs[full_key]))
            continue

        group_children = _convert_level(
            level=child_level,
            group_levels=own_levels,
            spec=spec,
            rich_jobs=rich_jobs,
        )

        converted.append(_convert_group(group_spec=spec.groups[full_key], children=group_children))

    return converted


def _convert_group(group_spec: GroupSpec, children: list[_ConvertedNode]) -> _ConvertedNode:
    status = aggregate_group_status(children=(status for _, status, _ in children))
    dates = aggregate_group_dates(children=[dates for *_, dates in children])

    node = GroupNode(
        name=group_spec.names.internal,
        display_name=group_spec.names.display,
        status=status,
        start_time=dates.start,
        end_time=dates.finish,
        duration=dates.duration,
        is_terminatable=True,
        kind=group_spec.type,
        children=tuple(node for node, *_ in children),
    )

    return node, status, dates


def _convert_job(rich_job: RichJob) -> _ConvertedNode:
    runtime = rich_job.runtime

    node = JobNode(
        id=runtime.id,
        name=rich_job.spec.names.internal,
        display_name=rich_job.spec.names.display,
        status=runtime.status,
        start_time=runtime.dates.start,
        end_time=runtime.dates.finish,
        duration=runtime.dates.duration,
        is_terminatable=rich_job.spec.details.terminatable,
    )

    return node, runtime.status, runtime.dates


# DRF layer over the node types above: dumb, declared-fields-only serializers, since the tree itself
# is already built (and tested) in plain Python. `status` and `kind` (of a group) are read with
# `ReadOnlyField` rather than `CharField`, because both are `str` enums: `CharField.to_representation`
# calls `str()` on them, which -- unlike the plain string content a str-enum instance already carries --
# gives back `"ExecutionStatus.SUCCESS"` instead of `"success"`.


class JobNodeSerializer(Serializer):
    kind = ReadOnlyField()
    id = IntegerField()
    name = CharField()
    display_name = CharField()
    status = ReadOnlyField()
    start_time = DateTimeField(allow_null=True)
    end_time = DateTimeField(allow_null=True)
    duration = FloatField(allow_null=True)
    is_terminatable = BooleanField()


class GroupNodeSerializer(Serializer):
    kind = ReadOnlyField()
    name = CharField()
    display_name = CharField()
    status = ReadOnlyField()
    start_time = DateTimeField(allow_null=True)
    end_time = DateTimeField(allow_null=True)
    duration = FloatField(allow_null=True)
    is_terminatable = BooleanField()
    children = SerializerMethodField()

    @staticmethod
    def get_children(obj: GroupNode) -> list[dict]:
        return [_serialize_node(child) for child in obj.children]


class TaskExecutionPlanSerializer(Serializer):
    version = IntegerField()
    children = SerializerMethodField()

    @staticmethod
    def get_children(obj: TaskExecutionPlan) -> list[dict]:
        return [_serialize_node(child) for child in obj.children]


def _serialize_node(node: Node) -> dict:
    if isinstance(node, GroupNode):
        return GroupNodeSerializer(instance=node).data

    return JobNodeSerializer(instance=node).data
