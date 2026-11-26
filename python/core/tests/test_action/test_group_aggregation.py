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

from core.action.job.operations import aggregate_group_dates, aggregate_group_status
from core.action.types import ExecutionStatus, ExecutionStyle, RuntimeDates

ABORTED = ExecutionStatus.ABORTED
BROKEN = ExecutionStatus.BROKEN
CREATED = ExecutionStatus.CREATED
FAILED = ExecutionStatus.FAILED
QUEUED = ExecutionStatus.QUEUED
REVOKED = ExecutionStatus.REVOKED
REVOKING = ExecutionStatus.REVOKING
RUNNING = ExecutionStatus.RUNNING
SCHEDULED = ExecutionStatus.SCHEDULED
SUCCESS = ExecutionStatus.SUCCESS
TERMINATING = ExecutionStatus.TERMINATING

PARALLEL = ExecutionStyle.PARALLEL
SEQUENTIAL = ExecutionStyle.SEQUENTIAL

BASE = datetime(2026, 8, 12, 10, 30, tzinfo=timezone.utc)
NO_DATES = RuntimeDates()


def at(seconds: int) -> datetime:
    return BASE + timedelta(seconds=seconds)


def ran(start: int, finish: int | None = None) -> RuntimeDates:
    return RuntimeDates(start=at(start), finish=None if finish is None else at(finish))


StatusCase = tuple[list[ExecutionStatus], ExecutionStyle, ExecutionStatus]


def in_both_styles(children: list[ExecutionStatus], expected: ExecutionStatus) -> tuple[StatusCase, StatusCase]:
    return (children, SEQUENTIAL, expected), (children, PARALLEL, expected)


# children's statuses in level order | style of the node | derived node status
# grouped by the evaluation order of the rules, first matching rule wins
STATUS_CASES: tuple[StatusCase, ...] = (
    # 1. anything in progress makes the node running, whatever else is there
    *in_both_styles([RUNNING], RUNNING),
    *in_both_styles([SUCCESS, RUNNING], RUNNING),
    *in_both_styles([SUCCESS, SCHEDULED], RUNNING),
    *in_both_styles([SUCCESS, QUEUED], RUNNING),
    *in_both_styles([SUCCESS, REVOKING], RUNNING),
    *in_both_styles([SUCCESS, TERMINATING], RUNNING),
    *in_both_styles([RUNNING, SUCCESS], RUNNING),
    *in_both_styles([FAILED, RUNNING], RUNNING),
    *in_both_styles([BROKEN, RUNNING], RUNNING),
    *in_both_styles([CREATED, RUNNING], RUNNING),
    # 2. failure beats everything settled and not started
    *in_both_styles([FAILED], FAILED),
    *in_both_styles([BROKEN], FAILED),
    *in_both_styles([SUCCESS, BROKEN], FAILED),
    *in_both_styles([FAILED, SUCCESS], FAILED),
    *in_both_styles([FAILED, ABORTED], FAILED),
    *in_both_styles([FAILED, REVOKED], FAILED),
    *in_both_styles([BROKEN, ABORTED], FAILED),
    *in_both_styles([BROKEN, REVOKED], FAILED),
    *in_both_styles([FAILED, CREATED], FAILED),
    # 3. nothing started yet
    *in_both_styles([CREATED], CREATED),
    *in_both_styles([CREATED, CREATED], CREATED),
    # 4. everything succeeded
    *in_both_styles([SUCCESS], SUCCESS),
    *in_both_styles([SUCCESS, SUCCESS, SUCCESS], SUCCESS),
    # 5. everything revoked
    *in_both_styles([REVOKED], REVOKED),
    *in_both_styles([REVOKED, REVOKED], REVOKED),
    # 6. some settled, some not started: running, whatever state the task is in
    *in_both_styles([SUCCESS, CREATED], RUNNING),
    *in_both_styles([CREATED, SUCCESS], RUNNING),
    *in_both_styles([ABORTED, CREATED], RUNNING),
    *in_both_styles([REVOKED, CREATED], RUNNING),
    # 7. settled mix of success, aborted and revoked: parallel node is aborted
    ([ABORTED], PARALLEL, ABORTED),
    ([SUCCESS, ABORTED], PARALLEL, ABORTED),
    ([ABORTED, SUCCESS], PARALLEL, ABORTED),
    ([SUCCESS, REVOKED], PARALLEL, ABORTED),
    ([REVOKED, SUCCESS], PARALLEL, ABORTED),
    ([ABORTED, REVOKED], PARALLEL, ABORTED),
    # 7. settled mix of success, aborted and revoked: sequential node is what its last child is
    ([ABORTED, SUCCESS], SEQUENTIAL, SUCCESS),
    ([REVOKED, SUCCESS], SEQUENTIAL, SUCCESS),
    ([ABORTED, REVOKED, SUCCESS], SEQUENTIAL, SUCCESS),
    ([SUCCESS, ABORTED], SEQUENTIAL, ABORTED),
    ([SUCCESS, REVOKED], SEQUENTIAL, ABORTED),
    ([ABORTED, REVOKED], SEQUENTIAL, ABORTED),
    ([REVOKED, ABORTED], SEQUENTIAL, ABORTED),
    ([SUCCESS, SUCCESS, ABORTED], SEQUENTIAL, ABORTED),
    ([ABORTED], SEQUENTIAL, ABORTED),
    ([ABORTED, ABORTED], SEQUENTIAL, ABORTED),
    # parallel flicker when celery stalls one branch: failed while the branch isn't started ...
    ([SUCCESS, FAILED, CREATED], PARALLEL, FAILED),
    # ... running again once it is
    ([SUCCESS, FAILED, RUNNING], PARALLEL, RUNNING),
    # no children at all
    ([], PARALLEL, ABORTED),
)

# children's dates | derived group dates
DATES_CASES: tuple[tuple[list[RuntimeDates], RuntimeDates], ...] = (
    # start is the earliest known, end the latest one once every child has finished
    ([ran(10, 20), ran(5, 15), ran(30, 40)], ran(5, 40)),
    # a child without an end (not started, still running or never finished) leaves the group's end unknown
    ([ran(10, 20), NO_DATES, ran(5, 15), ran(30, 40)], RuntimeDates(start=at(5))),
    ([ran(0, 12), ran(12, 30), NO_DATES], RuntimeDates(start=at(0))),
    ([ran(0, 7), NO_DATES], RuntimeDates(start=at(0))),
    ([ran(0, 10), ran(10)], RuntimeDates(start=at(0))),
    ([ran(0, 10), ran(20)], RuntimeDates(start=at(0))),
    # no child ever ran
    ([NO_DATES, NO_DATES], NO_DATES),
)


class TestAggregateGroupStatus(TestCase):
    def test_status_cases(self) -> None:
        for children, style, expected in STATUS_CASES:
            with self.subTest(children=children, style=style):
                self.assertEqual(aggregate_group_status(children=children, style=style), expected)

    def test_every_status_is_classified(self) -> None:
        # a status no rule knows about raises, so a newly added one surfaces here
        for status in ExecutionStatus:
            for style in ExecutionStyle:
                with self.subTest(status=status, style=style):
                    self.assertIsInstance(aggregate_group_status(children=[status], style=style), ExecutionStatus)

    def test_subgroup_counts_as_one_child_with_its_status(self) -> None:
        aborted_subgroup = aggregate_group_status(children=[SUCCESS, ABORTED], style=PARALLEL)
        succeeded_subgroup = aggregate_group_status(children=[ABORTED, SUCCESS], style=SEQUENTIAL)

        self.assertEqual(aggregate_group_status(children=[SUCCESS, aborted_subgroup], style=SEQUENTIAL), ABORTED)
        self.assertEqual(aggregate_group_status(children=[aborted_subgroup, SUCCESS], style=SEQUENTIAL), SUCCESS)
        self.assertEqual(aggregate_group_status(children=[succeeded_subgroup, SUCCESS], style=PARALLEL), SUCCESS)
        self.assertEqual(aggregate_group_status(children=[SUCCESS, succeeded_subgroup], style=SEQUENTIAL), SUCCESS)

    def test_sequential_without_children_has_no_last_child(self) -> None:
        with self.assertRaises(IndexError):
            aggregate_group_status(children=[], style=SEQUENTIAL)


class TestAggregateGroupDates(TestCase):
    def test_dates_cases(self) -> None:
        for children, expected in DATES_CASES:
            with self.subTest(children=children):
                dates = aggregate_group_dates(children=children)

                self.assertEqual(dates, expected)
                self.assertEqual(dates.duration, expected.duration)
